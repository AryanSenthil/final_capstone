import { Layers, Box } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export type ArchitectureType = "CNN" | "ResNet";

interface ArchitectureSelectorProps {
  selected: ArchitectureType;
  onChange: (arch: ArchitectureType) => void;
}

export function ArchitectureSelector({ selected, onChange }: ArchitectureSelectorProps) {
  return (
    <div className="space-y-2">
       <div className="flex items-center justify-between mb-1">
        <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Model Architecture</h3>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <TooltipProvider>
          <Tooltip delayDuration={300}>
            <TooltipTrigger asChild>
              <button
                onClick={() => onChange("CNN")}
                className={cn(
                  "relative flex items-center gap-3 p-3 rounded-lg border transition-all duration-200 text-left h-16",
                  selected === "CNN"
                    ? "border-primary bg-primary/5 shadow-sm ring-0"
                    : "border-border bg-card hover:border-primary/30 hover:bg-accent/50"
                )}
              >
                <div className={cn(
                  "p-2 rounded-md transition-colors shrink-0",
                  selected === "CNN" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                )}>
                  <Layers size={18} />
                </div>

                <div className="flex flex-col min-w-0">
                  <span className={cn(
                    "font-bold text-sm leading-none mb-1",
                    selected === "CNN" ? "text-primary" : "text-foreground"
                  )}>CNN</span>
                  <span className="text-[10px] text-muted-foreground leading-tight truncate">Fast Baseline</span>
                </div>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs max-w-[200px]">
              Convolutional Neural Network - Faster training, good baseline
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <TooltipProvider>
          <Tooltip delayDuration={300}>
            <TooltipTrigger asChild>
              <button
                onClick={() => onChange("ResNet")}
                className={cn(
                  "relative flex items-center gap-3 p-3 rounded-lg border transition-all duration-200 text-left h-16",
                  selected === "ResNet"
                    ? "border-primary bg-primary/5 shadow-sm ring-0"
                    : "border-border bg-card hover:border-primary/30 hover:bg-accent/50"
                )}
              >
                <div className={cn(
                  "p-2 rounded-md transition-colors shrink-0",
                  selected === "ResNet" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                )}>
                  <Box size={18} />
                </div>

                <div className="flex flex-col min-w-0">
                  <span className={cn(
                    "font-bold text-sm leading-none mb-1",
                    selected === "ResNet" ? "text-primary" : "text-foreground"
                  )}>ResNet</span>
                   <span className="text-[10px] text-muted-foreground leading-tight truncate">High Accuracy</span>
                </div>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="text-xs max-w-[200px]">
              Residual Network - Better accuracy, longer training
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
}
