import { useState, useRef, useCallback } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import { Upload, Plus, Loader2, FileText, X, Database, Wand2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const formSchema = z.object({
  folderName: z.string().optional(),
  label: z.string().min(1, "Label is required").regex(/^[a-zA-Z0-9_.-]+$/, "Alphanumeric, dots, dashes, and underscores only"),
});

type FormValues = z.infer<typeof formSchema>;

interface SelectedFile {
  file: File;
  id: string;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function AddDataModal() {
  const [open, setOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processingStage, setProcessingStage] = useState("");
  const [uploadedFolderPath, setUploadedFolderPath] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      folderName: "",
      label: "",
    },
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
      });
    }

    if (validFiles.length > 0) {
      setSelectedFiles(prev => [...prev, ...validFiles]);
    }
  }, [selectedFiles, toast]);

  const removeFile = useCallback((id: string) => {
    setSelectedFiles(prev => prev.filter(sf => sf.id !== id));
  }, []);

  const clearFiles = useCallback(() => {
    setSelectedFiles([]);
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

  const suggestLabelMutation = useMutation({
    mutationFn: async () => {
      // Use the first file's name or folder name to suggest a label
      const baseName = form.getValues("folderName") ||
        (selectedFiles.length > 0 ? selectedFiles[0].file.name.replace('.csv', '') : '');

      if (!baseName) {
        throw new Error("No files selected");
      }

      // Generate a clean label from the filename
      const cleanLabel = baseName
        .replace(/[^a-zA-Z0-9_.-]/g, '_')
        .replace(/_+/g, '_')
        .replace(/^_|_$/g, '')
        .toLowerCase();

      return { success: true, label: cleanLabel };
    },
    onSuccess: (data) => {
      if (data.success && data.label) {
        form.setValue("label", data.label, {
          shouldValidate: true,
          shouldDirty: true,
          shouldTouch: true
        });
        toast({
          title: "Label Generated",
          description: `Suggested label: ${data.label}`,
          duration: 3000,
        });
      }
    },
    onError: (error: Error) => {
      toast({
        title: "Could not generate label",
        description: error.message || "Please enter a label manually.",
        variant: "destructive",
        duration: 3000,
      });
    },
  });

  async function onSubmit(values: FormValues) {
    if (selectedFiles.length === 0) {
      toast({
        title: "No Files Selected",
        description: "Please select at least one CSV file to upload.",
        variant: "destructive",
      });
      return;
    }

    setIsProcessing(true);
    setProgress(0);
    setProcessingStage("Uploading files...");

    try {
      // Step 1: Upload files to raw_database
      const formData = new FormData();
      selectedFiles.forEach(sf => {
        formData.append('files', sf.file);
      });
      if (values.folderName) {
        formData.append('folder_name', values.folderName);
      }

      setProgress(10);

      const uploadResponse = await fetch('/api/raw-database/upload', {
        method: 'POST',
        body: formData,
      });

      const uploadResult = await uploadResponse.json();

      if (!uploadResponse.ok || !uploadResult.success) {
        throw new Error(uploadResult.detail || uploadResult.error || 'Upload failed');
      }

      setUploadedFolderPath(uploadResult.folder_path);
      setProgress(40);
      setProcessingStage("Processing data...");

      // Step 2: Trigger ingestion with the uploaded folder
      const ingestResponse = await apiRequest("POST", "/api/ingest", {
        folderPath: uploadResult.folder_path,
        classificationLabel: values.label,
      });

      const ingestResult = await ingestResponse.json();

      setProgress(70);
      setProcessingStage("Finalizing...");

      // Step 3: Poll for completion
      const labelToCheck = values.label;
      let attempts = 0;
      const maxAttempts = 30;

      const pollForCompletion = async (): Promise<boolean> => {
        attempts++;
        try {
          const response = await fetch(`/api/labels/${encodeURIComponent(labelToCheck)}`);
          if (response.ok) {
            return true;
          }
        } catch (e) {
          // Label not ready yet
        }

        if (attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 2000));
          setProgress(70 + (attempts / maxAttempts) * 25);
          return pollForCompletion();
        }
        return false;
      };

      const completed = await pollForCompletion();

      setProgress(100);
      setProcessingStage("Complete!");

      await new Promise(resolve => setTimeout(resolve, 1000));

      setIsProcessing(false);
      setOpen(false);
      setSelectedFiles([]);
      setUploadedFolderPath(null);
      form.reset();

      queryClient.invalidateQueries({ queryKey: ["/api/labels"] });
      queryClient.invalidateQueries({ queryKey: ["/api/raw-database"] });

      toast({
        title: "Data Processed Successfully",
        description: completed
          ? `Data for label "${labelToCheck}" has been processed.`
          : "Data processing has started. It may take a moment to appear.",
        duration: 5000,
      });

    } catch (error) {
      setIsProcessing(false);
      setProgress(0);
      setProcessingStage("");
      toast({
        title: "Processing Failed",
        description: error instanceof Error ? error.message : "Failed to process data. Please try again.",
        variant: "destructive",
        duration: 5000,
      });
    }
  }

  const handleClose = (isOpen: boolean) => {
    if (isProcessing) return;
    setOpen(isOpen);
    if (!isOpen) {
      setSelectedFiles([]);
      setUploadedFolderPath(null);
      setProgress(0);
      setProcessingStage("");
      form.reset();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogTrigger asChild>
        <Button size="lg" className="gap-2 shadow-md hover:shadow-lg hover:scale-105 active:scale-95 transition-all duration-200 text-base px-6 py-3 h-12">
          <Plus className="h-5 w-5" /> Add Data
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[700px] w-[95vw] max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            {isProcessing ? (
              <>
                <Database className="h-5 w-5 animate-pulse" />
                Processing Data
              </>
            ) : (
              <>
                <Database className="h-5 w-5" />
                Import & Process Sensor Data
              </>
            )}
          </DialogTitle>
          {!isProcessing && (
            <DialogDescription>
              Upload CSV sensor data files from your computer and provide a classification label.
            </DialogDescription>
          )}
        </DialogHeader>

        {isProcessing ? (
          <div className="space-y-6 py-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{processingStage}</span>
                <span className="font-mono text-muted-foreground">{Math.round(progress)}%</span>
              </div>
              <Progress value={progress} className="h-3" />
            </div>

            <div className="bg-muted/50 rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-2 text-sm">
                <FileText className="h-4 w-4 text-blue-500" />
                <span className="text-muted-foreground">Files:</span>
                <span className="font-medium">{selectedFiles.length} CSV file(s)</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Database className="h-4 w-4 text-green-500" />
                <span className="text-muted-foreground">Label:</span>
                <code className="text-xs bg-background px-2 py-1 rounded">
                  {form.getValues("label")}
                </code>
              </div>
            </div>

            <p className="text-xs text-center text-muted-foreground">
              Processing runs in the background. You'll be notified when complete.
            </p>
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 py-2">
              {/* File Upload Area */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  CSV Files <span className="text-destructive">*</span>
                </label>

                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={cn(
                    "border-2 border-dashed rounded-lg p-6 transition-all cursor-pointer",
                    isDragging && "border-primary bg-primary/5 scale-[1.01]",
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
                  <div className="flex flex-col items-center gap-2 text-center">
                    <div className={cn(
                      "rounded-full p-3",
                      isDragging ? "bg-primary/10" : "bg-muted"
                    )}>
                      <Upload className={cn(
                        "h-6 w-6",
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
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-muted-foreground">
                        {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
                      </p>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={clearFiles}
                        className="h-7 text-xs text-muted-foreground hover:text-foreground"
                      >
                        Clear All
                      </Button>
                    </div>
                    <ScrollArea className={cn("border rounded-lg", selectedFiles.length > 4 ? "h-32" : "")}>
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
                              type="button"
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
                  </div>
                )}
              </div>

              {/* Folder Name (Optional) */}
              <FormField
                control={form.control}
                name="folderName"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium">
                      Folder Name (optional)
                    </FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Auto-generated if empty"
                        {...field}
                        className="h-11"
                      />
                    </FormControl>
                    <p className="text-xs text-muted-foreground">
                      Name for the folder in raw database. Leave empty to auto-generate.
                    </p>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Classification Label */}
              <FormField
                control={form.control}
                name="label"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium">
                      Classification Label <span className="text-destructive">*</span>
                    </FormLabel>
                    <div className="flex gap-2">
                      <FormControl>
                        <Input
                          placeholder="e.g., damaged, healthy, baseline"
                          {...field}
                          className="h-11"
                        />
                      </FormControl>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => suggestLabelMutation.mutate()}
                        disabled={selectedFiles.length === 0 || suggestLabelMutation.isPending}
                        className="h-11 px-3 hover:scale-110 hover:shadow-md active:scale-95 transition-all duration-200"
                        title="Generate label from filename"
                      >
                        {suggestLabelMutation.isPending ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Wand2 className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      This label identifies the processed dataset (alphanumeric, dots, dashes, underscores)
                    </p>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <DialogFooter className="gap-2 pt-4 border-t">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setOpen(false)}
                  className="hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={selectedFiles.length === 0 || !form.watch("label")}
                  className="min-w-[140px] hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
                >
                  <Upload className="mr-2 h-4 w-4" />
                  Upload & Process
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  );
}
