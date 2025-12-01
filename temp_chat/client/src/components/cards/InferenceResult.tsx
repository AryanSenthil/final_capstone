import { InferenceResult } from '@/lib/mockData';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle, RotateCcw } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

interface InferenceResultProps {
  result: InferenceResult;
  onRunAgain?: () => void;
}

export function InferenceResultCard({ result, onRunAgain }: InferenceResultProps) {
  const isCritical = result.prediction.includes('DISBOND') || result.prediction.includes('CRITICAL');

  return (
    <Card className="w-full bg-card border-border shadow-md animate-in fade-in duration-500">
      <CardHeader className={`pb-4 border-b ${isCritical ? 'border-destructive/30 bg-destructive/5' : 'border-primary/30 bg-primary/5'}`}>
        <div className="flex justify-between items-center">
          <CardTitle className="text-sm font-medium font-display text-muted-foreground uppercase tracking-wider">Inference Result</CardTitle>
          <Badge variant={isCritical ? "destructive" : "default"} className="font-mono">
            {isCritical ? <AlertTriangle className="w-3 h-3 mr-1" /> : <CheckCircle className="w-3 h-3 mr-1" />}
            {(result.confidence * 100).toFixed(1)}% Confidence
          </Badge>
        </div>
        <div className={`text-3xl font-bold font-display mt-2 ${isCritical ? 'text-destructive' : 'text-primary'}`}>
          {result.prediction}
        </div>
      </CardHeader>
      
      <CardContent className="p-0">
        <div className="p-3 bg-secondary/20 text-xs font-semibold text-muted-foreground border-b border-border/50 grid grid-cols-4 gap-4 px-6">
            <div className="col-span-1">ID</div>
            <div className="col-span-1">Time</div>
            <div className="col-span-1">Prediction</div>
            <div className="col-span-1 text-right">Conf</div>
        </div>
        <ScrollArea className="h-[200px]">
          <div className="p-2">
            {result.chunks.map((chunk, i) => (
              <div 
                key={chunk.id} 
                className={`grid grid-cols-4 gap-4 px-4 py-2 text-sm border-b border-border/30 last:border-0 items-center hover:bg-accent/5 rounded transition-colors font-mono ${
                  chunk.prediction === 'DISBOND' ? 'text-destructive' : 'text-foreground'
                }`}
              >
                <div className="col-span-1 text-muted-foreground opacity-70">{chunk.id}</div>
                <div className="col-span-1">{chunk.timestamp}</div>
                <div className="col-span-1 font-bold">{chunk.prediction}</div>
                <div className="col-span-1 text-right opacity-80">{(chunk.confidence * 100).toFixed(0)}%</div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
      <CardFooter className="p-3 border-t border-border/50 bg-secondary/5 justify-center">
        <Button variant="ghost" size="sm" onClick={onRunAgain} className="text-muted-foreground hover:text-primary">
          <RotateCcw className="w-4 h-4 mr-2" /> Run Another Test
        </Button>
      </CardFooter>
    </Card>
  );
}
