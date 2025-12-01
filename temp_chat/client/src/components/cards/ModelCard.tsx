import { Model } from '@/lib/mockData';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Brain, Play, FileText, Trash2 } from 'lucide-react';

interface ModelCardProps {
  model: Model;
  onViewGraphs?: (model: Model) => void;
}

export function ModelCard({ model, onViewGraphs }: ModelCardProps) {
  return (
    <Card className="w-full bg-card border-border/50 shadow-sm hover:shadow-md transition-all duration-200 group" data-testid={`card-model-${model.id}`}>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-md bg-accent/10 text-accent">
              <Brain className="w-4 h-4" />
            </div>
            <div>
              <CardTitle className="text-base font-medium text-foreground font-display">{model.name}</CardTitle>
              <p className="text-xs text-muted-foreground font-mono">{model.architecture}</p>
            </div>
          </div>
          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="icon" className="h-7 w-7 hover:bg-primary/10 hover:text-primary" title="View Graphs" onClick={() => onViewGraphs?.(model)}>
              <Play className="w-3.5 h-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7 hover:bg-secondary/20" title="View Report">
              <FileText className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 text-xs mt-2">
          <div className="bg-secondary/30 p-2 rounded border border-border/50">
            <span className="text-muted-foreground block mb-1">Accuracy</span>
            <span className="font-mono font-bold text-primary text-lg">{model.accuracy}%</span>
          </div>
          <div className="bg-secondary/30 p-2 rounded border border-border/50">
            <span className="text-muted-foreground block mb-1">Loss</span>
            <span className="font-mono font-bold text-accent text-lg">{model.loss.toFixed(3)}</span>
          </div>
        </div>
        <div className="mt-3 flex justify-between items-center">
           <span className="text-[10px] text-muted-foreground uppercase tracking-wider">
             Trained {model.trainingDate}
           </span>
        </div>
      </CardContent>
    </Card>
  );
}
