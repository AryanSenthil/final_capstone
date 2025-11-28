import { useState } from "react";
import { useRoute } from "wouter";
import { useQuery } from "@tanstack/react-query";
import type { Dataset, DataPoint } from "@/lib/mockData";
import { TimeSeriesChart } from "@/components/line-chart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Download, FileText, Info, ArrowLeft, ChevronRight, Loader2 } from "lucide-react";
import { Link } from "wouter";
import { cn } from "@/lib/utils";

interface FileInfo {
  name: string;
  size: string;
}

interface FileDataResponse {
  data: DataPoint[];
  yAxisLabel: string;
}

export default function LabelDetailView() {
  const [, params] = useRoute("/database/:id");
  const id = params?.id;

  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  // Track downloading state for individual files
  const [downloadingFiles, setDownloadingFiles] = useState<Record<string, boolean>>({});
  // Track downloading state for "Download All"
  const [downloadingAll, setDownloadingAll] = useState(false);

  // Fetch dataset metadata
  const { data: dataset, isLoading: datasetLoading, error: datasetError } = useQuery<Dataset>({
    queryKey: ["/api/labels", id],
    enabled: !!id,
  });

  // Fetch file list
  const { data: fileList, isLoading: filesLoading } = useQuery<FileInfo[]>({
    queryKey: ["/api/labels", id, "files"],
    enabled: !!id,
  });

  // Fetch chart data for selected file
  const { data: fileData, isLoading: chartLoading } = useQuery<FileDataResponse>({
    queryKey: ["/api/labels", id, "files", selectedFile],
    enabled: !!id && !!selectedFile,
  });

  const handleDownloadFile = (filename: string) => {
    setDownloadingFiles(prev => ({ ...prev, [filename]: true }));

    // Download in same tab using hidden anchor
    const link = document.createElement('a');
    link.href = `/api/labels/${id}/files/${filename}/download`;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Reset after short delay to show feedback
    setTimeout(() => {
      setDownloadingFiles(prev => ({ ...prev, [filename]: false }));
    }, 1500);
  };

  const handleDownloadAll = () => {
    setDownloadingAll(true);

    // Download in same tab using hidden anchor
    const link = document.createElement('a');
    link.href = `/api/labels/${id}/download`;
    link.download = `${id}.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Reset after short delay to show feedback
    setTimeout(() => {
      setDownloadingAll(false);
    }, 2000);
  };

  if (datasetLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] space-y-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-muted-foreground">Loading dataset...</p>
      </div>
    );
  }

  if (datasetError || !dataset) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] space-y-4">
        <h2 className="text-2xl font-bold text-primary">Dataset Not Found</h2>
        <p className="text-muted-foreground">Make sure the API server is running.</p>
        <Link href="/">
          <Button variant="outline"><ArrowLeft className="mr-2 h-4 w-4" /> Back to Database</Button>
        </Link>
      </div>
    );
  }

  const files = fileList || [];

  return (
    <div className="space-y-6 h-[calc(100vh-60px)] flex flex-col">
      {/* Breadcrumb Header */}
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Link href="/" className="hover:text-primary transition-colors">Database</Link>
        <ChevronRight className="h-4 w-4" />
        <span className="font-medium text-primary">{dataset.label}</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full min-h-0 pb-4">
        {/* Left Sidebar */}
        <Card className="lg:col-span-3 h-full flex flex-col border-border shadow-sm overflow-hidden">
          <CardHeader className="border-b border-border bg-muted/30 py-4">
            <div className="space-y-1">
              <CardTitle className="text-lg font-mono truncate text-primary" title={dataset.label}>
                {dataset.label}
              </CardTitle>
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground">{dataset.chunks} files</span>
                <Badge variant="outline" className="text-[10px] font-normal h-5">CSV</Badge>
              </div>
            </div>
          </CardHeader>
          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="p-2 border-b border-border bg-muted/10">
              <div className="text-xs font-medium text-muted-foreground px-2 mb-1 uppercase tracking-wider">Files</div>
            </div>
            <ScrollArea className="flex-1">
              <div className="p-2 space-y-1">
                {filesLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                ) : files.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground text-sm">
                    No files found
                  </div>
                ) : (
                  files.map((file) => (
                    <div
                      key={file.name}
                      className={cn(
                        "w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors font-mono group relative",
                        selectedFile === file.name
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "hover:bg-muted text-muted-foreground hover:text-foreground"
                      )}
                    >
                      <button
                        className="flex-1 text-left truncate flex items-center gap-2"
                        onClick={() => setSelectedFile(file.name)}
                      >
                        <FileText className={cn("h-3.5 w-3.5 opacity-70", selectedFile === file.name ? "text-primary-foreground" : "")} />
                        <span className="truncate">{file.name}</span>
                      </button>

                      {/* Individual Download Button */}
                      <Button
                        variant="ghost"
                        size="icon"
                        className={cn(
                          "h-6 w-6 absolute right-1 transition-all duration-200",
                          "hover:scale-110 hover:shadow-md active:scale-95",
                          downloadingFiles[file.name]
                            ? "opacity-100 bg-primary/10"
                            : "opacity-0 group-hover:opacity-100",
                          selectedFile === file.name
                            ? "text-primary-foreground hover:bg-primary-foreground/30"
                            : "hover:bg-primary hover:text-primary-foreground"
                        )}
                        title="Download file"
                        disabled={downloadingFiles[file.name]}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDownloadFile(file.name);
                        }}
                      >
                        {downloadingFiles[file.name] ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Download className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>
          <div className="p-4 border-t border-border bg-muted/30">
            <Button
              className={cn(
                "w-full gap-2 transition-all duration-200",
                "hover:bg-primary hover:text-primary-foreground hover:shadow-lg hover:scale-[1.02] hover:border-primary",
                "active:scale-[0.98]",
                downloadingAll && "bg-primary/10 border-primary/30"
              )}
              variant="outline"
              disabled={downloadingAll}
              onClick={handleDownloadAll}
            >
              {downloadingAll ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Downloading...
                </>
              ) : (
                <>
                  <Download className="h-4 w-4" /> Download All
                </>
              )}
            </Button>
          </div>
        </Card>

        {/* Right Content Area */}
        <div className="lg:col-span-9 flex flex-col gap-6 h-full overflow-y-auto lg:overflow-hidden pr-1">

          {/* Metadata Card */}
          <Card className="shadow-sm border-border shrink-0">
            <CardHeader className="pb-3 bg-muted/10 border-b border-border">
              <div className="flex items-center gap-2">
                <Info className="h-4 w-4 text-primary" />
                <h3 className="font-semibold text-primary">Dataset Information</h3>
              </div>
            </CardHeader>
            <CardContent className="pt-4 grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4 text-sm">
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <span className="text-muted-foreground">Classification:</span>
                  <span className="font-mono text-foreground">{dataset.label}</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <span className="text-muted-foreground">Data Type:</span>
                  <div>
                    <Badge className="bg-primary text-primary-foreground hover:bg-primary/90 font-medium text-xs px-2 py-0.5 h-auto rounded-md">
                      {dataset.measurement} ({dataset.unit})
                    </Badge>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <span className="text-muted-foreground">Total Files:</span>
                  <span>{dataset.chunks}</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <span className="text-muted-foreground">Generated:</span>
                  <span className="font-mono">{dataset.lastUpdated}</span>
                </div>
              </div>

              <div className="space-y-3">
                 <div className="grid grid-cols-2 gap-2">
                  <span className="text-muted-foreground">Duration:</span>
                  <span className="font-mono">{dataset.totalDuration}</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <span className="text-muted-foreground">Source File:</span>
                  <span className="font-mono text-xs truncate" title={dataset.sourceFile}>{dataset.sourceFile}</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <span className="text-muted-foreground">Interpolation:</span>
                  <span className="font-mono">{dataset.interpolationInterval}</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <span className="text-muted-foreground">Sampling Rate:</span>
                  <span>{dataset.stats.rate}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Graph Area */}
          <Card className="flex-1 border-border shadow-sm flex flex-col min-h-[550px]">
            <CardHeader className="pb-2 border-b border-border flex flex-row items-center justify-between">
              <div className="space-y-1">
                <CardTitle className="text-lg flex items-center gap-2 text-primary">
                  Time-Series Visualization
                </CardTitle>
                <p className="text-xs text-muted-foreground">
                  {selectedFile ? `Viewing: ${selectedFile}` : "Select a file to visualize"}
                </p>
              </div>
            </CardHeader>
            <CardContent className="flex-1 p-4 flex items-center justify-center">
              {chartLoading ? (
                 <div className="flex flex-col items-center gap-3 text-muted-foreground">
                   <div className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                   <p className="text-sm">Loading data...</p>
                 </div>
              ) : fileData && fileData.data && fileData.data.length > 0 ? (
                <TimeSeriesChart
                  data={fileData.data}
                  label={dataset.label}
                  yAxisLabel={fileData.yAxisLabel}
                  height={480}
                />
              ) : (
                <div className="text-center text-muted-foreground space-y-2">
                  <div className="bg-muted/30 p-4 rounded-full inline-block mb-2">
                    <FileText className="h-8 w-8 opacity-50" />
                  </div>
                  <p>Select a CSV file from the sidebar to render graph</p>
                </div>
              )}
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  );
}
