import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { Database, Clock, ArrowRight, HardDrive, Trash2, Loader2 } from "lucide-react";
import { Link } from "wouter";
import { Dataset } from "@/lib/mockData";
import { apiRequest } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";

interface ClassificationCardProps {
  dataset: Dataset;
}

export function ClassificationCard({ dataset }: ClassificationCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("DELETE", `/api/labels/${dataset.id}`);
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["/api/labels"] });
      queryClient.invalidateQueries({ queryKey: ["/api/raw-database"] });
      toast({
        title: "Dataset Deleted",
        description: data.message || `Dataset "${dataset.label}" has been deleted.`,
        duration: 4000,
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Delete Failed",
        description: error.message || "Failed to delete dataset.",
        variant: "destructive",
        duration: 5000,
      });
    },
  });

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowDeleteDialog(true);
  };

  const confirmDelete = () => {
    deleteMutation.mutate();
    setShowDeleteDialog(false);
  };

  return (
    <>
      <Link href={`/database/${dataset.id}`}>
        <div className="group relative cursor-pointer h-full">
          <Card className="h-full border-border hover:border-primary/50 transition-all duration-200 hover:shadow-lg hover:scale-[1.02] bg-card">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <div className="p-2 bg-primary/10 rounded-md flex-shrink-0">
                    <Database className="h-4 w-4 text-primary" />
                  </div>
                  <CardTitle className="text-base font-bold font-sans break-all text-primary">
                    {dataset.label}
                  </CardTitle>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive hover:bg-destructive/10 flex-shrink-0"
                  onClick={handleDelete}
                  disabled={deleteMutation.isPending}
                >
                  {deleteMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Trash2 className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </CardHeader>
          <CardContent className="pb-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground font-medium">{dataset.chunks} files</span>
                <Badge className="bg-primary text-primary-foreground hover:bg-primary/90 font-medium text-xs px-2 py-0.5 h-auto rounded-md">
                  {dataset.measurement} ({dataset.unit})
                </Badge>
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Clock className="h-3 w-3" />
                  <span>{dataset.durationPerChunk}</span>
                </div>
                <div className="flex items-center gap-2">
                  <HardDrive className="h-3 w-3" />
                  <span>{dataset.folderSize}</span>
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter className="pt-0 pb-4 text-xs text-muted-foreground flex justify-between items-center border-t border-border/50 mt-auto pt-4">
            <span className="truncate mr-2" title={dataset.lastUpdated}>Updated: {dataset.lastUpdated}</span>
            <span className="text-primary font-medium opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 shrink-0">
              Details <ArrowRight className="h-3 w-3" />
            </span>
          </CardFooter>
        </Card>
      </div>
    </Link>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Dataset</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <span className="font-semibold text-foreground">{dataset.label}</span>?
              This will permanently remove {dataset.chunks} files and the associated raw data.
              This action cannot be undone.
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
    </>
  );
}
