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
    <div className="space-y-1.5">
      <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
        <Layers size={10} /> Architecture
      </h3>

      <div className="flex flex-col gap-1.5">
        <TooltipProvider>
          <Tooltip delayDuration={300}>
            <TooltipTrigger asChild>
              <button
                onClick={() => onChange("CNN")}
                className={cn(
                  "relative flex items-center gap-3 px-3 py-2 rounded-lg border transition-all duration-200 text-left",
                  selected === "CNN"
                    ? "border-primary bg-primary/5 shadow-sm ring-0"
                    : "border-border bg-card hover:border-primary/30 hover:bg-accent/50"
                )}
              >
                <div className={cn(
                  "p-1.5 rounded-md transition-colors shrink-0",
                  selected === "CNN" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                )}>
                  <Layers size={14} />
                </div>

                <div className="flex-1 min-w-0">
                  <span className={cn(
                    "font-bold text-xs",
                    selected === "CNN" ? "text-primary" : "text-foreground"
                  )}>CNN</span>
                  <span className="text-[10px] text-muted-foreground ml-2">Fast training, good baseline</span>
                </div>
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" className="text-xs max-w-[200px]">
              Convolutional Neural Network
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        <TooltipProvider>
          <Tooltip delayDuration={300}>
            <TooltipTrigger asChild>
              <button
                onClick={() => onChange("ResNet")}
                className={cn(
                  "relative flex items-center gap-3 px-3 py-2 rounded-lg border transition-all duration-200 text-left",
                  selected === "ResNet"
                    ? "border-primary bg-primary/5 shadow-sm ring-0"
                    : "border-border bg-card hover:border-primary/30 hover:bg-accent/50"
                )}
              >
                <div className={cn(
                  "p-1.5 rounded-md transition-colors shrink-0",
                  selected === "ResNet" ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
                )}>
                  <Box size={14} />
                </div>

                <div className="flex-1 min-w-0">
                  <span className={cn(
                    "font-bold text-xs",
                    selected === "ResNet" ? "text-primary" : "text-foreground"
                  )}>ResNet</span>
                  <span className="text-[10px] text-muted-foreground ml-2">Higher accuracy, longer training</span>
                </div>
              </button>
            </TooltipTrigger>
            <TooltipContent side="right" className="text-xs max-w-[200px]">
              Residual Network
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
}
