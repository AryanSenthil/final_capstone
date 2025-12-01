import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Calendar, Download, ArrowRight, Box, Layers, Activity, Trash2, Loader2, Clock } from "lucide-react";
import { Link } from "wouter";
import { cn } from "@/lib/utils";
import { toast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useState } from "react";

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

export default function ModelsPage() {
  const queryClient = useQueryClient();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [modelToDelete, setModelToDelete] = useState<Model | null>(null);

  const { data: models = [], isLoading } = useQuery<Model[]>({
    queryKey: ["/api/models"],
  });

  const deleteMutation = useMutation({
    mutationFn: async (modelId: string) => {
      const response = await apiRequest("DELETE", `/api/models/${modelId}`);
      return response.json();
    },
    onSuccess: (_, modelId) => {
      queryClient.invalidateQueries({ queryKey: ["/api/models"] });
      const model = models.find(m => m.id === modelId);
      toast({
        title: "Model Deleted",
        description: `${model?.name || modelId} has been removed from registry.`,
        variant: "destructive"
      });
      setDeleteDialogOpen(false);
      setModelToDelete(null);
    },
    onError: (error: Error) => {
      toast({
        title: "Delete Failed",
        description: error.message,
        variant: "destructive"
      });
    },
  });

  const handleDeleteClick = (model: Model, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setModelToDelete(model);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (modelToDelete) {
      deleteMutation.mutate(modelToDelete.id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-border pb-4">
        <div className="space-y-1">
          <h2 className="text-2xl font-bold tracking-tight text-primary">Model Registry</h2>
          <p className="text-muted-foreground text-base">Manage, version, and deploy trained neural networks.</p>
        </div>
        <div className="flex gap-3">
           <Button className="rounded-xl shadow-lg shadow-primary/20 hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200">Downloads</Button>
        </div>
      </div>

      {models.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <Layers className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-semibold mb-2">No Models Yet</h3>
            <p className="text-sm">Train your first model to see it here.</p>
            <Link href="/training">
              <Button className="mt-4 hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200">Go to Training</Button>
            </Link>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto pb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {models.map((model) => (
            <Link key={model.id} href={`/models/${model.id}`}>
              <a className="block h-full group outline-none">
                <Card className={cn(
                  "h-full transition-all duration-300 border-border/60 bg-card/50 backdrop-blur-sm overflow-hidden relative",
                  "hover:shadow-2xl hover:shadow-primary/5 hover:border-primary/20 hover:-translate-y-1",
                  "group-focus:ring-2 group-focus:ring-primary group-focus:ring-offset-2"
                )}>
                  {/* Top Decoration Line */}
                  <div className="absolute top-0 left-0 right-0 h-1 bg-border group-hover:bg-primary transition-all duration-500" />

                  <CardHeader className="pb-4 pt-6">
                    <div className="flex justify-between items-start mb-2">
                      <div className="p-2.5 rounded-xl bg-background shadow-sm border border-border/50 group-hover:scale-110 transition-transform duration-300">
                         {model.architecture === "ResNet" ? <Box size={20} className="text-primary" /> : <Layers size={20} className="text-blue-400" />}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10 hover:scale-110 hover:shadow-md active:scale-95 transition-all duration-200"
                        onClick={(e) => handleDeleteClick(model, e)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 size={16} />
                      </Button>
                    </div>
                    <CardTitle className="text-xl font-bold font-mono tracking-tight group-hover:text-primary transition-colors">
                      {model.name}
                    </CardTitle>
                    <div className="flex items-center gap-3 text-xs text-muted-foreground font-medium pt-1">
                       <span className="flex items-center gap-1">
                         <Calendar size={12} />
                         {model.date}
                       </span>
                       {model.training_time !== undefined && (
                         <span className="flex items-center gap-1">
                           <Clock size={12} />
                           {formatTrainingTime(model.training_time)}
                         </span>
                       )}
                    </div>
                  </CardHeader>

                  <CardContent className="pb-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-background/50 p-3 rounded-xl border border-border/50 group-hover:border-primary/10 transition-colors">
                        <span className="flex items-center gap-1.5 text-xs text-muted-foreground uppercase tracking-wider font-semibold mb-1">
                          <Activity size={12} /> Accuracy
                        </span>
                        <span className="text-2xl font-bold tracking-tight">{model.accuracy}</span>
                      </div>
                      <div className="bg-background/50 p-3 rounded-xl border border-border/50 group-hover:border-primary/10 transition-colors">
                         <span className="flex items-center gap-1.5 text-xs text-muted-foreground uppercase tracking-wider font-semibold mb-1">
                          <Layers size={12} /> Arch
                        </span>
                        <span className="text-lg font-medium">{model.architecture}</span>
                      </div>
                    </div>
                  </CardContent>

                  <CardFooter className="pt-4 border-t border-border/40 flex justify-between bg-muted/5">
                    <Button variant="ghost" size="sm" className="gap-2 text-muted-foreground hover:text-foreground hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200 -ml-2" onClick={(e) => e.stopPropagation()}>
                      <Download size={14} /> <span className="text-xs">Weights</span>
                    </Button>
                    <div className="flex items-center gap-1 text-sm font-semibold text-primary opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">
                      View Analytics <ArrowRight size={14} />
                    </div>
                  </CardFooter>
                </Card>
              </a>
            </Link>
          ))}
          </div>
        </div>
      )}

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Model</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <span className="font-semibold text-foreground">{modelToDelete?.name}</span>?
              This action cannot be undone. The model weights, graphs, and all associated data will be permanently removed.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
