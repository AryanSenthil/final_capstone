import { useQuery } from "@tanstack/react-query";
import { GraphCarousel } from "@/components/training/GraphCarousel";
import { ReportModal } from "@/components/training/ReportModal";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Download, FileText, Calendar, Clock, Layers, Activity, Loader2 } from "lucide-react";
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
  report_path: string | null;
}

export default function ModelDetailPage() {
  const [showReport, setShowReport] = useState(false);
  const [, params] = useRoute("/models/:id");
  const modelId = params?.id;

  const { data: model, isLoading, error } = useQuery<Model>({
    queryKey: ["/api/models", modelId],
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
          <Button className="mt-4">Back to Models</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] -m-4 sm:-m-6">
      {/* Header */}
      <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 p-6">
        <div className="flex items-center justify-between max-w-7xl mx-auto w-full">
          <div className="flex items-center gap-4">
            <Link href="/models">
              <Button variant="ghost" size="icon" className="rounded-full">
                <ArrowLeft size={20} />
              </Button>
            </Link>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold tracking-tight">{model.name}</h1>
                <Badge variant="default" className="bg-emerald-500 hover:bg-emerald-600">
                  {model.status}
                </Badge>
              </div>
              <div className="flex items-center gap-4 text-sm text-muted-foreground">
                <span className="flex items-center gap-1.5"><Calendar size={14} /> {model.date}</span>
                <span className="flex items-center gap-1.5"><Layers size={14} /> {model.architecture}</span>
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            {model.report_path && (
              <Button variant="outline" onClick={() => setShowReport(true)}>
                <FileText size={16} className="mr-2 text-blue-600" />
                View Report
              </Button>
            )}
            <Button variant="outline">
              <Download size={16} className="mr-2" />
              Weights
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto bg-secondary/10 p-6">
         <div className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Key Metrics */}
            <div className="lg:col-span-1 space-y-6">
               <div className="grid grid-cols-2 gap-4">
                  <div className="bg-card p-5 rounded-xl border shadow-sm">
                     <div className="text-sm text-muted-foreground mb-1 flex items-center gap-2">
                       <Activity size={14} /> Accuracy
                     </div>
                     <div className="text-3xl font-bold text-primary">{model.accuracy}</div>
                  </div>
                  <div className="bg-card p-5 rounded-xl border shadow-sm">
                     <div className="text-sm text-muted-foreground mb-1 flex items-center gap-2">
                       <Activity size={14} /> Loss
                     </div>
                     <div className="text-3xl font-bold">{model.loss}</div>
                  </div>
               </div>

               <div className="bg-card p-6 rounded-xl border shadow-sm space-y-4">
                  <h3 className="font-semibold">Model Information</h3>
                  <div className="space-y-3">
                     <div className="flex justify-between text-sm border-b border-border/50 pb-2">
                        <span className="text-muted-foreground">Architecture</span>
                        <span className="font-medium">{model.architecture}</span>
                     </div>
                     <div className="flex justify-between text-sm border-b border-border/50 pb-2">
                        <span className="text-muted-foreground">Created</span>
                        <span className="font-medium">{model.date}</span>
                     </div>
                     <div className="flex justify-between text-sm border-b border-border/50 pb-2">
                        <span className="text-muted-foreground">Status</span>
                        <span className="font-medium">{model.status}</span>
                     </div>
                     <div className="flex justify-between text-sm pb-1">
                        <span className="text-muted-foreground">Path</span>
                        <span className="font-medium font-mono text-xs truncate max-w-[150px]" title={model.path}>
                          {model.path.split('/').pop()}
                        </span>
                     </div>
                  </div>
               </div>
            </div>

            {/* Visualizations */}
            <div className="lg:col-span-2 bg-card rounded-xl border shadow-sm p-6 min-h-[500px]">
               <GraphCarousel hasData={true} />
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
