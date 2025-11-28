import { useQuery } from "@tanstack/react-query";
import { ClassificationCard } from "@/components/classification-card";
import { AddDataModal } from "@/components/add-data-modal";
import { Loader2 } from "lucide-react";
import type { Dataset } from "@/lib/mockData";

export default function DatabasePage() {
  const { data: datasets, isLoading, error } = useQuery<Dataset[]>({
    queryKey: ["/api/labels"],
  });

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header - Removed Main Title, kept action bar */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-border pb-6">
        <div className="space-y-1">
          <h2 className="text-2xl font-bold tracking-tight text-primary">Processed Database</h2>
          <p className="text-muted-foreground text-base">
            Standardized sensor data files ready for training
          </p>
        </div>
        <AddDataModal />
      </div>

      {/* Grid */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center h-[40vh] gap-3 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm">Loading datasets...</p>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center h-[40vh] gap-3 text-destructive">
          <p className="text-sm">Failed to load datasets. Make sure the API server is running.</p>
        </div>
      ) : datasets && datasets.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {datasets.map((dataset) => (
            <ClassificationCard key={dataset.id} dataset={dataset} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center h-[40vh] gap-3 text-muted-foreground">
          <p className="text-lg font-medium">No datasets found</p>
          <p className="text-sm">Click "Add Data" to import and process sensor data</p>
        </div>
      )}
    </div>
  );
}
