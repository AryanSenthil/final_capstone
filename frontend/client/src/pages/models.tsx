import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Calendar, Download, ArrowRight, Box, Layers, Activity, Trash2, Loader2, Clock, Search, ArrowUpDown } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useState, useMemo } from "react";

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
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("date-desc");
  const [downloadingModel, setDownloadingModel] = useState<string | null>(null);

  const { data: models = [], isLoading } = useQuery<Model[]>({
    queryKey: ["/api/models"],
  });

  // Filter and sort models
  const filteredModels = useMemo(() => {
    let result = [...models];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(model =>
        model.name.toLowerCase().includes(query) ||
        model.architecture.toLowerCase().includes(query)
      );
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case "date-asc":
          return new Date(a.date).getTime() - new Date(b.date).getTime();
        case "name-asc":
          return a.name.localeCompare(b.name);
        case "name-desc":
          return b.name.localeCompare(a.name);
        case "accuracy-desc":
          return parseFloat(b.accuracy) - parseFloat(a.accuracy);
        case "accuracy-asc":
          return parseFloat(a.accuracy) - parseFloat(b.accuracy);
        case "date-desc":
        default:
          return new Date(b.date).getTime() - new Date(a.date).getTime();
      }
    });

    return result;
  }, [models, searchQuery, sortBy]);

  const handleDownloadWeights = async (model: Model, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDownloadingModel(model.id);

    try {
      const link = document.createElement('a');
      link.href = `/api/models/${model.id}/weights`;
      link.download = `${model.name}.keras`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast({
        title: "Download Started",
        description: `Downloading ${model.name}.keras weights file`,
      });
    } catch (error) {
      toast({
        title: "Download Failed",
        description: "Failed to download model weights",
        variant: "destructive",
      });
    } finally {
      setTimeout(() => setDownloadingModel(null), 1500);
    }
  };

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
      </div>

      {/* Search and Filter Bar */}
      {models.length > 0 && (
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search models..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-10"
            />
          </div>
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-[180px] h-10">
              <ArrowUpDown className="h-4 w-4 mr-2 text-muted-foreground" />
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date-desc">Newest First</SelectItem>
              <SelectItem value="date-asc">Oldest First</SelectItem>
              <SelectItem value="name-asc">Name A-Z</SelectItem>
              <SelectItem value="name-desc">Name Z-A</SelectItem>
              <SelectItem value="accuracy-desc">Highest Accuracy</SelectItem>
              <SelectItem value="accuracy-asc">Lowest Accuracy</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

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
      ) : filteredModels.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-semibold mb-2">No Results Found</h3>
            <p className="text-sm">Try adjusting your search terms.</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto pb-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredModels.map((model) => (
            <Link key={model.id} href={`/models/${model.id}`}>
              <a className="block h-full group outline-none">
                <Card className={cn(
                  "h-full transition-all duration-300 border-border/60 bg-card/50 backdrop-blur-sm overflow-hidden relative",
                  "hover:shadow-xl hover:shadow-primary/5 hover:border-primary/20 hover:-translate-y-0.5",
                  "group-focus:ring-2 group-focus:ring-primary group-focus:ring-offset-2"
                )}>
                  {/* Top Decoration Line */}
                  <div className="absolute top-0 left-0 right-0 h-0.5 bg-border group-hover:bg-primary transition-all duration-500" />

                  <CardHeader className="pb-2 pt-4 px-4">
                    <div className="flex justify-between items-start mb-1">
                      <div className="p-2 rounded-lg bg-background shadow-sm border border-border/50 group-hover:scale-110 transition-transform duration-300">
                         {model.architecture === "ResNet" ? <Box size={16} className="text-primary" /> : <Layers size={16} className="text-blue-400" />}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10 hover:scale-110 hover:shadow-md active:scale-95 transition-all duration-200"
                        onClick={(e) => handleDeleteClick(model, e)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 size={14} />
                      </Button>
                    </div>
                    <CardTitle className="text-base font-bold font-mono tracking-tight group-hover:text-primary transition-colors truncate">
                      {model.name}
                    </CardTitle>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-medium pt-0.5">
                       <span className="flex items-center gap-1">
                         <Calendar size={10} />
                         {model.date}
                       </span>
                       {model.training_time !== undefined && (
                         <span className="flex items-center gap-1">
                           <Clock size={10} />
                           {formatTrainingTime(model.training_time)}
                         </span>
                       )}
                    </div>
                  </CardHeader>

                  <CardContent className="pb-2 px-4">
                    <div className="grid grid-cols-2 gap-2">
                      <div className="bg-background/50 p-2 rounded-lg border border-border/50 group-hover:border-primary/10 transition-colors">
                        <span className="flex items-center gap-1 text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-0.5">
                          <Activity size={10} /> Accuracy
                        </span>
                        <span className="text-lg font-bold tracking-tight">{model.accuracy}</span>
                      </div>
                      <div className="bg-background/50 p-2 rounded-lg border border-border/50 group-hover:border-primary/10 transition-colors">
                         <span className="flex items-center gap-1 text-[10px] text-muted-foreground uppercase tracking-wider font-semibold mb-0.5">
                          <Layers size={10} /> Arch
                        </span>
                        <span className="text-sm font-medium">{model.architecture}</span>
                      </div>
                    </div>
                  </CardContent>

                  <CardFooter className="pt-2 pb-3 px-4 border-t border-border/40 flex justify-between bg-muted/5">
                    <Button
                      variant="ghost"
                      size="sm"
                      className={cn(
                        "gap-1.5 text-muted-foreground hover:text-foreground hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200 -ml-2 h-7 px-2 text-xs",
                        downloadingModel === model.id && "text-primary"
                      )}
                      onClick={(e) => handleDownloadWeights(model, e)}
                      disabled={downloadingModel === model.id}
                    >
                      {downloadingModel === model.id ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <Download size={12} />
                      )}
                      <span>Weights</span>
                    </Button>
                    <div className="flex items-center gap-1 text-xs font-semibold text-primary opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300">
                      View <ArrowRight size={12} />
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
