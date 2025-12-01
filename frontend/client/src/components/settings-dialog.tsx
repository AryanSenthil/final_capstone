import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Settings, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { cn } from "@/lib/utils";

interface SettingsData {
  time_window: number;
  sampling_rate: number;
  epochs: number;
  validation_split: number;
}

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Time window options with corresponding sampling rates
const TIME_WINDOW_OPTIONS = [
  { value: 1, label: "1 second", samplingRate: 16000, description: "Highest resolution" },
  { value: 2, label: "2 seconds", samplingRate: 8000, description: "High resolution" },
  { value: 5, label: "5 seconds", samplingRate: 3200, description: "Balanced" },
  { value: 10, label: "10 seconds", samplingRate: 1600, description: "More context" },
];

// Training duration presets
const TRAINING_DURATION_OPTIONS = [
  { value: "quick", label: "Quick", epochs: 300, description: "Fast iteration (~5 min)" },
  { value: "standard", label: "Standard", epochs: 1000, description: "Balanced (~15 min)" },
  { value: "thorough", label: "Thorough", epochs: 2000, description: "Best results (~30 min)" },
];

// Data split options
const DATA_SPLIT_OPTIONS = [
  { value: 0.1, label: "10%", description: "More training data" },
  { value: 0.15, label: "15%", description: "Balanced" },
  { value: 0.2, label: "20%", description: "Standard" },
  { value: 0.3, label: "30%", description: "More validation" },
];

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Local state for selections
  const [selectedTimeWindow, setSelectedTimeWindow] = useState<number>(10);
  const [selectedDuration, setSelectedDuration] = useState<string>("standard");
  const [selectedSplit, setSelectedSplit] = useState<number>(0.2);
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch current settings
  const { data: settings, isLoading } = useQuery<SettingsData>({
    queryKey: ["/api/settings"],
    enabled: open,
  });

  // Update local state when settings load
  useEffect(() => {
    if (settings) {
      setSelectedTimeWindow(settings.time_window);
      setSelectedSplit(settings.validation_split);
      // Determine duration preset from epochs
      const durationPreset = TRAINING_DURATION_OPTIONS.find(
        (opt) => opt.epochs === settings.epochs
      );
      setSelectedDuration(durationPreset?.value || "standard");
      setHasChanges(false);
    }
  }, [settings]);

  // Track changes
  useEffect(() => {
    if (settings) {
      const durationPreset = TRAINING_DURATION_OPTIONS.find(
        (opt) => opt.epochs === settings.epochs
      );
      const changed =
        selectedTimeWindow !== settings.time_window ||
        selectedSplit !== settings.validation_split ||
        selectedDuration !== (durationPreset?.value || "standard");
      setHasChanges(changed);
    }
  }, [selectedTimeWindow, selectedDuration, selectedSplit, settings]);

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async () => {
      const updates: Record<string, unknown> = {};

      if (settings) {
        if (selectedTimeWindow !== settings.time_window) {
          updates.time_window = selectedTimeWindow;
        }
        const currentDuration = TRAINING_DURATION_OPTIONS.find(
          (opt) => opt.epochs === settings.epochs
        )?.value;
        if (selectedDuration !== currentDuration) {
          updates.training_duration = selectedDuration;
        }
        if (selectedSplit !== settings.validation_split) {
          updates.data_split = selectedSplit;
        }
      }

      const response = await apiRequest("PATCH", "/api/settings", updates);
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/settings"] });
      toast({
        title: "Settings Saved",
        description: "Your training settings have been updated.",
        duration: 3000,
      });
      onOpenChange(false);
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to Save Settings",
        description: error.message || "Please try again.",
        variant: "destructive",
        duration: 5000,
      });
    },
  });

  const handleSave = () => {
    saveMutation.mutate();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[540px]">
        <DialogHeader>
          <DialogTitle className="text-lg font-semibold flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Settings
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-4 py-2">
            {/* Time Window */}
            <div className="space-y-2">
              <Label className="text-xs font-medium text-muted-foreground">Time Window</Label>
              <div className="grid grid-cols-4 gap-1.5">
                {TIME_WINDOW_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setSelectedTimeWindow(option.value)}
                    className={cn(
                      "relative flex flex-col items-center p-2 rounded-md border transition-all text-xs",
                      selectedTimeWindow === option.value
                        ? "border-primary bg-primary/5 font-medium"
                        : "border-border hover:border-primary/50"
                    )}
                  >
                    <span>{option.value}s</span>
                    <span className="text-[10px] text-muted-foreground">
                      {option.samplingRate.toLocaleString()} Hz
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Training Duration */}
            <div className="space-y-2">
              <Label className="text-xs font-medium text-muted-foreground">Training Duration</Label>
              <div className="grid grid-cols-3 gap-1.5">
                {TRAINING_DURATION_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setSelectedDuration(option.value)}
                    className={cn(
                      "relative flex flex-col items-center p-2 rounded-md border transition-all text-xs",
                      selectedDuration === option.value
                        ? "border-primary bg-primary/5 font-medium"
                        : "border-border hover:border-primary/50"
                    )}
                  >
                    <span>{option.label}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {option.epochs} epochs
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Data Split */}
            <div className="space-y-2">
              <Label className="text-xs font-medium text-muted-foreground">Validation Split</Label>
              <div className="grid grid-cols-4 gap-1.5">
                {DATA_SPLIT_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setSelectedSplit(option.value)}
                    className={cn(
                      "relative flex flex-col items-center p-2 rounded-md border transition-all text-xs",
                      selectedSplit === option.value
                        ? "border-primary bg-primary/5 font-medium"
                        : "border-border hover:border-primary/50"
                    )}
                  >
                    <span>{option.label}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            className="hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={!hasChanges || saveMutation.isPending}
            className="hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
          >
            {saveMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              "Save Changes"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
