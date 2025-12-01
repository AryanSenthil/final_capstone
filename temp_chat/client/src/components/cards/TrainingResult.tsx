import { TrainingJob } from '@/lib/mockData';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, Download, Play } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis } from 'recharts';

interface TrainingResultProps {
  job: TrainingJob;
}

export function TrainingResult({ job }: TrainingResultProps) {
  return (
    <Card className="w-full bg-card border-primary/20 shadow-lg shadow-primary/5 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <CardHeader className="pb-2 border-b border-border/50 bg-primary/5">
        <div className="flex items-center gap-2 text-primary">
          <CheckCircle2 className="w-5 h-5" />
          <CardTitle className="text-lg font-medium font-display">Training Complete</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
           <div className="md:col-span-1 space-y-4">
              <div className="p-4 bg-background rounded-lg border border-border">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">Final Accuracy</span>
                <div className="text-3xl font-mono font-bold text-primary mt-1">94.2%</div>
              </div>
              <div className="p-4 bg-background rounded-lg border border-border">
                <span className="text-xs text-muted-foreground uppercase tracking-wider">Final Loss</span>
                <div className="text-3xl font-mono font-bold text-accent mt-1">0.042</div>
              </div>
           </div>
           
           <div className="md:col-span-2 bg-background rounded-lg border border-border p-4 flex flex-col">
              <span className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Training Convergence</span>
              <div className="flex-1 min-h-[120px]">
                 <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={job.history}>
                    <Line type="monotone" dataKey="accuracy" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="loss" stroke="hsl(var(--accent))" strokeWidth={2} dot={false} />
                    <XAxis dataKey="epoch" hide />
                    <YAxis hide />
                  </LineChart>
                </ResponsiveContainer>
              </div>
           </div>
        </div>
        
        <div className="grid grid-cols-3 gap-2">
          {/* Placeholder for Confusion Matrix Image */}
          <div className="aspect-square bg-background rounded border border-border flex items-center justify-center">
             <div className="text-[10px] text-muted-foreground text-center">
               Confusion<br/>Matrix
             </div>
          </div>
           {/* Placeholder for Precision Recall Image */}
          <div className="aspect-square bg-background rounded border border-border flex items-center justify-center">
             <div className="text-[10px] text-muted-foreground text-center">
               Precision<br/>Recall
             </div>
          </div>
           {/* Placeholder for ROC Curve Image */}
          <div className="aspect-square bg-background rounded border border-border flex items-center justify-center">
             <div className="text-[10px] text-muted-foreground text-center">
               ROC<br/>Curve
             </div>
          </div>
        </div>

      </CardContent>
      <CardFooter className="bg-secondary/10 border-t border-border/50 gap-2 justify-end p-3">
        <Button variant="outline" size="sm" className="gap-2">
          <Download className="w-4 h-4" /> Report
        </Button>
        <Button size="sm" className="gap-2">
          <Play className="w-4 h-4" /> Test Model
        </Button>
      </CardFooter>
    </Card>
  );
}
