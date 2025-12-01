import { TrainingJob } from '@/lib/mockData';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { Loader2, XCircle } from 'lucide-react';

interface TrainingProgressProps {
  job: TrainingJob;
  onCancel?: () => void;
}

export function TrainingProgress({ job, onCancel }: TrainingProgressProps) {
  const progress = (job.currentEpoch / job.totalEpochs) * 100;

  return (
    <Card className="w-full bg-card border-border shadow-md overflow-hidden animate-in fade-in zoom-in-95 duration-300">
      <CardHeader className="pb-2 border-b border-border/50 bg-secondary/10">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-primary" />
            <CardTitle className="text-base font-medium font-display">Training Model...</CardTitle>
          </div>
          <Button variant="ghost" size="sm" className="h-8 text-muted-foreground hover:text-destructive" onClick={onCancel}>
            <XCircle className="w-4 h-4 mr-1" /> Cancel
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="space-y-4">
          {/* Status Text */}
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">{job.progressMessage}</span>
            <span className="font-mono text-primary">{job.currentEpoch} / {job.totalEpochs} Epochs</span>
          </div>

          {/* Progress Bar */}
          <Progress value={progress} className="h-2" />

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-4 mt-2">
            <div className="bg-background/50 p-3 rounded border border-border/50">
              <span className="text-xs text-muted-foreground uppercase tracking-wider block mb-1">Current Accuracy</span>
              <span className="text-2xl font-mono font-bold text-primary">
                {(job.accuracy * 100).toFixed(1)}%
              </span>
            </div>
            <div className="bg-background/50 p-3 rounded border border-border/50">
              <span className="text-xs text-muted-foreground uppercase tracking-wider block mb-1">Current Loss</span>
              <span className="text-2xl font-mono font-bold text-accent">
                {job.loss.toFixed(4)}
              </span>
            </div>
          </div>

          {/* Live Graph */}
          <div className="h-40 w-full mt-4 bg-background/30 rounded border border-border/50 p-2">
             <ResponsiveContainer width="100%" height="100%">
              <LineChart data={job.history}>
                <XAxis dataKey="epoch" hide />
                <YAxis domain={[0, 1]} hide />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'hsl(var(--popover))', borderColor: 'hsl(var(--border))', color: 'hsl(var(--foreground))' }}
                  itemStyle={{ color: 'hsl(var(--primary))' }}
                  labelStyle={{ display: 'none' }}
                />
                <Line type="monotone" dataKey="accuracy" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="loss" stroke="hsl(var(--accent))" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
