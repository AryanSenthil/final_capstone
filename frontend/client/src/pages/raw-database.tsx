import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { RawFolder } from "@/lib/mockData";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger
} from "@/components/ui/collapsible";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Folder,
  ChevronDown,
  ChevronUp,
  FileText,
  Download,
  Calendar,
  HardDrive,
  Loader2,
  Search,
  ArrowUpDown
} from "lucide-react";
import { cn } from "@/lib/utils";

export default function RawDatabasePage() {
  // Track expanded state for each folder
  const [expandedFolders, setExpandedFolders] = useState<Record<string, boolean>>({});
  // Track downloading state for individual files (key: "folderId-filename")
  const [downloadingFiles, setDownloadingFiles] = useState<Record<string, boolean>>({});
  // Track downloading state for "Download All" per folder
  const [downloadingFolders, setDownloadingFolders] = useState<Record<string, boolean>>({});
  // Search and sort state
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("date-desc");

  const handleDownloadFile = async (folderId: string, filename: string) => {
    const key = `${folderId}-${filename}`;
    setDownloadingFiles(prev => ({ ...prev, [key]: true }));

    // Download in same tab using hidden anchor
    const link = document.createElement('a');
    link.href = `/api/raw-database/${folderId}/files/${filename}/download`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Reset after short delay to show feedback
    setTimeout(() => {
      setDownloadingFiles(prev => ({ ...prev, [key]: false }));
    }, 1500);
  };

  const handleDownloadAll = async (folderId: string) => {
    setDownloadingFolders(prev => ({ ...prev, [folderId]: true }));

    // Download in same tab using hidden anchor
    const link = document.createElement('a');
    link.href = `/api/raw-database/${folderId}/download`;
    link.download = `${folderId}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Reset after short delay to show feedback
    setTimeout(() => {
      setDownloadingFolders(prev => ({ ...prev, [folderId]: false }));
    }, 2000);
  };

  // Fetch raw folders
  const { data: rawFolders, isLoading, error } = useQuery<RawFolder[]>({
    queryKey: ["/api/raw-database"],
    refetchInterval: 3000, // Auto-refresh every 3 seconds
  });

  // Filter and sort folders
  const filteredFolders = useMemo(() => {
    if (!rawFolders) return [];

    let result = [...rawFolders];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(folder =>
        folder.name.toLowerCase().includes(query)
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
        case "files-desc":
          return b.fileCount - a.fileCount;
        case "files-asc":
          return a.fileCount - b.fileCount;
        case "date-desc":
        default:
          return new Date(b.date).getTime() - new Date(a.date).getTime();
      }
    });

    return result;
  }, [rawFolders, searchQuery, sortBy]);

  const toggleFolder = (id: string) => {
    setExpandedFolders(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[40vh] gap-3 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm">Loading raw data folders...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-[40vh] gap-3 text-destructive">
        <p className="text-sm">Failed to load raw data. Make sure the API server is running.</p>
      </div>
    );
  }

  const folders = rawFolders || [];

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-border pb-6">
        <div className="space-y-1">
          <h2 className="text-2xl font-bold tracking-tight text-primary">Raw Data Files</h2>
          <p className="text-muted-foreground text-base">
            Original imported sensor data before processing
          </p>
        </div>
      </div>

      {/* Search and Filter Bar */}
      {rawFolders && rawFolders.length > 0 && (
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search folders..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 h-10"
            />
          </div>
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-[220px] h-10">
              <ArrowUpDown className="h-4 w-4 mr-2 text-muted-foreground" />
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date-desc">Newest First</SelectItem>
              <SelectItem value="date-asc">Oldest First</SelectItem>
              <SelectItem value="name-asc">Name A-Z</SelectItem>
              <SelectItem value="name-desc">Name Z-A</SelectItem>
              <SelectItem value="files-desc">Most Files</SelectItem>
              <SelectItem value="files-asc">Fewest Files</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* List View */}
      {!rawFolders || rawFolders.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-[30vh] gap-3 text-muted-foreground">
          <p className="text-lg font-medium">No raw data folders found</p>
          <p className="text-sm">Import data using the "Add Data" button to see raw files here</p>
        </div>
      ) : filteredFolders.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-[30vh] gap-3 text-muted-foreground">
          <Search className="h-12 w-12 opacity-50" />
          <p className="text-lg font-medium">No results found</p>
          <p className="text-sm">Try adjusting your search terms</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredFolders.map((folder) => (
            <Collapsible
              key={folder.id}
              open={expandedFolders[folder.id]}
              onOpenChange={() => toggleFolder(folder.id)}
              className="border border-border rounded-lg bg-card shadow-sm transition-all hover:shadow-md"
            >
              <div
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/5 transition-colors"
                onClick={() => toggleFolder(folder.id)}
              >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                  <div className={cn(
                    "h-10 w-10 rounded-md flex items-center justify-center transition-colors",
                    expandedFolders[folder.id] ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                  )}>
                    <Folder className="h-5 w-5" />
                  </div>

                  <div className="space-y-1 min-w-0">
                    <h3 className="text-base font-semibold font-mono truncate text-primary">{folder.name}</h3>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <FileText className="h-3 w-3" /> {folder.fileCount} files
                      </span>
                      <span className="flex items-center gap-1">
                        <HardDrive className="h-3 w-3" /> {folder.size}
                      </span>
                      <span className="flex items-center gap-1 hidden sm:flex">
                        <Calendar className="h-3 w-3" /> {folder.date}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center text-muted-foreground">
                   {expandedFolders[folder.id] ? (
                      <ChevronUp className="h-5 w-5" />
                    ) : (
                      <ChevronDown className="h-5 w-5" />
                    )}
                </div>
              </div>

              <CollapsibleContent>
                <div className="border-t border-border bg-muted/5 p-6">
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                    {/* Files List */}
                    <div className="lg:col-span-2 border border-border rounded-md bg-background overflow-hidden flex flex-col max-h-[300px]">
                      <div className="bg-muted/30 px-4 py-2 border-b border-border flex justify-between items-center">
                        <span className="text-sm font-medium text-primary">Files ({folder.fileCount})</span>
                        <Button
                          variant="ghost"
                          size="sm"
                          className={cn(
                            "h-7 text-xs transition-all duration-200",
                            "hover:bg-primary hover:text-primary-foreground hover:shadow-md hover:scale-105",
                            "active:scale-95",
                            downloadingFolders[folder.id] && "bg-primary/10 text-primary"
                          )}
                          disabled={downloadingFolders[folder.id]}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDownloadAll(folder.id);
                          }}
                        >
                          {downloadingFolders[folder.id] ? (
                            <>
                              <Loader2 className="mr-2 h-3 w-3 animate-spin" /> Downloading...
                            </>
                          ) : (
                            <>
                              <Download className="mr-2 h-3 w-3" /> Download All
                            </>
                          )}
                        </Button>
                      </div>
                      <div className="overflow-y-auto p-2 space-y-1">
                        {folder.files.map((file, idx) => (
                          <div key={idx} className="flex justify-between items-center px-3 py-2 text-sm hover:bg-muted/50 rounded-sm group transition-colors">
                            <span className="truncate font-mono text-muted-foreground group-hover:text-foreground">{file.name}</span>
                            <div className="flex items-center gap-3">
                               <span className="text-xs text-muted-foreground">{file.size}</span>
                               <Button
                                 variant="ghost"
                                 size="icon"
                                 className={cn(
                                   "h-6 w-6 transition-all duration-200",
                                   "hover:bg-primary hover:text-primary-foreground hover:shadow-md hover:scale-110",
                                   "active:scale-95",
                                   downloadingFiles[`${folder.id}-${file.name}`]
                                     ? "opacity-100 bg-primary/10"
                                     : "opacity-0 group-hover:opacity-100"
                                 )}
                                 title="Download file"
                                 disabled={downloadingFiles[`${folder.id}-${file.name}`]}
                                 onClick={(e) => {
                                   e.stopPropagation();
                                   handleDownloadFile(folder.id, file.name);
                                 }}
                               >
                                 {downloadingFiles[`${folder.id}-${file.name}`] ? (
                                   <Loader2 className="h-3 w-3 animate-spin" />
                                 ) : (
                                   <Download className="h-3 w-3" />
                                 )}
                               </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Metadata Panel */}
                    <div className="space-y-4">
                      <div className="border border-border rounded-md bg-background p-4 space-y-4">
                        <h4 className="font-medium text-sm border-b border-border pb-2 mb-2 text-primary">Metadata</h4>

                        <div className="space-y-3 text-sm">
                          <div>
                            <p className="text-xs text-muted-foreground">Import Folder</p>
                            <p className="font-mono text-xs break-all">{folder.name}</p>
                          </div>

                          <div>
                            <p className="text-xs text-muted-foreground">Imported At</p>
                            <p>{folder.metadata.importedAt}</p>
                          </div>

                          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-border/50">
                            <div>
                              <p className="text-xs text-muted-foreground">Avg Size</p>
                              <p>{folder.metadata.avgSize}</p>
                            </div>
                            <div>
                              <p className="text-xs text-muted-foreground">Largest</p>
                              <p>{folder.metadata.largest}</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          ))}
        </div>
      )}
    </div>
  );
}
