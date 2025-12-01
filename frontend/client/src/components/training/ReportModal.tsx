import { useState } from "react";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Download, Loader2, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface ReportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reportPath?: string;
  modelName?: string;
}

export function ReportModal({ open, onOpenChange, reportPath, modelName }: ReportModalProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadComplete, setDownloadComplete] = useState(false);

  const handleDownload = async () => {
    if (reportPath && !isDownloading) {
      setIsDownloading(true);
      setDownloadComplete(false);
      try {
        const response = await fetch(`/api/training/report/download?path=${encodeURIComponent(reportPath)}`);
        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          // Use actual filename from path for consistency
          const filename = reportPath.split('/').pop() || `${modelName || 'training'}_report.pdf`;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          a.remove();
          setDownloadComplete(true);
          setTimeout(() => setDownloadComplete(false), 2000);
        }
      } catch (error) {
        console.error('Failed to download report:', error);
      } finally {
        setIsDownloading(false);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl h-[90vh] flex flex-col p-0 overflow-hidden bg-zinc-100 dark:bg-zinc-900 gap-0 border-none outline-none">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-background border-b shrink-0">
          <h2 className="font-semibold text-sm flex items-center gap-2">
            <span className="bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400 px-1.5 py-0.5 rounded text-xs font-bold">PDF</span>
            {modelName ? `${modelName}_Report.pdf` : 'Training_Report.pdf'}
          </h2>
          <div className="flex items-center gap-2 mr-6">
            <Button
              variant="outline"
              size="sm"
              className={cn(
                "h-8 gap-1.5 transition-all duration-200",
                "hover:bg-primary hover:text-primary-foreground hover:border-primary hover:shadow-md",
                "active:scale-95 active:shadow-sm",
                isDownloading && "opacity-70 cursor-wait",
                downloadComplete && "bg-green-500 text-white border-green-500 hover:bg-green-600"
              )}
              onClick={handleDownload}
              disabled={isDownloading}
            >
              {isDownloading ? (
                <>
                  <Loader2 size={14} className="animate-spin" /> Downloading...
                </>
              ) : downloadComplete ? (
                <>
                  <Check size={14} /> Downloaded
                </>
              ) : (
                <>
                  <Download size={14} /> Download
                </>
              )}
            </Button>
          </div>
        </div>


        {/* Content Area */}
        <div className="flex-1 overflow-auto bg-zinc-200/50 dark:bg-zinc-950/50 p-4 flex justify-center">
          {reportPath ? (
            <iframe
              src={`/api/training/report/view?path=${encodeURIComponent(reportPath)}#toolbar=0&navpanes=0`}
              className="w-full h-full bg-white rounded shadow-xl"
            />
          ) : (
            <div
              className="bg-white shadow-xl w-full max-w-3xl"
            >
              {/* Mock Content */}
              <div className="p-12 text-zinc-900 space-y-6">
                <div className="border-b-2 border-zinc-900 pb-4 mb-8">
                  <h1 className="font-bold text-3xl">Model Training Report</h1>
                  <p className="text-zinc-500 mt-2">Generated on {new Date().toLocaleDateString()}</p>
                </div>

                <div className="grid grid-cols-2 gap-8">
                  <div className="bg-zinc-50 p-4 rounded border">
                     <h3 className="font-bold text-sm uppercase text-zinc-500 mb-2">Model Architecture</h3>
                     <p className="font-mono text-lg">ResNet-50</p>
                  </div>
                  <div className="bg-zinc-50 p-4 rounded border">
                     <h3 className="font-bold text-sm uppercase text-zinc-500 mb-2">Training Duration</h3>
                     <p className="font-mono text-lg">4h 23m</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <h3 className="font-bold text-lg">Executive Summary</h3>
                  <p className="leading-relaxed text-zinc-700">
                    The model achieved a validation accuracy of <strong>94.5%</strong> on the test set.
                    Convergence was observed around epoch 450. There were no signs of significant overfitting
                    observed in the loss curves.
                  </p>
                </div>

                <div className="mt-12 p-6 bg-blue-50 rounded-lg border border-blue-100">
                   <h4 className="text-blue-800 font-bold mb-2">Performance Metrics</h4>
                   <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-2xl font-bold text-blue-900">94.5%</div>
                        <div className="text-xs uppercase text-blue-600 font-bold">Accuracy</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-blue-900">0.18</div>
                        <div className="text-xs uppercase text-blue-600 font-bold">Loss</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-blue-900">0.92</div>
                        <div className="text-xs uppercase text-blue-600 font-bold">F1 Score</div>
                      </div>
                   </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
