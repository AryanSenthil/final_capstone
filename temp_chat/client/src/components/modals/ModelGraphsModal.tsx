import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Model } from '@/lib/mockData';
import { X } from 'lucide-react';

interface ModelGraphsModalProps {
  model: Model | null;
  isOpen: boolean;
  onClose: () => void;
}

export function ModelGraphsModal({ model, isOpen, onClose }: ModelGraphsModalProps) {
  if (!model) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl bg-card border-border">
        <DialogHeader>
          <DialogTitle className="text-lg font-display">{model.name} - Training Graphs</DialogTitle>
        </DialogHeader>
        
        <div className="grid grid-cols-3 gap-4 mt-6">
          {/* Accuracy Graph Placeholder */}
          <div className="aspect-square bg-secondary/30 rounded-xl border border-border flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl font-mono font-bold text-primary mb-2">{model.accuracy}%</div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Accuracy</div>
            </div>
          </div>

          {/* Loss Graph Placeholder */}
          <div className="aspect-square bg-secondary/30 rounded-xl border border-border flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl font-mono font-bold text-accent mb-2">{model.loss.toFixed(3)}</div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Loss</div>
            </div>
          </div>

          {/* Confusion Matrix Placeholder */}
          <div className="aspect-square bg-secondary/30 rounded-xl border border-border flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto bg-background rounded mb-2 border border-border/50"></div>
              <div className="text-xs text-muted-foreground uppercase tracking-wider">Confusion Matrix</div>
            </div>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
          <div className="p-3 bg-secondary/20 rounded-lg border border-border/50">
            <div className="text-muted-foreground text-xs uppercase tracking-wider mb-1">Architecture</div>
            <div className="font-mono text-foreground">{model.architecture}</div>
          </div>
          <div className="p-3 bg-secondary/20 rounded-lg border border-border/50">
            <div className="text-muted-foreground text-xs uppercase tracking-wider mb-1">Trained</div>
            <div className="font-mono text-foreground">{model.trainingDate}</div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
