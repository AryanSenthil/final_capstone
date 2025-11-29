import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Download, ZoomIn, ZoomOut, ChevronLeft, ChevronRight } from "lucide-react";
import { useState, useEffect } from "react";

interface ReportModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reportPath?: string;
  modelName?: string;
}

export function ReportModal({ open, onOpenChange, reportPath, modelName }: ReportModalProps) {
  const [zoom, setZoom] = useState(100);
  const [page, setPage] = useState(1);
  const totalPages = 5;

  // Reset page when modal opens
  useEffect(() => {
    if (open) {
      setPage(1);
      setZoom(100);
    }
  }, [open]);

  const handleDownload = async () => {
    if (reportPath) {
      try {
        const response = await fetch(`/api/training/report/download?path=${encodeURIComponent(reportPath)}`);
        if (response.ok) {
          const blob = await response.blob();
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `${modelName || 'training'}_report.pdf`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          a.remove();
        }
      } catch (error) {
        console.error('Failed to download report:', error);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl h-[90vh] flex flex-col p-0 overflow-hidden bg-zinc-100 dark:bg-zinc-900 gap-0 border-none outline-none">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-background border-b shrink-0">
          <h2 className="font-semibold text-sm flex items-center gap-2">
            <span className="bg-red-100 text-red-600 px-1.5 py-0.5 rounded text-xs font-bold">PDF</span>
            {modelName ? `${modelName}_Report.pdf` : 'Training_Report.pdf'}
          </h2>
          <div className="flex items-center gap-2 mr-6">
            <Button variant="outline" size="sm" className="h-8 gap-1" onClick={handleDownload}>
              <Download size={14} /> Download
            </Button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center justify-center gap-4 py-2 bg-muted/30 border-b text-sm shrink-0">
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" className="h-8 w-8" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
              <ChevronLeft size={16} />
            </Button>
            <span className="w-24 text-center">Page {page} of {totalPages}</span>
            <Button variant="ghost" size="icon" className="h-8 w-8" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>
              <ChevronRight size={16} />
            </Button>
          </div>
          <div className="w-px h-4 bg-border" />
          <div className="flex items-center gap-1">
             <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setZoom(z => Math.max(50, z - 10))}>
               <ZoomOut size={16} />
             </Button>
             <span className="w-16 text-center">{zoom}%</span>
             <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setZoom(z => Math.min(200, z + 10))}>
               <ZoomIn size={16} />
             </Button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-auto bg-zinc-200/50 dark:bg-zinc-950/50 p-8 flex justify-center">
          {reportPath ? (
            <iframe
              src={`/api/training/report/view?path=${encodeURIComponent(reportPath)}`}
              className="w-full h-full bg-white rounded shadow-xl"
              style={{
                transform: `scale(${zoom / 100})`,
                transformOrigin: 'top center',
              }}
            />
          ) : (
            <div
              className="bg-white shadow-xl transition-all duration-200 origin-top"
              style={{
                width: `${8.5 * 60 * (zoom/100)}px`,
                height: `${11 * 60 * (zoom/100)}px`,
              }}
            >
              {/* Mock Content */}
              <div className="p-12 text-zinc-900 space-y-6" style={{ fontSize: `${16 * (zoom/100)}px` }}>
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
