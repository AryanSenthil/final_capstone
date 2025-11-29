import { Check, Loader2, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

export type TrainingStatus = 'idle' | 'training' | 'complete' | 'error';

interface TrainingProgressProps {
  status: TrainingStatus;
  currentStep: number;
  currentEpoch?: number;
  totalEpochs?: number;
}

export function TrainingProgress({ status, currentStep, currentEpoch, totalEpochs }: TrainingProgressProps) {
  const steps = [
    { id: 1, label: "Prep", fullLabel: "Preparing Data" },
    { id: 2, label: "Build", fullLabel: "Building Model" },
    { id: 3, label: "Train", fullLabel: "Training Loop" },
  ];

  const getStepState = (stepId: number) => {
    if (status === 'idle') return 'pending';
    if (status === 'complete') return 'complete';
    if (status === 'error' && stepId === currentStep) return 'error';
    if (stepId < currentStep) return 'complete';
    if (stepId === currentStep) return 'active';
    return 'pending';
  };

  return (
    <div className="bg-muted/30 rounded-xl p-5 border border-border/50">
      <div className="flex items-center justify-between relative mb-6 px-4">
        {/* Connecting Line */}
        <div className="absolute left-8 right-8 top-[14px] h-[2px] bg-muted -z-10" />

        {steps.map((step) => {
           const stepState = getStepState(step.id);
           return (
             <div key={step.id} className="flex flex-col items-center gap-2 bg-transparent">
               <motion.div
                 initial={false}
                 animate={{
                   scale: stepState === 'active' ? 1.15 : 1,
                   borderColor: stepState === 'active' || stepState === 'complete' ? 'var(--color-primary)' : 'var(--color-muted)',
                   backgroundColor: stepState === 'complete' ? 'var(--color-primary)' : 'var(--color-background)'
                 }}
                 className={cn(
                   "w-8 h-8 rounded-full border-2 flex items-center justify-center transition-colors duration-300 z-10 shadow-sm",
                   stepState === 'error' && "border-destructive text-destructive"
                 )}
               >
                 {stepState === 'complete' && <Check size={14} className="text-primary-foreground" />}
                 {stepState === 'active' && <Loader2 size={14} className="animate-spin text-primary" />}
                 {stepState === 'error' && <AlertCircle size={14} />}
                 {stepState === 'pending' && <div className="w-2 h-2 rounded-full bg-muted-foreground/20" />}
               </motion.div>
               <span className={cn(
                 "text-xs font-medium transition-colors duration-300",
                 stepState === 'active' ? "text-primary font-bold" : "text-muted-foreground",
                 stepState === 'complete' && "text-primary"
               )}>
                 {step.label}
               </span>
             </div>
           );
        })}
      </div>

      <div className="text-center h-8 flex items-center justify-center bg-background/50 rounded-lg border border-border/50 py-2">
        {status === 'idle' && (
          <p className="text-sm text-muted-foreground">Ready to start training session</p>
        )}
        {status === 'training' && (
          <p className="text-sm font-medium text-foreground animate-pulse flex items-center gap-2">
            <Loader2 size={14} className="animate-spin" />
            {steps[currentStep - 1]?.fullLabel}...
            {currentStep === 3 && currentEpoch !== undefined && totalEpochs !== undefined && (
              <span className="font-mono opacity-75 bg-muted px-1.5 py-0.5 rounded text-xs">
                Epoch {currentEpoch}/{totalEpochs}
              </span>
            )}
          </p>
        )}
        {status === 'complete' && (
          <p className="text-sm font-medium text-emerald-600 flex items-center justify-center gap-2">
            <Check size={16} />
            Training successfully completed
          </p>
        )}
      </div>
    </div>
  );
}
