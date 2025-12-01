import { useQuery } from "@tanstack/react-query";
import { GraphCarousel } from "@/components/training/GraphCarousel";
import { InteractiveCharts } from "@/components/training/InteractiveCharts";
import { ReportModal } from "@/components/training/ReportModal";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ArrowLeft, Download, FileText, Calendar, Clock, Layers, Activity, Loader2, BarChart3, ImageIcon } from "lucide-react";
import { useState } from "react";
import { Link, useRoute } from "wouter";

interface Model {
  id: string;
  name: string;
  accuracy: string;
  loss: string;
  date: string;
  architecture: string;
  status: string;
  path: string;
  test_accuracy?: string;
  training_time?: number;  // Training duration in seconds
  report_path: string | null;
}

function formatTrainingTime(seconds: number | undefined): string {
  if (!seconds) return "N/A";

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
}

interface ModelGraphs {
  accuracy?: string;
  loss?: string;
  confusion_matrix?: string;
}

export default function ModelDetailPage() {
  const [showReport, setShowReport] = useState(false);
  const [, params] = useRoute("/models/:id");
  const modelId = params?.id;

  const { data: model, isLoading, error } = useQuery<Model>({
    queryKey: [`/api/models/${modelId}`],
    enabled: !!modelId,
  });

  // Fetch model graphs
  const { data: graphs } = useQuery<ModelGraphs>({
    queryKey: [`/api/models/${modelId}/graphs`],
    enabled: !!modelId,
  });

  // Fetch training history for interactive charts
  const { data: historyData } = useQuery<{ history: any }>({
    queryKey: [`/api/models/${modelId}/history`],
    enabled: !!modelId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !model) {
    return (
      <div className="text-center py-16">
        <h2 className="text-xl font-semibold text-destructive">Model not found</h2>
        <Link href="/models">
          <Button className="mt-4 hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200">Back to Models</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full -m-4 sm:-m-6 overflow-hidden">
      {/* Header */}
      <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-6 py-4 shrink-0">
        <div className="flex items-center justify-between max-w-7xl mx-auto w-full">
          <div className="flex items-center gap-4">
            <Link href="/models">
              <Button variant="ghost" size="icon" className="rounded-full hover:scale-110 hover:shadow-md active:scale-95 transition-all duration-200">
                <ArrowLeft size={20} />
              </Button>
            </Link>
            <div>
              <h1 className="text-xl font-bold tracking-tight text-primary">{model.name}</h1>
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5"><Calendar size={14} /> {model.date}</span>
                <span className="flex items-center gap-1.5"><Layers size={14} /> {model.architecture}</span>
                {model.training_time !== undefined && (
                  <span className="flex items-center gap-1.5"><Clock size={14} /> {formatTrainingTime(model.training_time)}</span>
                )}
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            {model.report_path && (
              <Button variant="outline" size="sm" onClick={() => setShowReport(true)} className="hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200">
                <FileText size={16} className="mr-2 text-blue-600" />
                View Report
              </Button>
            )}
            <Button variant="outline" size="sm" className="hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200">
              <Download size={16} className="mr-2" />
              Weights
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 bg-secondary/10 p-4 overflow-hidden">
         <div className="max-w-7xl mx-auto w-full h-full grid grid-cols-1 lg:grid-cols-4 gap-4">
            {/* Key Metrics - Compact sidebar */}
            <div className="lg:col-span-1 flex flex-col gap-4 h-full overflow-hidden">
               {/* Metrics row */}
               <div className="grid grid-cols-2 gap-3 shrink-0">
                  <div className="bg-card p-4 rounded-xl border shadow-sm">
                     <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1.5">
                       <Activity size={12} /> Accuracy
                     </div>
                     <div className="text-2xl font-bold text-primary">{model.accuracy}</div>
                  </div>
                  <div className="bg-card p-4 rounded-xl border shadow-sm">
                     <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1.5">
                       <Activity size={12} /> Loss
                     </div>
                     <div className="text-2xl font-bold">{model.loss}</div>
                  </div>
               </div>

               {/* Model Info - fills remaining space */}
               <div className="bg-card p-4 rounded-xl border shadow-sm flex-1 overflow-auto">
                  <h3 className="font-semibold text-sm mb-3">Model Information</h3>
                  <div className="space-y-2 text-sm">
                     <div className="flex justify-between border-b border-border/50 pb-2">
                        <span className="text-muted-foreground">Architecture</span>
                        <span className="font-medium">{model.architecture}</span>
                     </div>
                     <div className="flex justify-between border-b border-border/50 pb-2">
                        <span className="text-muted-foreground">Created</span>
                        <span className="font-medium">{model.date}</span>
                     </div>
                     <div className="flex justify-between border-b border-border/50 pb-2">
                        <span className="text-muted-foreground">Test Accuracy</span>
                        <span className="font-medium text-primary">{model.test_accuracy || model.accuracy}</span>
                     </div>
                     {model.training_time !== undefined && (
                       <div className="flex justify-between pt-1">
                          <span className="text-muted-foreground">Training Time</span>
                          <span className="font-medium">{formatTrainingTime(model.training_time)}</span>
                       </div>
                     )}
                  </div>
               </div>
            </div>

            {/* Visualizations - takes more space */}
            <div className="lg:col-span-3 bg-card rounded-xl border shadow-sm p-4 h-full overflow-hidden flex flex-col">
               <Tabs defaultValue="interactive" className="w-full h-full flex flex-col">
                 <TabsList className="grid w-full grid-cols-2 mb-4 shrink-0">
                   <TabsTrigger value="interactive" className="gap-2">
                     <BarChart3 size={16} />
                     Interactive Charts
                   </TabsTrigger>
                   <TabsTrigger value="graphs" className="gap-2">
                     <ImageIcon size={16} />
                     Graph Images
                   </TabsTrigger>
                 </TabsList>
                 <TabsContent value="interactive" className="mt-0 flex-1 overflow-hidden">
                   <InteractiveCharts history={historyData?.history} />
                 </TabsContent>
                 <TabsContent value="graphs" className="mt-0 flex-1 overflow-hidden">
                   <GraphCarousel hasData={true} graphs={graphs} />
                 </TabsContent>
               </Tabs>
            </div>
         </div>
      </div>

      {model.report_path && (
        <ReportModal
          open={showReport}
          onOpenChange={setShowReport}
          modelName={model.name}
          reportPath={model.report_path}
        />
      )}
    </div>
  );
}
