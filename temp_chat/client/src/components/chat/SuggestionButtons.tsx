import { Database, Brain, PlayCircle, FileBarChart } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SuggestionButtonsProps {
  onSelect: (action: string) => void;
}

export function SuggestionButtons({ onSelect }: SuggestionButtonsProps) {
  const suggestions = [
    { icon: <Database className="w-4 h-4" />, label: 'Datasets', action: 'What datasets do we have?' },
    { icon: <Brain className="w-4 h-4" />, label: 'Models', action: 'Show me the models' },
    { icon: <PlayCircle className="w-4 h-4" />, label: 'Train Model', action: 'Train a model on crushcore and disbond' },
    { icon: <FileBarChart className="w-4 h-4" />, label: 'Inference', action: 'Run inference' },
  ];

  return (
    <div className="flex gap-2 flex-wrap justify-center">
      {suggestions.map((suggestion) => (
        <Button
          key={suggestion.label}
          onClick={() => onSelect(suggestion.action)}
          variant="outline"
          className="gap-2 rounded-xl border-border/50 hover:bg-secondary/40 text-foreground hover:text-foreground"
          data-testid={`btn-suggest-${suggestion.label.toLowerCase()}`}
        >
          {suggestion.icon}
          <span className="text-sm">{suggestion.label}</span>
        </Button>
      ))}
    </div>
  );
}
