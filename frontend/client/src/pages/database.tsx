import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ClassificationCard } from "@/components/classification-card";
import { AddDataModal } from "@/components/add-data-modal";
import { Input } from "@/components/ui/input";
import { Loader2, Search, ArrowUpDown } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Dataset } from "@/lib/mockData";

export default function DatabasePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("name-asc");

  const { data: datasets, isLoading, error } = useQuery<Dataset[]>({
    queryKey: ["/api/labels"],
    select: (data) => data.map(dataset => ({
      ...dataset,
      name: dataset.label, // Add name alias for backwards compatibility
      fileCount: dataset.chunks // Add fileCount alias for backwards compatibility
    }))
  });

  // Filter and sort datasets
  const filteredDatasets = useMemo(() => {
    if (!datasets) return [];

    let result = [...datasets];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(dataset =>
        dataset.name.toLowerCase().includes(query) ||
        dataset.description?.toLowerCase().includes(query)
      );
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case "name-desc":
          return b.name.localeCompare(a.name);
        case "count-desc":
          return b.fileCount - a.fileCount;
        case "count-asc":
          return a.fileCount - b.fileCount;
        case "newest":
          return new Date(b.lastUpdated).getTime() - new Date(a.lastUpdated).getTime();
        case "oldest":
          return new Date(a.lastUpdated).getTime() - new Date(b.lastUpdated).getTime();
        case "name-asc":
        default:
          return a.name.localeCompare(b.name);
      }
    });

    return result;
  }, [datasets, searchQuery, sortBy]);

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
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

      {/* Search and Filter Bar */}
      {datasets && datasets.length > 0 && (
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search categories..."
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
              <SelectItem value="name-asc">Name A-Z</SelectItem>
              <SelectItem value="name-desc">Name Z-A</SelectItem>
              <SelectItem value="newest">Newest First</SelectItem>
              <SelectItem value="oldest">Oldest First</SelectItem>
              <SelectItem value="count-desc">Most Files</SelectItem>
              <SelectItem value="count-asc">Fewest Files</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

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
        filteredDatasets.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredDatasets.map((dataset) => (
              <ClassificationCard key={dataset.id} dataset={dataset} />
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-[30vh] gap-3 text-muted-foreground">
            <Search className="h-12 w-12 opacity-50" />
            <p className="text-lg font-medium">No results found</p>
            <p className="text-sm">Try adjusting your search terms</p>
          </div>
        )
      ) : (
        <div className="flex flex-col items-center justify-center h-[40vh] gap-3 text-muted-foreground">
          <p className="text-lg font-medium">No datasets found</p>
          <p className="text-sm">Click "Add Data" to import and process sensor data</p>
        </div>
      )}
    </div>
  );
}
