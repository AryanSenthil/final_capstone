import { Database, Brain, PlayCircle, FileBarChart } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface FloatingActionsProps {
  onAction: (action: string) => void;
}

export function FloatingActions({ onAction }: FloatingActionsProps) {
  const actions = [
    { icon: <Database className="w-4 h-4" />, label: 'View Datasets', action: 'What datasets do we have?' },
    { icon: <Brain className="w-4 h-4" />, label: 'View Models', action: 'Show me the models' },
    { icon: <PlayCircle className="w-4 h-4" />, label: 'Train Model', action: 'Train a model on crushcore and disbond' },
    { icon: <FileBarChart className="w-4 h-4" />, label: 'Run Inference', action: 'Run inference' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 w-full">
      {actions.map((action) => (
        <Button
          key={action.label}
          onClick={() => onAction(action.action)}
          className="h-auto flex flex-col items-center justify-center py-4 px-3 bg-secondary/40 hover:bg-secondary/60 border border-border rounded-xl transition-all hover:shadow-md group"
          variant="ghost"
          data-testid={`btn-action-${action.label.toLowerCase().replace(/\s+/g, '-')}`}
        >
          <div className="p-2 bg-primary/10 rounded-lg mb-2 text-primary group-hover:bg-primary/20 transition-colors">
            {action.icon}
          </div>
          <span className="text-xs font-medium text-foreground text-center">{action.label}</span>
        </Button>
      ))}
    </div>
  );
}
