import { Dataset } from '@/lib/mockData';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { Database, Eye, Trash2 } from 'lucide-react';

interface DatasetCardProps {
  dataset: Dataset;
}

export function DatasetCard({ dataset }: DatasetCardProps) {
  return (
    <Card className="w-full bg-card border-border/50 shadow-sm hover:shadow-md transition-all duration-200 group" data-testid={`card-dataset-${dataset.id}`}>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-md bg-primary/10 text-primary">
              <Database className="w-4 h-4" />
            </div>
            <div>
              <CardTitle className="text-base font-medium text-foreground font-display">{dataset.name}</CardTitle>
              <p className="text-xs text-muted-foreground">{dataset.dateAdded}</p>
            </div>
          </div>
          <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button variant="ghost" size="icon" className="h-7 w-7 hover:bg-primary/10 hover:text-primary">
              <Eye className="w-3.5 h-3.5" />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7 hover:bg-destructive/10 hover:text-destructive">
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4 line-clamp-2">
          {dataset.description}
        </p>
        
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <span className="text-muted-foreground block mb-1">Chunks</span>
            <span className="font-mono font-semibold">{dataset.chunkCount.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-muted-foreground block mb-1 flex justify-between">
              Quality
              <span className={dataset.qualityScore > 90 ? "text-green-400" : "text-yellow-400"}>
                {dataset.qualityScore}%
              </span>
            </span>
            <Progress value={dataset.qualityScore} className="h-1.5" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
