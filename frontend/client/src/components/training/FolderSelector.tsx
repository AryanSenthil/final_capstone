import { useState, useEffect } from "react";
import { Folder, X, UploadCloud, Loader2, Database, Clock, FileText, Activity, Sparkles, Info, Timer } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { apiRequest } from "@/lib/queryClient";

// Full dataset metadata from the backend
interface DatasetMetadata {
  id: string;
  label: string;
  chunks: number;
  measurement: string;
  unit: string;
  durationPerChunk: string;
  lastUpdated: string;
  samplesPerChunk: number;
  totalDuration: string;
  timeInterval: string;
  folderSize: string;
  sourceFile: string;
  interpolationInterval: string;
  stats: {
    min: number;
    max: number;
    rate: string;
  };
  // AI-generated fields (optional)
  description?: string;
  category?: string;
  qualityScore?: number;
  suggestedArchitecture?: string;
}

export interface FolderSelection {
  path: string;
  name: string;
  fileCount: number;
  selected: boolean;
  metadata?: DatasetMetadata;
}

interface FolderSelectorProps {
  selectedFolders: FolderSelection[];
  onSelectionChange: (folders: FolderSelection[]) => void;
}

export function FolderSelector({ selectedFolders, onSelectionChange }: FolderSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [tempSelection, setTempSelection] = useState<FolderSelection[]>([]);
  const [expandedFolder, setExpandedFolder] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const [isCompact] = useState(true); // Compact mode for narrower panels

  // Fetch available labels/folders from the API with full metadata
  const { data: labels, isLoading } = useQuery<DatasetMetadata[]>({
    queryKey: ["/api/labels"],
  });

  // Mutation to generate AI metadata for a folder
  const generateMetadataMutation = useMutation({
    mutationFn: async (labelId: string) => {
      const response = await apiRequest("POST", `/api/labels/${labelId}/generate-metadata`);
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/labels"] });
    },
  });

  // Mutation to generate AI metadata for ALL folders
  const generateAllMetadataMutation = useMutation({
    mutationFn: async () => {
      const response = await apiRequest("POST", "/api/labels/generate-all-metadata");
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["/api/labels"] });
      // Update temp selection with new metadata
      if (labels) {
        const currentPaths = new Set(selectedFolders.map(f => f.path));
        setTempSelection(labels.map(label => ({
          path: label.label,
          name: label.label,
          fileCount: label.chunks,
          selected: currentPaths.has(label.label),
          metadata: label
        })));
      }
    },
  });

  // Check if any labels are missing AI metadata
  const labelsWithoutMetadata = tempSelection.filter(f => !f.metadata?.description).length;

  // Auto-generate metadata when dialog opens if there are labels without metadata
  useEffect(() => {
    if (isOpen && labelsWithoutMetadata > 0 && !generateAllMetadataMutation.isPending) {
      // Auto-trigger batch metadata generation
      generateAllMetadataMutation.mutate();
    }
  }, [isOpen, labelsWithoutMetadata]);

  const handleOpenChange = (open: boolean) => {
    if (open && labels) {
      const currentPaths = new Set(selectedFolders.map(f => f.path));
      setTempSelection(labels.map(label => ({
        path: label.label,
        name: label.label,
        fileCount: label.chunks,
        selected: currentPaths.has(label.label),
        metadata: label
      })));
    }
    setIsOpen(open);
  };

  const toggleFolder = (path: string) => {
    setTempSelection(prev => prev.map(f =>
      f.path === path ? { ...f, selected: !f.selected } : f
    ));
  };

  const confirmSelection = () => {
    const confirmed = tempSelection.filter(f => f.selected);
    onSelectionChange(confirmed);
    setIsOpen(false);
  };

  const removeFolder = (path: string) => {
    onSelectionChange(selectedFolders.filter(f => f.path !== path));
  };

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1">
          <Folder size={10} /> Training Data
        </h3>
        {selectedFolders.length > 0 && (
          <span className="text-[10px] text-muted-foreground">{selectedFolders.length} selected</span>
        )}
      </div>

      <div className="rounded-lg border border-border bg-card p-2.5 shadow-sm transition-all hover:border-primary/20">
        <div className="flex flex-col gap-2">
          {/* Selected datasets - compact badges */}
          {selectedFolders.length > 0 && (
            <div className="flex flex-wrap gap-1.5 bg-muted/30 p-1.5 rounded border border-border/50 min-h-[32px]">
              {selectedFolders.map((folder) => (
                <TooltipProvider key={folder.path}>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Badge
                        variant="secondary"
                        className="pl-2 pr-1 py-0.5 h-6 text-[11px] flex items-center gap-1 group bg-background border shadow-sm cursor-default text-foreground"
                      >
                        <span className="truncate max-w-[80px] font-medium text-foreground">{folder.name}</span>
                        <span className="text-muted-foreground text-[9px]">({folder.fileCount})</span>
                        <button
                          onClick={(e) => { e.stopPropagation(); removeFolder(folder.path); }}
                          className="ml-0.5 rounded-full hover:bg-destructive/20 hover:text-destructive p-0.5 transition-colors"
                        >
                          <X size={10} />
                        </button>
                      </Badge>
                    </TooltipTrigger>
                    <TooltipContent side="top" className="text-xs">
                      {folder.metadata?.measurement} ({folder.metadata?.unit}) - {folder.metadata?.folderSize}
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              ))}
            </div>
          )}

          {/* Button to open selection dialog */}
          <Dialog open={isOpen} onOpenChange={handleOpenChange}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className={cn(
                "w-full h-8 text-xs border-dashed hover:text-primary hover:border-primary/30 transition-all",
                selectedFolders.length === 0 ? "text-muted-foreground" : "text-foreground"
              )}>
                <UploadCloud className="mr-1.5 h-3 w-3" />
                {selectedFolders.length > 0 ? "Modify Selection" : "Choose Training Data..."}
              </Button>
            </DialogTrigger>
              <DialogContent className="sm:max-w-4xl">
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <Database size={18} />
                    Select Training Datasets
                  </DialogTitle>
                  <p className="text-sm text-muted-foreground">
                    Choose classification labels from your processed data
                  </p>
                </DialogHeader>
                {isLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : (
                  <ScrollArea className="h-[500px] pr-4">
                    <div className="space-y-3">
                      {tempSelection.length === 0 ? (
                        <div className="text-center py-12 space-y-3">
                          <Database size={40} className="mx-auto text-muted-foreground/40" />
                          <p className="text-sm text-muted-foreground">
                            No datasets available. Import data first.
                          </p>
                        </div>
                      ) : (
                        tempSelection.map((folder) => (
                          <div
                            key={folder.path}
                            className={cn(
                              "rounded-xl border transition-all duration-200 overflow-hidden",
                              folder.selected
                                ? "bg-primary/5 border-primary/40 shadow-sm shadow-primary/10"
                                : "bg-card border-border hover:border-primary/30"
                            )}
                          >
                            {/* Main row - clickable */}
                            <div
                              className="flex items-center justify-between p-4 cursor-pointer"
                              onClick={() => toggleFolder(folder.path)}
                            >
                              <div className="flex items-center gap-3 flex-1 min-w-0">
                                <Checkbox
                                  checked={folder.selected}
                                  onCheckedChange={() => toggleFolder(folder.path)}
                                  id={`folder-${folder.path}`}
                                  className="shrink-0"
                                />
                                <div className="min-w-0 flex-1">
                                  <div className="flex items-center gap-2">
                                    <label className="font-semibold text-sm cursor-pointer truncate">
                                      {folder.name}
                                    </label>
                                    {folder.metadata?.description && (
                                      <TooltipProvider>
                                        <Tooltip>
                                          <TooltipTrigger asChild>
                                            <Sparkles size={12} className="text-amber-500 shrink-0" />
                                          </TooltipTrigger>
                                          <TooltipContent side="top" className="max-w-xs">
                                            <p className="text-xs">{folder.metadata.description}</p>
                                          </TooltipContent>
                                        </Tooltip>
                                      </TooltipProvider>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                                    <span className="flex items-center gap-1">
                                      <FileText size={10} />
                                      {folder.fileCount} chunks
                                    </span>
                                    {folder.metadata && (
                                      <>
                                        <span className="flex items-center gap-1">
                                          <Clock size={10} />
                                          {folder.metadata.durationPerChunk}
                                        </span>
                                        <span className="flex items-center gap-1">
                                          <Activity size={10} />
                                          {folder.metadata.measurement} ({folder.metadata.unit})
                                        </span>
                                      </>
                                    )}
                                  </div>
                                </div>
                              </div>

                              <div className="flex items-center gap-2 shrink-0">
                                {folder.metadata && (
                                  <Badge variant="secondary" className="text-[10px] px-2 py-0.5">
                                    {folder.metadata.folderSize}
                                  </Badge>
                                )}
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-7 w-7 p-0"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setExpandedFolder(expandedFolder === folder.path ? null : folder.path);
                                  }}
                                >
                                  <Info size={14} className={cn(
                                    "transition-transform",
                                    expandedFolder === folder.path && "rotate-180"
                                  )} />
                                </Button>
                              </div>
                            </div>

                            {/* Expanded metadata panel */}
                            {expandedFolder === folder.path && folder.metadata && (
                              <div className="px-4 pb-4 pt-0 border-t border-border/50 bg-muted/30">
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3">
                                  <MetadataCard
                                    label="Samples/Chunk"
                                    value={folder.metadata.samplesPerChunk.toString()}
                                    icon={<Database size={12} />}
                                  />
                                  <MetadataCard
                                    label="Time Interval"
                                    value={folder.metadata.timeInterval}
                                    icon={<Clock size={12} />}
                                  />
                                  <MetadataCard
                                    label="Sample Rate"
                                    value={folder.metadata.stats.rate}
                                    icon={<Activity size={12} />}
                                  />
                                  <MetadataCard
                                    label="Time Period"
                                    value={folder.metadata.durationPerChunk}
                                    icon={<Timer size={12} />}
                                  />
                                </div>

                                <div className="mt-3 pt-3 border-t border-border/50">
                                  <div className="flex items-center justify-between text-xs">
                                    <span className="text-muted-foreground">
                                      Source: <span className="font-mono text-foreground">{folder.metadata.sourceFile}</span>
                                    </span>
                                    <span className="text-muted-foreground">
                                      Updated: {folder.metadata.lastUpdated}
                                    </span>
                                  </div>
                                </div>


                              </div>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </ScrollArea>
                )}
                <DialogFooter className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-2">
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{tempSelection.filter(f => f.selected).length} of {tempSelection.length} selected</span>
                    {generateAllMetadataMutation.isPending && (
                      <span className="text-primary flex items-center gap-1">
                        <Loader2 size={10} className="animate-spin" />
                        Analyzing datasets...
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button onClick={confirmSelection} disabled={tempSelection.filter(f => f.selected).length === 0}>
                      Confirm Selection
                    </Button>
                  </div>
                </DialogFooter>
              </DialogContent>
            </Dialog>
        </div>
      </div>
    </div>
  );
}

// Helper component for metadata display cards
function MetadataCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="bg-background rounded-lg p-2.5 border border-border/50">
      <div className="flex items-center gap-1.5 text-muted-foreground mb-1">
        {icon}
        <span className="text-[10px] uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-xs font-medium truncate">{value}</p>
    </div>
  );
}

// Summary component showing aggregate stats for selected datasets
function DatasetSummary({ folders }: { folders: FolderSelection[] }) {
  if (folders.length === 0) return null;

  // Calculate aggregate statistics
  const totalChunks = folders.reduce((sum, f) => sum + (f.fileCount || 0), 0);
  const uniqueMeasurements = [...new Set(folders.map(f => f.metadata?.measurement).filter(Boolean))];

  // Calculate total size (parse from strings like "1.2 MB", "500 KB")
  const parseSize = (sizeStr: string | undefined): number => {
    if (!sizeStr) return 0;
    const match = sizeStr.match(/^([\d.]+)\s*(B|KB|MB|GB)?$/i);
    if (!match) return 0;
    const value = parseFloat(match[1]);
    const unit = (match[2] || 'B').toUpperCase();
    const multipliers: Record<string, number> = { 'B': 1, 'KB': 1024, 'MB': 1024*1024, 'GB': 1024*1024*1024 };
    return value * (multipliers[unit] || 1);
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const totalBytes = folders.reduce((sum, f) => sum + parseSize(f.metadata?.folderSize), 0);

  // Find value ranges across all datasets
  const allMins = folders.map(f => f.metadata?.stats?.min).filter((v): v is number => v !== undefined);
  const allMaxs = folders.map(f => f.metadata?.stats?.max).filter((v): v is number => v !== undefined);
  const globalMin = allMins.length > 0 ? Math.min(...allMins) : 0;
  const globalMax = allMaxs.length > 0 ? Math.max(...allMaxs) : 0;

  return (
    <div className="bg-gradient-to-br from-primary/5 to-primary/10 rounded-lg p-3 border border-primary/20">
      <div className="flex items-center gap-2 mb-2">
        <Activity size={12} className="text-primary" />
        <span className="text-[10px] font-semibold text-primary uppercase tracking-wider">Selection Summary</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Labels:</span>
          <span className="font-medium">{folders.length}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Total Chunks:</span>
          <span className="font-medium">{totalChunks.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Total Size:</span>
          <span className="font-medium">{formatSize(totalBytes)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">Value Range:</span>
          <span className="font-medium font-mono text-[10px]">
            {globalMin.toFixed(1)} ~ {globalMax.toFixed(1)}
          </span>
        </div>
      </div>
      {uniqueMeasurements.length > 0 && (
        <div className="mt-2 pt-2 border-t border-primary/10">
          <span className="text-[10px] text-muted-foreground">
            Measurements: {uniqueMeasurements.join(", ")}
          </span>
        </div>
      )}
    </div>
  );
}
