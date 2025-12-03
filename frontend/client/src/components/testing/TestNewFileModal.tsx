import React, { useState, useCallback, useRef } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Upload, X, FileText, Check, Loader2, ArrowRight, ArrowLeft, Sparkles, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

interface Model {
  id: string;
  name: string;
}

interface SelectedFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'uploaded' | 'error';
  uploadedPath?: string;
  error?: string;
}

interface TestNewFileModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

const STEPS = ['Select Model', 'Select Files', 'Add Notes', 'Processing'];

export default function TestNewFileModal({ open, onClose, onSuccess }: TestNewFileModalProps) {
  const { toast } = useToast();
  const [step, setStep] = useState(0);
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
  const [notes, setNotes] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isGeneratingNotes, setIsGeneratingNotes] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processingStage, setProcessingStage] = useState('');
  const [results, setResults] = useState<Array<{ filename: string; prediction: string; confidence: number; num_chunks: number }>>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch available models
  const { data: models = [] } = useQuery<Model[]>({
    queryKey: ['/api/models'],
  });

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const filesArray = Array.from(newFiles);
    const validFiles: SelectedFile[] = [];

    for (const file of filesArray) {
      // Only accept CSV files
      if (!file.name.toLowerCase().endsWith('.csv')) {
        toast({
          title: "Invalid File Type",
          description: `${file.name} is not a CSV file`,
          variant: "destructive",
        });
        continue;
      }

      // Check for duplicates
      const isDuplicate = selectedFiles.some(sf => sf.file.name === file.name && sf.file.size === file.size);
      if (isDuplicate) {
        continue;
      }

      validFiles.push({
        file,
        id: `${file.name}-${Date.now()}-${Math.random()}`,
        status: 'pending',
      });
    }

    if (validFiles.length > 0) {
      setSelectedFiles(prev => [...prev, ...validFiles]);
    }
  }, [selectedFiles, toast]);

  const removeFile = useCallback((id: string) => {
    setSelectedFiles(prev => prev.filter(sf => sf.id !== id));
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  }, [addFiles]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
      e.target.value = '';
    }
  }, [addFiles]);

  const handleGenerateNotes = async () => {
    if (!selectedModel || selectedFiles.length === 0) {
      toast({
        title: "Cannot Generate Notes",
        description: "Please select a model and at least one file first.",
        variant: "destructive",
      });
      return;
    }

    setIsGeneratingNotes(true);
    try {
      const modelResponse = await fetch(`/api/models/${selectedModel}`);
      if (!modelResponse.ok) throw new Error("Failed to fetch model details");
      const modelData = await modelResponse.json();

      const prompt = `Generate professional test notes for a sensor data analysis test with the following details:

Model: ${modelData.name || selectedModel}
Files to test: ${selectedFiles.map(f => f.file.name).join(", ")}
Number of files: ${selectedFiles.length}

Please generate concise, professional notes (2-3 sentences) that would be appropriate for documenting this inference test.`;

      const response = await fetch('/api/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt }),
      });

      if (!response.ok) throw new Error('Failed to generate notes');
      const data = await response.json();

      setNotes(data.response || '');
      toast({
        title: "Notes Generated",
        description: "AI has generated test notes. You can edit them before running the test.",
      });
    } catch (error) {
      console.error('Error generating notes:', error);
      toast({
        title: "Error",
        description: "Failed to generate notes. Please try again or write notes manually.",
        variant: "destructive",
      });
    } finally {
      setIsGeneratingNotes(false);
    }
  };

  const uploadAndRunInference = async () => {
    setIsProcessing(true);
    setIsUploading(true);
    setStep(3);
    setProgress(0);
    const newResults: Array<{ filename: string; prediction: string; confidence: number; num_chunks: number }> = [];

    const totalSteps = selectedFiles.length * 2; // upload + inference for each file
    let completedSteps = 0;

    for (let i = 0; i < selectedFiles.length; i++) {
      const selectedFile = selectedFiles[i];

      // Step 1: Upload the file
      setProcessingStage(`Uploading ${selectedFile.file.name}...`);

      try {
        const formData = new FormData();
        formData.append('file', selectedFile.file);

        const uploadResponse = await fetch('/api/tests/upload', {
          method: 'POST',
          body: formData,
        });

        const uploadResult = await uploadResponse.json();

        if (!uploadResponse.ok || !uploadResult.success) {
          throw new Error(uploadResult.detail || uploadResult.error || 'Upload failed');
        }

        completedSteps++;
        setProgress((completedSteps / totalSteps) * 100);

        // Update file status
        setSelectedFiles(prev => prev.map(sf =>
          sf.id === selectedFile.id ? { ...sf, status: 'uploaded', uploadedPath: uploadResult.file_path } : sf
        ));

        // Step 2: Run inference
        setProcessingStage(`Analyzing ${selectedFile.file.name}...`);
        setIsUploading(false);

        const inferenceResponse = await fetch('/api/tests/inference', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            csv_path: uploadResult.file_path,
            model_id: selectedModel,
            notes: notes,
            tags: [],
            log_to_database: true,
          }),
        });

        const inferenceResult = await inferenceResponse.json();

        if (!inferenceResult.success) {
          throw new Error(inferenceResult.error || 'Inference failed');
        }

        // Calculate average model confidence
        const probs = inferenceResult.probabilities || [];
        let avgConfidence = 0;
        if (probs.length > 0) {
          const maxProbs = probs.map((p: number[]) => Math.max(...p));
          avgConfidence = (maxProbs.reduce((a: number, b: number) => a + b, 0) / maxProbs.length) * 100;
        }

        newResults.push({
          filename: selectedFile.file.name,
          prediction: inferenceResult.majority_class || 'Unknown',
          confidence: avgConfidence,
          num_chunks: inferenceResult.num_chunks || 0,
        });

        completedSteps++;
        setProgress((completedSteps / totalSteps) * 100);

      } catch (error) {
        console.error('Error processing file:', error);
        newResults.push({
          filename: selectedFile.file.name,
          prediction: 'Error',
          confidence: 0,
          num_chunks: 0,
        });

        setSelectedFiles(prev => prev.map(sf =>
          sf.id === selectedFile.id ? { ...sf, status: 'error', error: error instanceof Error ? error.message : 'Failed' } : sf
        ));

        toast({
          title: "Processing Error",
          description: error instanceof Error ? error.message : 'Failed to process file',
          variant: "destructive",
        });

        completedSteps += 2; // Skip both steps
        setProgress((completedSteps / totalSteps) * 100);
      }
    }

    setResults(newResults);
    setIsProcessing(false);
    setIsUploading(false);
    setProcessingStage('');

    const successCount = newResults.filter(r => r.prediction !== 'Error').length;
    toast({
      title: "Tests Complete",
      description: `Successfully processed ${successCount} of ${newResults.length} file${newResults.length !== 1 ? 's' : ''}`,
    });
  };

  const resetAndClose = () => {
    setStep(0);
    setSelectedModel('');
    setSelectedFiles([]);
    setNotes('');
    setResults([]);
    setProgress(0);
    setIsDragging(false);
    onClose();
    if (results.length > 0) {
      onSuccess();
    }
  };

  const canProceed = () => {
    switch (step) {
      case 0: return !!selectedModel;
      case 1: return selectedFiles.length > 0;
      case 2: return true;
      default: return false;
    }
  };

  return (
    <Dialog open={open} onOpenChange={resetAndClose}>
      <DialogContent className="max-w-3xl w-[90vw] p-0 gap-0 overflow-hidden">
        <DialogHeader className="p-6 pb-4 border-b border-border">
          <DialogTitle className="text-xl font-bold text-foreground">
            Test New File
          </DialogTitle>

          <div className="flex items-center gap-2 mt-4">
            {STEPS.map((s, i) => (
              <React.Fragment key={s}>
                <div className={`flex items-center gap-2 ${i <= step ? 'text-foreground' : 'text-muted-foreground'}`}>
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-colors ${
                    i < step ? 'bg-primary text-primary-foreground' : i === step ? 'bg-primary text-primary-foreground' : 'bg-muted'
                  }`}>
                    {i < step ? <Check className="h-4 w-4" /> : i + 1}
                  </div>
                  <span className="text-sm font-medium hidden sm:block">{s}</span>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`flex-1 h-0.5 mx-2 ${i < step ? 'bg-primary' : 'bg-muted'}`} />
                )}
              </React.Fragment>
            ))}
          </div>
        </DialogHeader>

        <div className="p-6 min-h-[300px]">
          <AnimatePresence mode="wait">
            {step === 0 && (
              <motion.div
                key="step-0"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <label className="text-sm font-semibold text-foreground">Select Model</label>
                <Select value={selectedModel} onValueChange={setSelectedModel}>
                  <SelectTrigger className="h-12 text-base">
                    <SelectValue placeholder="Choose a model for inference..." />
                  </SelectTrigger>
                  <SelectContent>
                    {models.map((model) => (
                      <SelectItem key={model.id} value={model.id}>{model.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-sm text-muted-foreground">
                  Select the trained model that will be used to process your sensor data files.
                </p>
              </motion.div>
            )}

            {step === 1 && (
              <motion.div
                key="step-1"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-4"
              >
                <label className="text-sm font-semibold text-foreground">Select CSV Files from Your Computer</label>

                {/* Drop Zone */}
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={cn(
                    "border-2 border-dashed rounded-lg p-8 transition-all cursor-pointer",
                    isDragging && "border-primary bg-primary/5 scale-[1.02]",
                    !isDragging && "border-muted-foreground/25 hover:border-primary hover:bg-muted/50"
                  )}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv"
                    multiple
                    onChange={handleFileInputChange}
                    className="hidden"
                  />
                  <div className="flex flex-col items-center gap-3 text-center">
                    <div className={cn(
                      "rounded-full p-4",
                      isDragging ? "bg-primary/10" : "bg-muted"
                    )}>
                      <Upload className={cn(
                        "h-8 w-8",
                        isDragging ? "text-primary" : "text-muted-foreground"
                      )} />
                    </div>
                    <div>
                      <p className="font-medium text-foreground">
                        {isDragging ? "Drop files here" : "Click to browse or drag files here"}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        CSV files only
                      </p>
                    </div>
                  </div>
                </div>

                {/* Selected Files List */}
                {selectedFiles.length > 0 && (
                  <ScrollArea className={cn("border rounded-lg", selectedFiles.length > 3 ? "h-40" : "")}>
                    <div className="p-2 space-y-1">
                      {selectedFiles.map((sf) => (
                        <div
                          key={sf.id}
                          className="flex items-center gap-2 px-3 py-2 rounded-md text-sm bg-muted/50"
                        >
                          <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="truncate font-medium">{sf.file.name}</p>
                            <p className="text-xs text-muted-foreground">{formatFileSize(sf.file.size)}</p>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={(e) => {
                              e.stopPropagation();
                              removeFile(sf.id);
                            }}
                            className="h-6 w-6 text-muted-foreground hover:text-foreground flex-shrink-0"
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )}

                <p className="text-sm text-muted-foreground">
                  {selectedFiles.length > 0
                    ? `${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''} selected`
                    : "Select CSV files from your computer to test with the model"}
                </p>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div
                key="step-2"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-5"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-sm font-semibold text-foreground">Notes (optional)</label>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleGenerateNotes}
                      disabled={isGeneratingNotes || !selectedModel || selectedFiles.length === 0}
                      className="h-8 hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
                    >
                      {isGeneratingNotes ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                          Generate Notes
                        </>
                      )}
                    </Button>
                  </div>
                  <Textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add any notes about this test..."
                    className="min-h-[150px] resize-none"
                  />
                  <p className="text-xs text-muted-foreground">
                    Document the purpose of this test, expected results, or any other relevant information.
                  </p>
                </div>
              </motion.div>
            )}

            {step === 3 && (
              <motion.div
                key="step-3"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                {isProcessing ? (
                  <div className="text-center py-8">
                    <Loader2 className="h-12 w-12 text-muted-foreground mx-auto mb-4 animate-spin" />
                    <h3 className="text-lg font-semibold text-foreground mb-2">
                      {isUploading ? 'Uploading Files' : 'Processing Files'}
                    </h3>
                    <p className="text-sm text-muted-foreground mb-6">
                      {processingStage || 'Running inference on your sensor data...'}
                    </p>
                    <Progress value={progress} className="h-2" />
                    <p className="text-sm text-muted-foreground mt-2">{Math.round(progress)}% complete</p>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <div className="w-16 h-16 bg-primary rounded-full flex items-center justify-center mx-auto mb-4">
                      <Check className="h-8 w-8 text-primary-foreground" />
                    </div>
                    <h3 className="text-lg font-semibold text-foreground mb-2">Tests Complete</h3>
                    <p className="text-sm text-muted-foreground mb-6">
                      Successfully processed {results.filter(r => r.prediction !== 'Error').length} of {results.length} file{results.length !== 1 ? 's' : ''}
                    </p>
                    <div className="bg-muted/50 rounded-lg p-4 text-left max-h-60 overflow-y-auto">
                      {results.map((result, idx) => (
                        <div key={idx} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                          <div className="min-w-0 flex-1 mr-4">
                            <span className="text-sm text-foreground truncate block">{result.filename}</span>
                            <span className="text-xs text-muted-foreground">{result.num_chunks} chunks processed</span>
                          </div>
                          <div className="flex items-center gap-3 flex-shrink-0">
                            <span className="text-sm font-semibold">{result.prediction}</span>
                            <span className={`text-xs px-2 py-1 rounded ${
                              result.prediction === 'Error' ? 'bg-red-500/10 text-red-600' :
                              result.confidence >= 80 ? 'bg-green-500/10 text-green-600' :
                              result.confidence >= 50 ? 'bg-yellow-500/10 text-yellow-600' :
                              'bg-red-500/10 text-red-600'
                            }`}>
                              {result.prediction === 'Error' ? 'Failed' : `${result.confidence.toFixed(0)}%`}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="p-6 pt-4 border-t border-border flex justify-between">
          {step > 0 && step < 3 && (
            <Button
              variant="ghost"
              onClick={() => setStep(step - 1)}
              className="text-muted-foreground hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
          )}
          {step === 0 && <div />}

          {step < 2 && (
            <Button
              variant="default"
              onClick={() => setStep(step + 1)}
              disabled={!canProceed()}
              aria-label="Continue to next step"
              className="ml-auto"
            >
              Continue
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          )}

          {step === 2 && (
            <Button
              variant="default"
              onClick={uploadAndRunInference}
              aria-label="Upload files and run inference"
              className="ml-auto"
            >
              Upload & Run Inference
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          )}

          {step === 3 && !isProcessing && (
            <Button
              variant="default"
              onClick={resetAndClose}
              aria-label="Close test modal"
              className="ml-auto"
            >
              Done
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
