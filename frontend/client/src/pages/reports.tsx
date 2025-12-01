import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { FileText, Search, Download, MoreVertical, Loader2, ScrollText, ArrowUpDown, Trash2, Eye, ExternalLink } from "lucide-react";
import { ReportModal } from "@/components/training/ReportModal";
import { useState, useMemo } from "react";
import { Link } from "wouter";
import { toast } from "@/hooks/use-toast";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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

interface Report {
  id: string;
  name: string;
  size: string;
  date: string;
  model_name: string;
  path: string;
  training_time?: number;  // Training duration in seconds
}

function formatTrainingTime(seconds?: number): string {
  if (!seconds) return "-";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

export default function ReportsPage() {
  const queryClient = useQueryClient();
  const [showReport, setShowReport] = useState(false);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isExporting, setIsExporting] = useState(false);
  const [sortBy, setSortBy] = useState<string>("date-desc");
  const [modelFilter, setModelFilter] = useState<string>("all");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [reportToDelete, setReportToDelete] = useState<Report | null>(null);

  const { data: reports = [], isLoading } = useQuery<Report[]>({
    queryKey: ["/api/reports"],
  });

  const deleteMutation = useMutation({
    mutationFn: async (report: Report) => {
      const response = await fetch(`/api/reports/${report.id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete report');
      return response.json();
    },
    onSuccess: (_, report) => {
      queryClient.invalidateQueries({ queryKey: ["/api/reports"] });
      toast({
        title: "Report Deleted",
        description: `${report.name} has been removed.`,
        variant: "destructive"
      });
      setDeleteDialogOpen(false);
      setReportToDelete(null);
    },
    onError: (error: Error) => {
      toast({
        title: "Delete Failed",
        description: error.message,
        variant: "destructive"
      });
    },
  });

  const handleDeleteClick = (report: Report, e: React.MouseEvent) => {
    e.stopPropagation();
    setReportToDelete(report);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = () => {
    if (reportToDelete) {
      deleteMutation.mutate(reportToDelete);
    }
  };

  // Get unique model names for filter dropdown
  const modelNames = useMemo(() => {
    const models = new Set<string>();
    reports.forEach(r => models.add(r.model_name));
    return Array.from(models).sort();
  }, [reports]);

  // Filter and sort reports
  const filteredReports = useMemo(() => {
    let result = reports.filter(report =>
      report.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      report.model_name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Apply model filter
    if (modelFilter !== "all") {
      result = result.filter(r => r.model_name === modelFilter);
    }

    // Sort reports
    result.sort((a, b) => {
      switch (sortBy) {
        case "date-asc":
          return new Date(a.date).getTime() - new Date(b.date).getTime();
        case "name-asc":
          return a.name.localeCompare(b.name);
        case "name-desc":
          return b.name.localeCompare(a.name);
        case "model-asc":
          return a.model_name.localeCompare(b.model_name);
        case "date-desc":
        default:
          return new Date(b.date).getTime() - new Date(a.date).getTime();
      }
    });

    return result;
  }, [reports, searchQuery, modelFilter, sortBy]);

  const handleViewReport = (report: Report) => {
    setSelectedReport(report);
    setShowReport(true);
  };

  const handleDownload = async (report: Report, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const response = await fetch(`/api/training/report/download?path=${encodeURIComponent(report.path)}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        // Use actual filename from path for consistency
        const filename = report.path.split('/').pop() || report.name;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
      }
    } catch (error) {
      console.error('Failed to download report:', error);
    }
  };

  const handleExportAll = async () => {
    if (reports.length === 0) return;

    setIsExporting(true);
    try {
      const response = await fetch('/api/reports/export-all');
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        const filenameMatch = contentDisposition?.match(/filename=(.+)/);
        const filename = filenameMatch ? filenameMatch[1] : 'all_reports.zip';
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();

        // Show success message
        console.log(`Successfully downloaded: ${filename}`);
      } else {
        const errorText = await response.text();
        console.error('Export failed:', response.status, errorText);
        alert(`Failed to export reports: ${response.status} - ${errorText}`);
      }
    } catch (error) {
      console.error('Failed to export all reports:', error);
      alert(`Failed to export reports: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsExporting(false);
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
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-border pb-6">
        <div className="space-y-1">
          <h2 className="text-2xl font-bold tracking-tight text-primary">Reports Library</h2>
          <p className="text-muted-foreground text-base">Centralized archive of all experiment documentation.</p>
        </div>
        <Button
          className="gap-2 rounded-xl shadow-lg shadow-primary/20 hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
          onClick={handleExportAll}
          disabled={isExporting || reports.length === 0}
        >
          {isExporting ? (
            <>
              <Loader2 size={18} className="animate-spin" /> Exporting...
            </>
          ) : (
            <>
              <Download size={18} /> Export All
            </>
          )}
        </Button>
      </div>

      <div className="flex items-center gap-4 bg-white dark:bg-zinc-900 p-2 rounded-2xl border shadow-sm ring-1 ring-black/5">
         <div className="relative flex-1">
           <Search className="absolute left-3.5 top-3 h-4 w-4 text-muted-foreground" />
           <Input
             placeholder="Search filenames, models..."
             className="pl-10 h-10 bg-transparent border-none focus-visible:ring-0 placeholder:text-muted-foreground/60"
             value={searchQuery}
             onChange={(e) => setSearchQuery(e.target.value)}
           />
         </div>
         <div className="h-6 w-px bg-border mx-2" />
         <Select value={modelFilter} onValueChange={setModelFilter}>
           <SelectTrigger className="w-[200px] h-10 rounded-xl border-none bg-transparent hover:bg-muted/50 transition-colors">
             <SelectValue placeholder="All Models" />
           </SelectTrigger>
           <SelectContent>
             <SelectItem value="all">All Models</SelectItem>
             {modelNames.map(model => (
               <SelectItem key={model} value={model}>{model}</SelectItem>
             ))}
           </SelectContent>
         </Select>
         <div className="h-6 w-px bg-border" />
         <Select value={sortBy} onValueChange={setSortBy}>
           <SelectTrigger className="w-[200px] h-10 rounded-xl border-none bg-transparent hover:bg-muted/50 transition-colors">
             <ArrowUpDown size={14} className="mr-2 text-muted-foreground" />
             <SelectValue placeholder="Sort by" />
           </SelectTrigger>
           <SelectContent>
             <SelectItem value="date-desc">Newest First</SelectItem>
             <SelectItem value="date-asc">Oldest First</SelectItem>
             <SelectItem value="name-asc">Name A-Z</SelectItem>
             <SelectItem value="name-desc">Name Z-A</SelectItem>
             <SelectItem value="model-asc">Model A-Z</SelectItem>
           </SelectContent>
         </Select>
      </div>

      {filteredReports.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <ScrollText className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-semibold mb-2">No Reports Yet</h3>
          <p className="text-sm">Train a model with report generation enabled to see reports here.</p>
          <Link href="/training">
            <Button className="mt-4 hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200">Go to Training</Button>
          </Link>
        </div>
      ) : (
        <div className="rounded-2xl border bg-white/50 dark:bg-zinc-900/50 backdrop-blur-sm shadow-sm overflow-hidden">
          <Table>
            <TableHeader className="bg-muted/30">
              <TableRow className="hover:bg-transparent border-b border-border/60">
                <TableHead className="w-[400px] py-4 pl-6 text-xs uppercase tracking-wider font-semibold text-muted-foreground">Filename</TableHead>
                <TableHead className="py-4 text-xs uppercase tracking-wider font-semibold text-muted-foreground">Model</TableHead>
                <TableHead className="py-4 text-xs uppercase tracking-wider font-semibold text-muted-foreground">Generated</TableHead>
                <TableHead className="py-4 text-xs uppercase tracking-wider font-semibold text-muted-foreground">Training Time</TableHead>
                <TableHead className="py-4 text-xs uppercase tracking-wider font-semibold text-muted-foreground">Size</TableHead>
                <TableHead className="py-4 pr-6 text-right text-xs uppercase tracking-wider font-semibold text-muted-foreground">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredReports.map((report) => (
                <TableRow
                  key={report.id}
                  className="group cursor-pointer hover:bg-blue-50/50 dark:hover:bg-blue-900/10 transition-colors border-border/40"
                  onClick={() => handleViewReport(report)}
                >
                  <TableCell className="py-4 pl-6">
                    <div className="flex items-center gap-4">
                      <div className="bg-blue-100 dark:bg-blue-500/20 p-2.5 rounded-xl text-blue-600 dark:text-blue-400 shadow-sm group-hover:scale-105 transition-transform">
                        <FileText size={20} />
                      </div>
                      <div className="flex flex-col gap-0.5">
                        <span className="font-semibold text-sm text-foreground group-hover:text-blue-700 dark:group-hover:text-blue-400 transition-colors">{report.name}</span>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground font-medium">{report.model_name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground font-medium">{report.date}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{formatTrainingTime(report.training_time)}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded w-fit">{report.size}</TableCell>
                  <TableCell className="text-right pr-6">
                    <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 hover:text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/30 active:scale-95 active:bg-blue-200 dark:active:bg-blue-800/40 transition-all duration-150"
                        onClick={(e) => handleDownload(report, e)}
                      >
                        <Download size={16} />
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 hover:bg-muted hover:scale-110 hover:shadow-md active:scale-95 transition-all duration-200"
                            onClick={(e) => { e.stopPropagation(); }}
                          >
                            <MoreVertical size={16} />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              handleViewReport(report);
                            }}
                            className="gap-2 cursor-pointer focus:bg-primary/10"
                          >
                            <Eye size={16} />
                            View Report
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDownload(report, e as unknown as React.MouseEvent);
                            }}
                            className="gap-2 cursor-pointer focus:bg-primary/10"
                          >
                            <Download size={16} />
                            Download PDF
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation();
                              window.open(`/api/training/report/view?path=${encodeURIComponent(report.path)}`, '_blank');
                            }}
                            className="gap-2 cursor-pointer focus:bg-primary/10"
                          >
                            <ExternalLink size={16} />
                            Open in New Tab
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={(e) => handleDeleteClick(report, e as unknown as React.MouseEvent)}
                            className="gap-2 cursor-pointer text-destructive focus:text-destructive focus:bg-destructive/10"
                          >
                            <Trash2 size={16} />
                            Delete Report
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <ReportModal
        open={showReport}
        onOpenChange={setShowReport}
        modelName={selectedReport?.model_name}
        reportPath={selectedReport?.path}
      />

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Report</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <span className="font-semibold text-foreground">{reportToDelete?.name}</span>?
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
    </div>
  );
}
