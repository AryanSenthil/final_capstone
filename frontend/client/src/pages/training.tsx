import { useState, useEffect, useRef } from "react";
import { useMutation } from "@tanstack/react-query";
import { FolderSelector, type FolderSelection } from "@/components/training/FolderSelector";
import { ArchitectureSelector, type ArchitectureType } from "@/components/training/ArchitectureSelector";
import { TrainingProgress, type TrainingStatus } from "@/components/training/TrainingProgress";
import { GraphCarousel } from "@/components/training/GraphCarousel";
import { ReportModal } from "@/components/training/ReportModal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Rocket, Square, FileText, RotateCcw, AlertCircle, CheckCircle2, Type, Download, Activity } from "lucide-react";
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
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

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

  const resetTraining = () => {
    setStatus("idle");
    setCurrentStep(0);
    setModelName("");
    setJobId(null);
    setTrainingResult(null);
    setCurrentEpoch(undefined);
    setTotalEpochs(undefined);
  };

  return (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-8rem)] -m-4 sm:-m-6">
      {/* LEFT PANEL (Configuration) */}
      <div className="w-full lg:w-[420px] xl:w-[460px] flex-shrink-0 border-r border-border bg-background flex flex-col h-full overflow-y-auto lg:overflow-hidden z-10 shadow-xl shadow-black/5">
        <div className="p-6 flex flex-col h-full gap-6">
          {/* Header */}
          <div className="shrink-0 space-y-1 pb-2 border-b border-border/50">
             <h2 className="text-xl font-bold tracking-tight">Experiment Setup</h2>
             <p className="text-xs text-muted-foreground">Define parameters for new run</p>
          </div>

          {/* Scrollable Configuration Area */}
          <div className="flex-1 overflow-y-auto pr-2 space-y-6 min-h-0 py-2">

            {/* Model Name Input */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                 <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
                   <Type size={12} /> Model Identifier
                 </h3>
                 {modelNameError && <span className="text-xs text-destructive font-medium">Required</span>}
              </div>
              <Input
                placeholder="e.g., resnet50_batch_v2"
                value={modelName}
                onChange={(e) => {
                  setModelName(e.target.value);
                  if (e.target.value) setModelNameError(false);
                }}
                className={cn(
                  "transition-all",
                  modelNameError ? "border-destructive ring-destructive/20" : "focus-visible:ring-primary/20"
                )}
                disabled={status === "training"}
              />
            </div>

            <div className="space-y-2">
              <FolderSelector
                selectedFolders={selectedFolders}
                onSelectionChange={setSelectedFolders}
              />
            </div>

            <div className="h-px bg-border/60 w-full" />

            <div className="space-y-2">
              <ArchitectureSelector
                selected={architecture}
                onChange={setArchitecture}
              />
            </div>

            <div className="h-px bg-border/60 w-full" />

            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Status Monitor</h3>
              <TrainingProgress
                status={status}
                currentStep={currentStep}
                currentEpoch={currentEpoch}
                totalEpochs={totalEpochs}
              />
            </div>
          </div>

          {/* Fixed Footer Actions */}
          <div className="shrink-0 pt-4 mt-auto">
            {status === "idle" && (
              <Button
                size="lg"
                className="w-full gap-3 shadow-lg shadow-primary/20 h-12 text-base font-semibold rounded-lg transition-all hover:translate-y-[-1px]"
                onClick={startTraining}
                disabled={selectedFolders.length === 0 || startMutation.isPending}
              >
                <Rocket size={18} />
                {startMutation.isPending ? "Starting..." : "Start Training"}
              </Button>
            )}

            {status === "training" && (
              <Button
                size="lg"
                variant="destructive"
                className="w-full gap-3 h-12 text-base font-semibold rounded-lg shadow-lg shadow-destructive/20"
                onClick={stopTraining}
              >
                <Square size={18} fill="currentColor" />
                Stop Training
              </Button>
            )}

            {(status === "complete" || status === "error") && (
              <div className="flex flex-col gap-2">
                <div className="flex gap-2">
                  <Button
                    size="lg"
                    variant="outline"
                    className="flex-1 gap-2 h-12 text-base font-semibold rounded-lg border-primary/20 hover:bg-primary/5 hover:text-primary"
                    onClick={resetTraining}
                  >
                    <RotateCcw size={18} />
                    Start New Run
                  </Button>

                  {status === "complete" && trainingResult?.report_path && (
                    <Button
                      size="lg"
                      className="flex-1 gap-2 h-12 text-base font-semibold rounded-lg shadow-lg shadow-primary/10"
                      onClick={() => setShowReport(true)}
                    >
                      <FileText size={18} />
                      View Report
                    </Button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* RIGHT PANEL (Visuals) */}
      <div className="flex-1 bg-secondary/30 flex flex-col relative overflow-hidden">
         {/* Top Status Banner Area */}
         <div className="h-20 shrink-0 px-8 pt-6 pb-2 flex items-center justify-between z-20 border-b border-transparent">
            <div className="flex-1 relative h-14">
               {/* Placeholder / Empty State */}
               <div className={cn(
                 "absolute inset-0 bg-background/40 border border-border/50 rounded-lg flex items-center px-6 transition-opacity duration-300",
                 status === "idle" || status === "training" ? "opacity-100" : "opacity-0 pointer-events-none"
               )}>
                  <div className="flex items-center gap-3 text-muted-foreground/50">
                     <Activity size={18} />
                     <span className="text-sm font-medium">
                       {status === "idle" ? "Ready for training sequence" : "Training in progress..."}
                     </span>
                  </div>
               </div>

               <AnimatePresence mode="wait">
                  {status === "complete" && trainingResult && (
                     <motion.div
                       initial={{ opacity: 0, y: 10 }}
                       animate={{ opacity: 1, y: 0 }}
                       exit={{ opacity: 0, y: -10 }}
                       className="absolute inset-0 bg-emerald-500 text-white px-6 rounded-lg shadow-lg flex items-center justify-between gap-4 w-full"
                     >
                       <div className="flex items-center gap-4">
                         <div className="bg-white/20 p-1.5 rounded-full">
                           <CheckCircle2 size={20} className="text-white" />
                         </div>
                         <div>
                           <h3 className="font-bold text-sm">Training Successful</h3>
                           <p className="text-xs text-white/90">
                             Accuracy: {trainingResult.accuracy} | Loss: {trainingResult.loss}
                           </p>
                         </div>
                       </div>

                       <div className="flex items-center gap-2">
                         {trainingResult.report_path && (
                           <Button
                             size="sm"
                             variant="ghost"
                             className="text-white hover:bg-white/20 h-8 px-3 border border-white/20"
                             onClick={() => setShowReport(true)}
                           >
                             <FileText size={14} className="mr-2" /> View Report
                           </Button>
                         )}
                         <Button
                           size="sm"
                           variant="ghost"
                           className="text-white hover:bg-white/20 h-8 px-3 border border-white/20"
                         >
                           <Download size={14} className="mr-2" /> Download
                         </Button>
                       </div>
                     </motion.div>
                  )}

                  {status === "error" && (
                     <motion.div
                       initial={{ opacity: 0, y: 10 }}
                       animate={{ opacity: 1, y: 0 }}
                       exit={{ opacity: 0, y: -10 }}
                       className="absolute inset-0 bg-destructive text-white px-6 rounded-lg shadow-lg flex items-center gap-4 w-full"
                     >
                       <div className="bg-white/20 p-1.5 rounded-full">
                         <AlertCircle size={20} className="text-white" />
                       </div>
                       <div>
                         <h3 className="font-bold text-sm">Training Failed</h3>
                         <p className="text-xs text-white/90">Check console for details</p>
                       </div>
                     </motion.div>
                  )}
               </AnimatePresence>
            </div>

            {/* Run ID Display */}
            <div className="ml-4">
               <div
                 className="text-muted-foreground font-mono text-sm bg-background/50 px-3 py-2 rounded border border-border/50 backdrop-blur h-14 flex items-center"
               >
                 <span className="text-xs text-muted-foreground mr-2">ID:</span>
                 {modelName || "—"}
               </div>
            </div>
         </div>

         {/* Main Graph Area */}
         <div className="flex-1 p-6 lg:p-8 pt-2 overflow-y-auto">
           <div className="bg-card rounded-2xl border shadow-sm h-full p-6 lg:p-8 flex flex-col max-w-7xl mx-auto relative">
              <GraphCarousel hasData={status === "complete"} />
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
