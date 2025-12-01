import React, { useState, useCallback } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Upload, X, FileText, Check, Loader2, ArrowRight, ArrowLeft, FolderOpen, Folder, Home, ChevronLeft, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

interface Model {
  id: string;
  name: string;
}

interface DirectoryItem {
  name: string;
  path: string;
  isDirectory: boolean;
}

interface TestNewFileModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const STEPS = ['Select Model', 'Select Files', 'Add Notes', 'Processing'];

export default function TestNewFileModal({ open, onClose, onSuccess }: TestNewFileModalProps) {
  const { toast } = useToast();
  const [step, setStep] = useState(0);
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<Array<{ path: string; name: string }>>([]);
  const [notes, setNotes] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isGeneratingNotes, setIsGeneratingNotes] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processingStage, setProcessingStage] = useState('');
  const [results, setResults] = useState<Array<{ filename: string; prediction: string; confidence: number; num_chunks: number }>>([]);

  // File browser state
  const [showBrowser, setShowBrowser] = useState(false);
  const [currentPath, setCurrentPath] = useState('');

  // Fetch available models
  const { data: models = [] } = useQuery<Model[]>({
    queryKey: ['/api/models'],
  });

  // Fetch directory contents
  const { data: dirContents, isLoading: dirLoading } = useQuery<DirectoryItem[]>({
    queryKey: ["/api/browse", currentPath ? `?path=${encodeURIComponent(currentPath)}` : ""],
    enabled: showBrowser,
  });

  const handleSelectFile = (path: string, name: string) => {
    // Check if already selected
    if (!selectedFiles.some(f => f.path === path)) {
      setSelectedFiles(prev => [...prev, { path, name }]);
    }
  };

  const removeFile = (path: string) => {
    setSelectedFiles(prev => prev.filter(f => f.path !== path));
  };

  const handleNavigate = (path: string) => {
    setCurrentPath(path);
  };

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
      // Get model details
      const modelResponse = await fetch(`/api/models/${selectedModel}`);
      if (!modelResponse.ok) throw new Error("Failed to fetch model details");
      const modelData = await modelResponse.json();

      // Generate notes using OpenAI
      const prompt = `Generate professional test notes for a sensor data analysis test with the following details:

Model: ${modelData.name || selectedModel}
Files to test: ${selectedFiles.map(f => f.name).join(", ")}
Number of files: ${selectedFiles.length}

Please generate concise, professional notes (2-3 sentences) that would be appropriate for documenting this inference test.`;

      const response = await fetch('/api/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: prompt,
        }),
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

  const runInference = async () => {
    setIsProcessing(true);
    setStep(3);
    setProgress(0);
    const newResults: Array<{ filename: string; prediction: string; confidence: number; num_chunks: number }> = [];

    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      setProgress(((i) / selectedFiles.length) * 100);
      setProcessingStage(`Processing ${file.name}...`);

      try {
        // Run inference directly with the file path (no upload needed)
        const inferenceResponse = await fetch('/api/tests/inference', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            csv_path: file.path,
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

        // Calculate average model confidence from probabilities
        // Each prob array contains confidence for each class, take max per chunk
        const probs = inferenceResult.probabilities || [];
        let avgConfidence = 0;
        if (probs.length > 0) {
          const maxProbs = probs.map((p: number[]) => Math.max(...p));
          avgConfidence = (maxProbs.reduce((a: number, b: number) => a + b, 0) / maxProbs.length) * 100;
        }

        newResults.push({
          filename: file.name,
          prediction: inferenceResult.majority_class || 'Unknown',
          confidence: avgConfidence,
          num_chunks: inferenceResult.num_chunks || 0,
        });
      } catch (error) {
        console.error('Error processing file:', error);
        newResults.push({
          filename: file.name,
          prediction: 'Error',
          confidence: 0,
          num_chunks: 0,
        });
        toast({
          title: "Processing Error",
          description: error instanceof Error ? error.message : 'Failed to process file',
          variant: "destructive",
        });
      }

      setProgress(((i + 1) / selectedFiles.length) * 100);
    }

    setResults(newResults);
    setIsProcessing(false);
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
    setShowBrowser(false);
    setCurrentPath('');
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

  // Filter for CSV files in directory listing
  const csvFiles = dirContents?.filter(item => !item.isDirectory && item.name.endsWith('.csv')) || [];
  const directories = dirContents?.filter(item => item.isDirectory) || [];

  return (
    <Dialog open={open} onOpenChange={resetAndClose}>
      <DialogContent className={cn(
        "p-0 gap-0 overflow-hidden",
        showBrowser ? "max-w-6xl w-[90vw]" : "max-w-3xl w-[90vw]"
      )}>
        <DialogHeader className="p-6 pb-4 border-b border-border">
          <DialogTitle className="text-xl font-bold text-foreground">
            {showBrowser ? "Browse for CSV Files" : "Test New File"}
          </DialogTitle>

          {!showBrowser && (
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
          )}
        </DialogHeader>

        {showBrowser ? (
          // File Browser View
          <div className="p-6 space-y-4">
            {/* Navigation bar */}
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setCurrentPath("")}
                title="Go to home directory"
                className="h-9 px-2 hover:scale-110 hover:shadow-md active:scale-95 transition-all duration-200"
              >
                <Home className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  if (currentPath) {
                    const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
                    setCurrentPath(parentPath === '/' ? '' : parentPath);
                  }
                }}
                disabled={!currentPath}
                title="Go to parent directory"
                className="h-9 px-2 hover:scale-110 hover:shadow-md active:scale-95 transition-all duration-200"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <div className="flex-1 flex items-center gap-2 p-2 bg-muted rounded-lg border h-9">
                <Folder className="h-4 w-4 text-primary flex-shrink-0" />
                <code className="text-sm truncate font-mono">
                  {currentPath || "~ (Home)"}
                </code>
              </div>
            </div>

            {/* Directory listing */}
            <ScrollArea className="h-[500px] border rounded-lg">
              {dirLoading ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="p-2 space-y-1">
                  {/* Directories first */}
                  {directories.map((item) => (
                    <div
                      key={item.path}
                      className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm cursor-pointer transition-all hover:bg-muted hover:shadow-sm"
                      onClick={() => handleNavigate(item.path)}
                    >
                      <Folder className="h-4 w-4 text-primary" />
                      <span className="flex-1 truncate">{item.name}</span>
                    </div>
                  ))}

                  {/* CSV Files */}
                  {csvFiles.map((item) => (
                    <div
                      key={item.path}
                      className={cn(
                        "flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm transition-all",
                        selectedFiles.some(f => f.path === item.path)
                          ? "bg-primary/10 border border-primary/30"
                          : "hover:bg-muted cursor-pointer"
                      )}
                      onClick={() => handleSelectFile(item.path, item.name)}
                    >
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1 truncate">{item.name}</span>
                      {selectedFiles.some(f => f.path === item.path) ? (
                        <Check className="h-4 w-4 text-primary" />
                      ) : (
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-7 px-3 text-xs hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectFile(item.path, item.name);
                          }}
                        >
                          Select
                        </Button>
                      )}
                    </div>
                  ))}

                  {directories.length === 0 && csvFiles.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground">
                      No CSV files in this directory
                    </div>
                  )}
                </div>
              )}
            </ScrollArea>

            {/* Selected files summary */}
            {selectedFiles.length > 0 && (
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-sm font-medium text-foreground mb-2">
                  {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
                </p>
                <div className="flex flex-wrap gap-2">
                  {selectedFiles.map((file) => (
                    <div key={file.path} className="flex items-center gap-1 bg-background px-2 py-1 rounded text-xs">
                      <FileText className="h-3 w-3" />
                      <span className="truncate max-w-[150px]">{file.name}</span>
                      <button
                        onClick={() => removeFile(file.path)}
                        className="ml-1 hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setShowBrowser(false)} className="hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200">
                Done Selecting
              </Button>
            </DialogFooter>
          </div>
        ) : (
          // Main Wizard View
          <>
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
                    <label className="text-sm font-semibold text-foreground">Select CSV Files</label>

                    <Button
                      variant="outline"
                      className="w-full h-24 border-dashed hover:shadow-md hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
                      onClick={() => setShowBrowser(true)}
                    >
                      <div className="flex flex-col items-center gap-2">
                        <FolderOpen className="h-8 w-8 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">Browse for CSV files...</span>
                      </div>
                    </Button>

                    {selectedFiles.length > 0 && (
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {selectedFiles.map((file) => (
                          <div key={file.path} className="flex items-center justify-between p-3 bg-muted/50 rounded-lg gap-2">
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                              <FileText className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                              <div className="min-w-0 flex-1">
                                <p className="text-sm font-medium text-foreground truncate">{file.name}</p>
                                <p className="text-xs text-muted-foreground break-all line-clamp-2">{file.path}</p>
                              </div>
                            </div>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeFile(file.path)}
                              className="h-8 w-8 text-muted-foreground hover:text-foreground hover:scale-110 hover:shadow-md active:scale-95 transition-all duration-200 flex-shrink-0"
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
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
                        <h3 className="text-lg font-semibold text-foreground mb-2">Processing Files</h3>
                        <p className="text-sm text-muted-foreground mb-6">{processingStage || 'Running inference on your sensor data...'}</p>
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
                  onClick={runInference}
                  aria-label="Run inference on uploaded file"
                  className="ml-auto"
                >
                  Run Inference
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
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
