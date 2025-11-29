import { useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import { FolderOpen, Plus, Loader2, Folder, FileText, ChevronUp, Check, Database, Wand2, ChevronLeft, Home } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

const formSchema = z.object({
  folderPath: z.string().min(1, "Please select a folder"),
  label: z.string().min(1, "Label is required").regex(/^[a-zA-Z0-9_.-]+$/, "Alphanumeric, dots, dashes, and underscores only"),
});

type FormValues = z.infer<typeof formSchema>;

interface DirectoryItem {
  name: string;
  path: string;
  isDirectory: boolean;
}

export function AddDataModal() {
  const [open, setOpen] = useState(false);
  const [showBrowser, setShowBrowser] = useState(false);
  const [currentPath, setCurrentPath] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [processingStage, setProcessingStage] = useState("");
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      folderPath: "",
      label: "",
    },
  });

  // Fetch directory contents
  const { data: dirContents, isLoading: dirLoading } = useQuery<DirectoryItem[]>({
    queryKey: ["/api/browse", currentPath ? `?path=${encodeURIComponent(currentPath)}` : ""],
    enabled: showBrowser,
  });

  // Cleanup progress interval on unmount
  useEffect(() => {
    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, []);

  const startProgressSimulation = () => {
    setIsProcessing(true);
    setProgress(0);
    setProcessingStage("Copying raw data...");

    const stages = [
      { progress: 10, stage: "Copying raw data..." },
      { progress: 20, stage: "Detecting CSV structure..." },
      { progress: 35, stage: "Processing CSV files..." },
      { progress: 50, stage: "Creating data chunks..." },
      { progress: 65, stage: "Interpolating data..." },
      { progress: 80, stage: "Generating metadata..." },
      { progress: 90, stage: "Finalizing..." },
    ];

    let currentStage = 0;
    let slowProgress = 90;
    progressIntervalRef.current = setInterval(() => {
      if (currentStage < stages.length) {
        setProgress(stages[currentStage].progress);
        setProcessingStage(stages[currentStage].stage);
        currentStage++;
      } else {
        // Continue slow progress from 90 to 99 (never reach 100 on our own)
        if (slowProgress < 99) {
          slowProgress += 0.5;
          setProgress(Math.min(slowProgress, 99));
          setProcessingStage("Processing... please wait");
        }
      }
    }, 1500);
  };

  const stopProgressSimulation = (success: boolean) => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
    if (success) {
      setProgress(100);
      setProcessingStage("Complete!");
    }
    // Small delay before closing to show completion
    setTimeout(() => {
      setIsProcessing(false);
      setProgress(0);
      setProcessingStage("");
    }, success ? 1000 : 0);
  };

  const suggestLabelMutation = useMutation({
    mutationFn: async (folderPath: string) => {
      const response = await apiRequest("POST", "/api/suggest-label", {
        folderPath,
      });
      return response.json();
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
      } else {
        toast({
          title: "Could not generate label",
          description: data.message || "Please enter a label manually.",
          variant: "destructive",
          duration: 3000,
        });
      }
    },
    onError: (error: Error) => {
      console.error("Suggest label error:", error);
      toast({
        title: "Could not generate label",
        description: "Please enter a label manually.",
        variant: "destructive",
        duration: 3000,
      });
    },
  });

  const ingestMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      startProgressSimulation();
      const response = await apiRequest("POST", "/api/ingest", {
        folderPath: values.folderPath,
        classificationLabel: values.label,
      });
      return response.json();
    },
    onSuccess: (data) => {
      // Poll for the label to appear in the database (up to 60 seconds)
      const labelToCheck = form.getValues("label");
      let attempts = 0;
      const maxAttempts = 30; // 30 attempts * 2 seconds = 60 seconds max

      const pollForCompletion = async () => {
        attempts++;
        try {
          const response = await fetch(`/api/labels/${encodeURIComponent(labelToCheck)}`);
          if (response.ok) {
            // Label exists - processing complete!
            stopProgressSimulation(true);
            setTimeout(() => {
              setOpen(false);
              setShowBrowser(false);
              form.reset();
              queryClient.invalidateQueries({ queryKey: ["/api/labels"] });
              queryClient.invalidateQueries({ queryKey: ["/api/raw-database"] });
              toast({
                title: "Data Processed Successfully",
                description: data.message || `Data for label "${labelToCheck}" has been processed.`,
                duration: 5000,
              });
            }, 1500);
            return;
          }
        } catch (e) {
          // Label not ready yet
        }

        if (attempts < maxAttempts) {
          // Keep polling
          setTimeout(pollForCompletion, 2000);
        } else {
          // Timeout - assume it worked since API returned 200
          stopProgressSimulation(true);
          setTimeout(() => {
            setOpen(false);
            setShowBrowser(false);
            form.reset();
            queryClient.invalidateQueries({ queryKey: ["/api/labels"] });
            queryClient.invalidateQueries({ queryKey: ["/api/raw-database"] });
            toast({
              title: "Processing Initiated",
              description: "Data processing has started. It may take a moment to appear.",
              duration: 5000,
            });
          }, 1500);
        }
      };

      // Start polling after a short delay
      setTimeout(pollForCompletion, 3000);
    },
    onError: (error: Error) => {
      stopProgressSimulation(false);
      toast({
        title: "Processing Failed",
        description: error.message || "Failed to process data. Please check the folder path and try again.",
        variant: "destructive",
        duration: 5000,
      });
    },
  });

  function onSubmit(values: FormValues) {
    ingestMutation.mutate(values);
  }

  const handleBrowseClick = () => {
    setShowBrowser(true);
    // Start from home directory
    setCurrentPath("");
  };

  const handleSelectFolder = (path: string) => {
    form.setValue("folderPath", path, {
      shouldValidate: true,
      shouldDirty: true,
      shouldTouch: true
    });
    setShowBrowser(false);
    setCurrentPath("");
  };

  const handleNavigate = (path: string) => {
    setCurrentPath(path);
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => {
      if (isProcessing) return; // Prevent closing while processing
      setOpen(isOpen);
      if (!isOpen) {
        setShowBrowser(false);
        setCurrentPath("");
      }
    }}>
      <DialogTrigger asChild>
        <Button size="lg" className="gap-2 shadow-md hover:shadow-lg transition-all text-base px-6 py-3 h-12">
          <Plus className="h-5 w-5" /> Add Data
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[1400px] w-[95vw] max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold flex items-center gap-2">
            {showBrowser ? (
              <>
                <FolderOpen className="h-5 w-5" />
                Select Folder
              </>
            ) : isProcessing ? (
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
          {!showBrowser && !isProcessing && (
            <DialogDescription>
              Select a folder containing CSV sensor data files and provide a classification label.
            </DialogDescription>
          )}
        </DialogHeader>

        {isProcessing ? (
          // Processing view with progress bar
          <div className="space-y-6 py-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{processingStage}</span>
                <span className="font-mono text-muted-foreground">{progress}%</span>
              </div>
              <Progress value={progress} className="h-3" />
            </div>

            <div className="bg-muted/50 rounded-lg p-4 space-y-3">
              <div className="flex flex-col gap-1 text-sm">
                <div className="flex items-center gap-2">
                  <Folder className="h-4 w-4 text-blue-500 shrink-0" />
                  <span className="text-muted-foreground">Folder:</span>
                </div>
                <code className="text-xs bg-background px-2 py-1.5 rounded break-all ml-6 block w-full overflow-x-auto whitespace-pre-wrap" title={form.getValues("folderPath")}>
                  {form.getValues("folderPath")}
                </code>
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

            <div className="flex justify-center pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  stopProgressSimulation(false);
                  setOpen(false);
                  form.reset();
                }}
                className="gap-2"
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : showBrowser ? (
          <div className="space-y-4">
            {/* Navigation bar */}
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setCurrentPath("")}
                title="Go to home directory"
                className="h-9 px-2"
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
                className="h-9 px-2"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <div className="flex-1 flex items-center gap-2 p-2 bg-muted rounded-lg border h-9">
                <Folder className="h-4 w-4 text-blue-500 flex-shrink-0" />
                <code className="text-sm truncate font-mono">
                  {currentPath || "~ (Home)"}
                </code>
              </div>
            </div>

            {/* Directory listing */}
            <ScrollArea className="h-[700px] border rounded-lg">
              {dirLoading ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="p-2 space-y-1">
                  {dirContents?.map((item) => (
                    <div
                      key={item.path}
                      className={cn(
                        "flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm cursor-pointer transition-all",
                        item.isDirectory
                          ? "hover:bg-muted hover:shadow-sm"
                          : "opacity-40 cursor-not-allowed"
                      )}
                      onClick={() => item.isDirectory && handleNavigate(item.path)}
                    >
                      {item.isDirectory ? (
                        item.name === ".." ? (
                          <ChevronUp className="h-4 w-4 text-muted-foreground" />
                        ) : (
                          <Folder className="h-4 w-4 text-blue-500" />
                        )
                      ) : (
                        <FileText className="h-4 w-4 text-muted-foreground" />
                      )}
                      <span className={cn("flex-1 truncate", item.name === ".." && "text-muted-foreground italic")}>
                        {item.name === ".." ? "Go up one level" : item.name}
                      </span>
                      {item.isDirectory && item.name !== ".." && (
                        <Button
                          size="sm"
                          variant="secondary"
                          className="h-7 px-3 text-xs"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectFolder(item.path);
                          }}
                        >
                          <Check className="h-3 w-3 mr-1" />
                          Select
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>

            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setShowBrowser(false)}>
                Cancel
              </Button>
              {currentPath && (
                <Button onClick={() => handleSelectFolder(currentPath)}>
                  <Check className="h-4 w-4 mr-2" />
                  Select Current Folder
                </Button>
              )}
            </DialogFooter>
          </div>
        ) : (
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6 py-2">
              <FormField
                control={form.control}
                name="folderPath"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-sm font-medium">
                      Folder Path <span className="text-destructive">*</span>
                    </FormLabel>
                    <div className="flex gap-2">
                      <FormControl>
                        <Input
                          placeholder="Click Browse to select a folder..."
                          {...field}
                          className="font-mono text-sm h-11 bg-muted/30"
                          readOnly
                        />
                      </FormControl>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={handleBrowseClick}
                        className="h-11 px-4"
                      >
                        <FolderOpen className="h-4 w-4 mr-2" />
                        Browse
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Select the folder containing your raw CSV sensor data files
                    </p>
                    <FormMessage />
                  </FormItem>
                )}
              />

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
                          {...field}
                          className="h-11"
                        />
                      </FormControl>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={() => {
                          const folderPath = form.getValues("folderPath");
                          if (folderPath) {
                            suggestLabelMutation.mutate(folderPath);
                          }
                        }}
                        disabled={!form.watch("folderPath") || suggestLabelMutation.isPending}
                        className="h-11 px-3"
                        title="Generate label from folder name"
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
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={ingestMutation.isPending || !form.watch("folderPath") || !form.watch("label")}
                  className="min-w-[140px]"
                >
                  {ingestMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Starting...
                    </>
                  ) : (
                    <>
                      <Database className="mr-2 h-4 w-4" />
                      Process Data
                    </>
                  )}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        )}
      </DialogContent>
    </Dialog>
  );
}
