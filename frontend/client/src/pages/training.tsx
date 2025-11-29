import { useState, useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderSelector, type FolderSelection } from "@/components/training/FolderSelector";
import { ArchitectureSelector, type ArchitectureType } from "@/components/training/ArchitectureSelector";
import { TrainingProgress, type TrainingStatus } from "@/components/training/TrainingProgress";
import { GraphCarousel } from "@/components/training/GraphCarousel";
import { ReportModal } from "@/components/training/ReportModal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Rocket, Square, FileText, RotateCcw, AlertCircle, CheckCircle2, Type, Download, Activity, Wand2, Loader2 } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/queryClient";

interface TrainingResult {
  accuracy: string;
  loss: string;
  model_path: string;
  report_path: string | null;
}

interface TrainingStateResponse {
  model_name: string;
  selected_labels: string[];
  architecture: string;
  last_updated: string;
  // Persisted training result
  status: TrainingStatus;
  job_id: string | null;
  result: TrainingResult | null;
}

interface DatasetMetadata {
  id: string;
  label: string;
  chunks: number;
  measurement: string;
  unit: string;
}

interface GraphData {
  accuracy?: string;
  loss?: string;
  confusion_matrix?: string;
}

export default function TrainingPage() {
  // State
  const [selectedFolders, setSelectedFolders] = useState<FolderSelection[]>([]);
  const [architecture, setArchitecture] = useState<ArchitectureType>("CNN");
  const [status, setStatus] = useState<TrainingStatus>("idle");
  const [currentStep, setCurrentStep] = useState(0);
  const [showReport, setShowReport] = useState(false);
  const [modelName, setModelName] = useState("");
  const [modelNameError, setModelNameError] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [trainingResult, setTrainingResult] = useState<TrainingResult | null>(null);
  const [currentEpoch, setCurrentEpoch] = useState<number | undefined>();
  const [totalEpochs, setTotalEpochs] = useState<number | undefined>();
  const [stateLoaded, setStateLoaded] = useState(false);
  const [graphs, setGraphs] = useState<GraphData | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const queryClient = useQueryClient();

  // Load saved training state - track isFetching to avoid cache issues
  const { data: savedState, isFetching: isFetchingState } = useQuery<TrainingStateResponse>({
    queryKey: ["/api/training/state"],
    staleTime: 0, // Always refetch when component mounts
    refetchOnMount: "always",
  });

  // Load labels for restoring selections
  const { data: labels } = useQuery<DatasetMetadata[]>({
    queryKey: ["/api/labels"],
  });

  // Restore state from backend on mount - WAIT for fresh data (not cached)
  useEffect(() => {
    // Must wait for isFetching to be false to ensure we have fresh data, not stale cache
    if (!isFetchingState && savedState && labels && !stateLoaded) {
      if (savedState.model_name) {
        setModelName(savedState.model_name);
      }
      if (savedState.architecture) {
        setArchitecture(savedState.architecture as ArchitectureType);
      }
      if (savedState.selected_labels && savedState.selected_labels.length > 0) {
        // Restore folder selections from labels
        const restored = savedState.selected_labels
          .map(labelName => {
            const labelData = labels.find(l => l.label === labelName);
            if (labelData) {
              return {
                path: labelData.label,
                name: labelData.label,
                fileCount: labelData.chunks,
                selected: true,
                metadata: labelData,
              } as FolderSelection;
            }
            return null;
          })
          .filter(Boolean) as FolderSelection[];
        if (restored.length > 0) {
          setSelectedFolders(restored);
        }
      }
      // Restore completed training state
      if (savedState.status === "complete" && savedState.result) {
        setStatus("complete");
        setCurrentStep(4);
        setTrainingResult(savedState.result);
        setJobId(savedState.job_id);
        // Fetch graphs for completed model
        const fetchGraphs = async () => {
          try {
            const graphsResponse = await fetch(`/api/models/${encodeURIComponent(savedState.model_name)}/graphs`);
            if (graphsResponse.ok) {
              const graphsData = await graphsResponse.json();
              setGraphs(graphsData);
            }
          } catch (e) {
            console.error("Failed to fetch graphs:", e);
          }
        };
        fetchGraphs();
      }
      setStateLoaded(true);
    }
  }, [isFetchingState, savedState, labels, stateLoaded]);

  // Backend saves state when training completes - no frontend save needed

  // Generate model name mutation
  const generateNameMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", "/api/suggest-model-name", {
        labels: selectedFolders.map(f => f.name),
        architecture: architecture,
      });
      return response.json();
    },
    onSuccess: (data) => {
      if (data.success && data.name) {
        setModelName(data.name);
        setModelNameError(false);
      }
    },
    onError: () => {
      toast({
        title: "Could not generate name",
        description: "Please enter a name manually.",
        variant: "destructive",
        duration: 3000,
      });
    },
  });

  // Start training mutation
  const startMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", "/api/training/start", {
        model_name: modelName,
        labels: selectedFolders.map(f => f.name),
        architecture: architecture,
        generate_report: true,
        use_llm: true,
      });
      return response.json();
    },
    onSuccess: (data) => {
      setJobId(data.job_id);
      setStatus("training");
      setCurrentStep(1);
      toast({
        title: "Training Started",
        description: data.message,
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to Start Training",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Poll for training status
  useEffect(() => {
    if (jobId && status === "training") {
      const pollStatus = async () => {
        try {
          const response = await fetch(`/api/training/status/${jobId}`);
          if (response.ok) {
            const data = await response.json();

            // Map API status to our TrainingStatus
            if (data.status === "preparing") {
              setCurrentStep(1);
            } else if (data.status === "building") {
              setCurrentStep(2);
            } else if (data.status === "training") {
              setCurrentStep(3);
              setCurrentEpoch(data.current_epoch);
              setTotalEpochs(data.total_epochs);
            } else if (data.status === "complete") {
              setStatus("complete");
              setCurrentStep(4);
              setTrainingResult(data.result);
              toast({
                title: "Training Complete",
                description: `Model ${modelName} saved successfully.`,
              });
              if (pollingRef.current) {
                clearInterval(pollingRef.current);
              }
              // Fetch model graphs
              try {
                const graphsResponse = await fetch(`/api/models/${encodeURIComponent(modelName)}/graphs`);
                if (graphsResponse.ok) {
                  const graphsData = await graphsResponse.json();
                  setGraphs(graphsData);
                }
              } catch (e) {
                console.error("Failed to fetch graphs:", e);
              }
              // Backend saves state when training completes - invalidate query to get fresh state
              queryClient.invalidateQueries({ queryKey: ["/api/training/state"] });
            } else if (data.status === "error") {
              setStatus("error");
              toast({
                title: "Training Failed",
                description: data.error_message || "Unknown error occurred",
                variant: "destructive",
              });
              if (pollingRef.current) {
                clearInterval(pollingRef.current);
              }
            }
          }
        } catch (error) {
          console.error("Error polling status:", error);
        }
      };

      pollingRef.current = setInterval(pollStatus, 2000);
      pollStatus(); // Initial poll

      return () => {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
        }
      };
    }
  }, [jobId, status, modelName]);

  // Handlers
  const startTraining = () => {
    if (!modelName.trim()) {
      setModelNameError(true);
      toast({
        title: "Missing Model Name",
        description: "Please enter a name for your model before starting.",
        variant: "destructive"
      });
      return;
    }
    if (selectedFolders.length === 0) {
      toast({
        title: "No Data Selected",
        description: "Please select at least one dataset to train on.",
        variant: "destructive"
      });
      return;
    }

    setModelNameError(false);
    startMutation.mutate();
  };

  const stopTraining = async () => {
    if (jobId) {
      try {
        await apiRequest("POST", `/api/training/stop/${jobId}`);
      } catch (error) {
        console.error("Error stopping training:", error);
      }
    }
    setStatus("idle");
    setCurrentStep(0);
    setJobId(null);
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
    }
    toast({
      title: "Training Aborted",
      description: "Process stopped by user.",
      variant: "destructive",
    });
  };

  const resetTraining = async () => {
    setStatus("idle");
    setCurrentStep(0);
    setModelName("");
    setJobId(null);
    setTrainingResult(null);
    setCurrentEpoch(undefined);
    setTotalEpochs(undefined);
    setGraphs(null);
    setSelectedFolders([]);
    // Clear persisted state when starting new run
    try {
      await fetch("/api/training/state", { method: "DELETE" });
    } catch {}
  };

  const handleDownloadReport = async () => {
    if (!trainingResult?.report_path) {
      toast({
        title: "No Report Available",
        description: "Report has not been generated yet.",
        variant: "destructive",
      });
      return;
    }

    try {
      // Extract filename from report_path
      const filename = trainingResult.report_path.split('/').pop() || 'report.pdf';

      // Fetch the report PDF from the API using query parameter
      const response = await fetch(`/api/training/report/download?path=${encodeURIComponent(trainingResult.report_path)}`);

      if (!response.ok) {
        throw new Error('Failed to download report');
      }

      // Get the blob and create a download link
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast({
        title: "Download Started",
        description: `Downloading ${filename}`,
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: "Download Failed",
        description: "Could not download the report. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="flex h-[calc(100vh-2rem)] -m-4 sm:-m-6 lg:-m-6">
      {/* MAIN CONTENT - Single column layout */}
      <div className="flex-1 flex flex-col lg:flex-row bg-background overflow-hidden">
        {/* LEFT PANEL (Configuration + Status) */}
        <div className="w-full lg:w-[380px] xl:w-[420px] flex-shrink-0 border-r border-border bg-background flex flex-col h-full z-10">
          <div className="p-4 flex flex-col h-full gap-3 overflow-y-auto">
            {/* Header - Simple */}
            <div className="shrink-0 pb-2 border-b border-border/50">
               <h2 className="text-lg font-bold tracking-tight">Train Model</h2>
               <p className="text-[10px] text-muted-foreground">Configure and start training</p>
            </div>

            {/* Model Name Input - Compact */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                 <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                   <Type size={10} /> Model Name
                 </h3>
                 {modelNameError && <span className="text-[10px] text-destructive font-medium">Required</span>}
              </div>
              <div className="flex gap-1.5">
                <Input
                  value={modelName}
                  onChange={(e) => {
                    setModelName(e.target.value);
                    if (e.target.value) setModelNameError(false);
                  }}
                  className={cn(
                    "transition-all flex-1 h-8 text-sm",
                    modelNameError ? "border-destructive ring-destructive/20" : "focus-visible:ring-primary/20"
                  )}
                  disabled={status === "training"}
                  placeholder="Enter model name..."
                />
                <Button
                  type="button"
                  variant="secondary"
                  size="icon"
                  onClick={() => generateNameMutation.mutate()}
                  disabled={selectedFolders.length === 0 || generateNameMutation.isPending || status === "training"}
                  title="Generate name using AI"
                  className="h-8 w-8 shrink-0"
                >
                  {generateNameMutation.isPending ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Wand2 className="h-3 w-3" />
                  )}
                </Button>
              </div>
            </div>

            {/* Dataset Selection - Compact */}
            <div className="space-y-1.5">
              <FolderSelector
                selectedFolders={selectedFolders}
                onSelectionChange={setSelectedFolders}
              />
            </div>

            {/* Architecture Selection - Compact */}
            <div className="space-y-1.5">
              <ArchitectureSelector
                selected={architecture}
                onChange={setArchitecture}
              />
            </div>

            {/* Training Progress - Compact */}
            <div className="space-y-1.5 pt-2 border-t border-border/50">
              <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Status</h3>
              <TrainingProgress
                status={status}
                currentStep={currentStep}
                currentEpoch={currentEpoch}
                totalEpochs={totalEpochs}
              />
            </div>

            {/* Success Banner with Report Actions */}
            {status === "complete" && trainingResult && (
              <motion.div
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-emerald-500 text-white p-3 rounded-lg shadow-md"
              >
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 size={16} />
                  <span className="font-semibold text-sm">Training Complete</span>
                </div>
                <div className="flex items-center justify-between text-xs text-white/90 mb-3">
                  <span>Accuracy: {trainingResult.accuracy}</span>
                  <span>Loss: {trainingResult.loss}</span>
                </div>
                {trainingResult.report_path && (
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="secondary"
                      className="flex-1 h-8 text-xs bg-white/20 hover:bg-white/30 text-white border-0"
                      onClick={() => setShowReport(true)}
                    >
                      <FileText size={12} className="mr-1.5" />
                      View Report
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      className="h-8 w-8 bg-white/20 hover:bg-white/30 text-white border-0 p-0"
                      onClick={handleDownloadReport}
                      title="Download Report"
                    >
                      <Download size={12} />
                    </Button>
                  </div>
                )}
              </motion.div>
            )}

            {/* Action Buttons - Fixed at bottom */}
            <div className="shrink-0 mt-auto pt-3 space-y-2">
              {status === "idle" && (
                <Button
                  size="default"
                  className="w-full gap-2 shadow-lg shadow-primary/20 h-10 text-sm font-semibold rounded-lg transition-all hover:translate-y-[-1px]"
                  onClick={startTraining}
                  disabled={selectedFolders.length === 0 || startMutation.isPending}
                >
                  <Rocket size={16} />
                  {startMutation.isPending ? "Starting..." : "Start Training"}
                </Button>
              )}

              {status === "training" && (
                <Button
                  size="default"
                  variant="destructive"
                  className="w-full gap-2 h-10 text-sm font-semibold rounded-lg shadow-lg shadow-destructive/20"
                  onClick={stopTraining}
                >
                  <Square size={16} fill="currentColor" />
                  Stop Training
                </Button>
              )}

              {(status === "complete" || status === "error") && (
                <Button
                  size="default"
                  variant="outline"
                  className="w-full gap-1.5 h-10 text-sm font-semibold rounded-lg border-primary/20 hover:bg-primary/5 hover:text-primary"
                  onClick={resetTraining}
                >
                  <RotateCcw size={14} />
                  Start New Training
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT PANEL (Graphs) - Only visible when there's data */}
        <div className="flex-1 bg-secondary/30 flex flex-col relative overflow-hidden">
          {/* Graph Area */}
          <div className="flex-1 p-4 lg:p-6 overflow-y-auto">
            <div className="bg-card rounded-xl border shadow-sm h-full p-4 lg:p-6 flex flex-col max-w-5xl mx-auto relative">
              <GraphCarousel hasData={status === "complete"} graphs={graphs || undefined} />
            </div>
          </div>
        </div>
      </div>

      <ReportModal
        open={showReport}
        onOpenChange={setShowReport}
        modelName={modelName}
        reportPath={trainingResult?.report_path || undefined}
      />
    </div>
  );
}
