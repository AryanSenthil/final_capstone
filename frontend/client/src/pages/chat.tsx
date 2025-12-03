import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Send,
  Bot,
  User,
  Database,
  Brain,
  PlayCircle,
  FileBarChart,
  Loader2,
  Plus,
  X,
  MessageSquare,
  Settings2,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Wrench,
  RefreshCw,
  Paperclip,
  FileText,
  Download,
  ExternalLink,
  Folder,
  FolderOpen,
  Home,
  ChevronLeft,
  Image as ImageIcon,
  ZoomIn,
  Upload,
  HardDrive,
  File,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useToast } from "@/hooks/use-toast";

// Types
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  artifacts?: Artifact[];
  attachments?: Attachment[];
}

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  message_count: number;
}

interface ToolCall {
  name: string;
  arguments: Record<string, any>;
  result?: any;
}

interface Artifact {
  type: "image" | "report";
  name: string;
  data?: string; // base64 for images
  format?: string; // png, jpg, etc
  url?: string; // for reports
  filename?: string;
}

interface Attachment {
  type: "file" | "folder";
  path: string;
  name: string;
}

interface DirectoryItem {
  name: string;
  path: string;
  isDirectory: boolean;
}

// API functions
const API_BASE = "/api/chat";

async function fetchSessions(): Promise<ChatSession[]> {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

async function fetchSessionMessages(sessionId: string): Promise<{ messages: ChatMessage[] }> {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch messages");
  return res.json();
}

async function deleteSession(sessionId: string) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete session");
  return res.json();
}

// Streaming chat function
async function* streamChat(
  message: string,
  sessionId?: string
): AsyncGenerator<{ type: string; data: any }> {
  const res = await fetch(`${API_BASE}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  if (!res.ok) throw new Error("Failed to send message");

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          yield { type: data.type, data };
        } catch {
          // Skip invalid JSON
        }
      }
    }
  }
}

// Markdown components for styling - Claude/ChatGPT style
const markdownComponents = {
  p: ({ children }: any) => (
    <p className="mb-4 last:mb-0 text-slate-800 dark:text-slate-200 leading-7 text-[15px]">{children}</p>
  ),
  strong: ({ children }: any) => (
    <strong className="font-semibold text-slate-900 dark:text-white">{children}</strong>
  ),
  em: ({ children }: any) => <em className="italic">{children}</em>,
  ul: ({ children }: any) => (
    <ul className="mb-4 last:mb-0 pl-6 space-y-2 list-disc marker:text-slate-400 dark:marker:text-slate-500">{children}</ul>
  ),
  ol: ({ children }: any) => (
    <ol className="mb-4 last:mb-0 pl-6 space-y-2 list-decimal marker:text-slate-500 dark:marker:text-slate-400">{children}</ol>
  ),
  li: ({ children }: any) => (
    <li className="text-slate-800 dark:text-slate-200 leading-7 pl-1 text-[15px]">{children}</li>
  ),
  code: ({ children, className }: any) => {
    // Check if it's inline code (no className) or code block
    const isInline = !className;
    if (isInline) {
      return (
        <code className="bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 px-1.5 py-0.5 rounded text-sm font-mono border border-slate-200 dark:border-slate-700">
          {children}
        </code>
      );
    }
    return <code className={className}>{children}</code>;
  },
  pre: ({ children }: any) => (
    <pre className="bg-slate-900 dark:bg-slate-950 text-slate-100 p-4 rounded-lg overflow-x-auto my-4 text-sm font-mono leading-6 border border-slate-700">
      {children}
    </pre>
  ),
  h1: ({ children }: any) => (
    <h1 className="text-xl font-semibold mb-4 mt-6 first:mt-0 text-slate-900 dark:text-white">{children}</h1>
  ),
  h2: ({ children }: any) => (
    <h2 className="text-lg font-semibold mb-3 mt-5 first:mt-0 text-slate-900 dark:text-white">{children}</h2>
  ),
  h3: ({ children }: any) => (
    <h3 className="text-base font-semibold mb-2 mt-4 first:mt-0 text-slate-900 dark:text-white">{children}</h3>
  ),
  h4: ({ children }: any) => (
    <h4 className="text-[15px] font-semibold mb-2 mt-3 first:mt-0 text-slate-900 dark:text-white">{children}</h4>
  ),
  blockquote: ({ children }: any) => (
    <blockquote className="border-l-4 border-slate-300 dark:border-slate-600 pl-4 my-4 text-slate-600 dark:text-slate-400 italic text-[15px]">
      {children}
    </blockquote>
  ),
  hr: () => <hr className="my-6 border-slate-200 dark:border-slate-700" />,
  a: ({ children, href }: any) => (
    <a href={href} className="text-blue-600 dark:text-blue-400 hover:underline" target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
};

// Artifact Components - Claude-style image and report displays
function ImageArtifact({ artifact, onExpand }: { artifact: Artifact; onExpand: () => void }) {
  if (!artifact.data) return null;

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = `data:image/${artifact.format || "png"};base64,${artifact.data}`;
    link.download = artifact.name || `graph.${artifact.format || "png"}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="relative group my-3 max-w-md">
      <div className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 shadow-sm hover:shadow-md transition-shadow">
        <img
          src={`data:image/${artifact.format || "png"};base64,${artifact.data}`}
          alt={artifact.name}
          className="w-full h-auto cursor-pointer hover:opacity-95 transition-opacity"
          onClick={onExpand}
        />
      </div>
      <div className="flex items-center justify-between mt-2 px-1">
        <span className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5 font-medium">
          <ImageIcon className="w-3.5 h-3.5" />
          {artifact.name}
        </span>
        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleDownload}
            className="h-7 px-2 gap-1.5 text-xs hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-600 dark:hover:text-blue-400"
            title="Download image"
          >
            <Download className="w-3.5 h-3.5" />
            Download
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onExpand}
            className="h-7 px-2 gap-1.5 text-xs hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <ZoomIn className="w-3.5 h-3.5" />
            Expand
          </Button>
        </div>
      </div>
    </div>
  );
}

function ReportArtifact({ artifact, onView }: { artifact: Artifact; onView: () => void }) {
  if (!artifact.url) return null;

  const handleDownload = async () => {
    try {
      const response = await fetch(artifact.url!);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = artifact.filename || "report.pdf";
        document.body.appendChild(link);
        link.click();
        window.URL.revokeObjectURL(url);
        link.remove();
      }
    } catch (error) {
      console.error('Failed to download report:', error);
    }
  };

  return (
    <div className="my-4 p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-slate-800 dark:to-slate-800/50">
      <div className="flex items-center gap-3">
        <div className="p-2.5 rounded-lg bg-blue-100 dark:bg-blue-900/50">
          <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-slate-900 dark:text-white truncate">
            {artifact.name}
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            PDF Training Report
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onView}
            className="gap-1.5 text-xs hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            className="gap-1.5 text-xs hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
          >
            <Download className="w-3.5 h-3.5" />
            Download
          </Button>
        </div>
      </div>
    </div>
  );
}

function ArtifactsDisplay({
  artifacts,
  onImageExpand,
  onReportView,
}: {
  artifacts: Artifact[];
  onImageExpand: (artifact: Artifact) => void;
  onReportView: (artifact: Artifact) => void;
}) {
  if (!artifacts || artifacts.length === 0) return null;

  const images = artifacts.filter((a) => a.type === "image" && a.data);
  const reports = artifacts.filter((a) => a.type === "report" && a.url);

  return (
    <div className="mt-4 space-y-3">
      {/* Image Grid - show multiple images side by side */}
      {images.length > 0 && (
        <div className={cn(
          "grid gap-3",
          images.length === 1 ? "grid-cols-1" : images.length === 2 ? "grid-cols-2" : "grid-cols-2 lg:grid-cols-3"
        )}>
          {images.map((artifact, idx) => (
            <ImageArtifact
              key={idx}
              artifact={artifact}
              onExpand={() => onImageExpand(artifact)}
            />
          ))}
        </div>
      )}

      {/* Reports */}
      {reports.map((artifact, idx) => (
        <ReportArtifact key={idx} artifact={artifact} onView={() => onReportView(artifact)} />
      ))}
    </div>
  );
}

// Image Expand Modal
function ImageExpandModal({
  open,
  onClose,
  artifact,
}: {
  open: boolean;
  onClose: () => void;
  artifact: Artifact | null;
}) {
  if (!artifact || !artifact.data) return null;

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = `data:image/${artifact.format || "png"};base64,${artifact.data}`;
    link.download = artifact.name || `graph.${artifact.format || "png"}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] p-0 overflow-hidden bg-zinc-100 dark:bg-zinc-900">
        <DialogHeader className="p-4 pb-2 flex flex-row items-center justify-between border-b">
          <DialogTitle className="text-base font-medium flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-blue-100 dark:bg-blue-900/50">
              <ImageIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            {artifact.name}
          </DialogTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDownload}
            className="mr-6 gap-1.5 hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:text-blue-600 dark:hover:text-blue-400 hover:border-blue-300"
          >
            <Download className="w-4 h-4" />
            Download Image
          </Button>
        </DialogHeader>
        <div className="px-4 pb-4 overflow-auto bg-zinc-200/50 dark:bg-zinc-950/50 flex justify-center items-center">
          <img
            src={`data:image/${artifact.format || "png"};base64,${artifact.data}`}
            alt={artifact.name}
            className="max-w-full h-auto rounded-lg shadow-xl"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Report Viewer Modal - View PDFs in chat like training/reports pages
function ReportViewerModal({
  open,
  onClose,
  artifact,
}: {
  open: boolean;
  onClose: () => void;
  artifact: Artifact | null;
}) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadComplete, setDownloadComplete] = useState(false);

  if (!artifact || !artifact.url) return null;

  const handleDownload = async () => {
    if (!artifact.url || isDownloading) return;
    setIsDownloading(true);
    setDownloadComplete(false);
    try {
      const response = await fetch(artifact.url);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = artifact.filename || 'report.pdf';
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
  };

  // Build the view URL - convert download URL to view URL if needed
  const viewUrl = artifact.url.includes('/download?')
    ? artifact.url.replace('/download?', '/view?')
    : artifact.url;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl h-[90vh] flex flex-col p-0 overflow-hidden bg-zinc-100 dark:bg-zinc-900 gap-0 border-none outline-none">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-background border-b shrink-0">
          <h2 className="font-semibold text-sm flex items-center gap-2">
            <span className="bg-blue-100 dark:bg-blue-500/20 text-blue-600 dark:text-blue-400 px-1.5 py-0.5 rounded text-xs font-bold">PDF</span>
            {artifact.filename || artifact.name || 'Training Report'}
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
                  <CheckCircle2 size={14} /> Downloaded
                </>
              ) : (
                <>
                  <Download size={14} /> Download
                </>
              )}
            </Button>
          </div>
        </div>

        {/* PDF Viewer */}
        <div className="flex-1 overflow-auto bg-zinc-200/50 dark:bg-zinc-950/50 p-4 flex justify-center">
          <iframe
            src={`${viewUrl}#toolbar=0&navpanes=0`}
            className="w-full h-full bg-white rounded shadow-xl"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}

// File Upload Dialog for Attachments - Upload files from client computer
function FileUploadDialog({
  open,
  onClose,
  onFilesUploaded,
}: {
  open: boolean;
  onClose: () => void;
  onFilesUploaded: (files: Array<{ path: string; name: string; type: 'test' | 'data' }>) => void;
}) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadType, setUploadType] = useState<'test' | 'data'>('test');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files).filter(f => f.name.toLowerCase().endsWith('.csv'));
    if (files.length > 0) {
      setSelectedFiles(prev => [...prev, ...files]);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).filter(f => f.name.toLowerCase().endsWith('.csv'));
      setSelectedFiles(prev => [...prev, ...files]);
      e.target.value = '';
    }
  }, []);

  const removeFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadProgress(0);

    const uploadedFiles: Array<{ path: string; name: string; type: 'test' | 'data' }> = [];

    try {
      if (uploadType === 'test') {
        // Upload each file individually for testing
        for (let i = 0; i < selectedFiles.length; i++) {
          const file = selectedFiles[i];
          const formData = new FormData();
          formData.append('file', file);

          const response = await fetch('/api/tests/upload', {
            method: 'POST',
            body: formData,
          });

          const result = await response.json();

          if (response.ok && result.success) {
            uploadedFiles.push({
              path: result.file_path,
              name: file.name,
              type: 'test'
            });
          } else {
            throw new Error(result.detail || `Failed to upload ${file.name}`);
          }

          setUploadProgress(((i + 1) / selectedFiles.length) * 100);
        }
      } else {
        // Upload all files to raw_database as a batch
        const formData = new FormData();
        selectedFiles.forEach(file => formData.append('files', file));

        const response = await fetch('/api/raw-database/upload', {
          method: 'POST',
          body: formData,
        });

        const result = await response.json();

        if (response.ok && result.success) {
          // Add each uploaded file
          selectedFiles.forEach(file => {
            uploadedFiles.push({
              path: result.folder_path,
              name: file.name,
              type: 'data'
            });
          });
        } else {
          throw new Error(result.detail || 'Failed to upload files');
        }

        setUploadProgress(100);
      }

      toast({
        title: "Files Uploaded",
        description: `Successfully uploaded ${uploadedFiles.length} file(s)`,
      });

      onFilesUploaded(uploadedFiles);
      setSelectedFiles([]);
      onClose();

    } catch (error) {
      toast({
        title: "Upload Failed",
        description: error instanceof Error ? error.message : "Failed to upload files",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleClose = () => {
    if (!isUploading) {
      setSelectedFiles([]);
      onClose();
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] w-[95vw] max-h-[85vh] p-0 overflow-hidden flex flex-col">
        <DialogHeader className="p-4 pb-3 border-b border-border shrink-0">
          <DialogTitle className="text-lg font-semibold flex items-center gap-2">
            <Upload className="h-5 w-5 text-blue-500" />
            Upload Files from Your Computer
          </DialogTitle>
        </DialogHeader>

        <div className="p-4 space-y-4 flex-1 overflow-auto">
          {/* Upload Type Selection */}
          <div className="flex gap-2">
            <Button
              variant={uploadType === 'test' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setUploadType('test')}
              className="flex-1"
            >
              <PlayCircle className="h-4 w-4 mr-2" />
              For Testing/Inference
            </Button>
            <Button
              variant={uploadType === 'data' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setUploadType('data')}
              className="flex-1"
            >
              <Database className="h-4 w-4 mr-2" />
              For Data Import
            </Button>
          </div>

          <p className="text-xs text-muted-foreground">
            {uploadType === 'test'
              ? "Upload CSV files to run inference/testing with a trained model"
              : "Upload CSV files to add to the raw database for processing"
            }
          </p>

          {/* Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              "border-2 border-dashed rounded-lg p-8 transition-all cursor-pointer",
              isDragging && "border-primary bg-primary/5 scale-[1.02]",
              !isDragging && "border-muted-foreground/25 hover:border-primary hover:bg-muted/50"
            )}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              multiple
              onChange={handleFileSelect}
              className="hidden"
            />
            <div className="flex flex-col items-center gap-3 text-center">
              <div className={cn(
                "rounded-full p-4",
                isDragging ? "bg-primary/10" : "bg-muted"
              )}>
                <Upload className={cn(
                  "h-8 w-8",
                  isDragging ? "text-primary" : "text-muted-foreground"
                )} />
              </div>
              <div>
                <p className="font-medium text-foreground">
                  {isDragging ? "Drop files here" : "Click to browse or drag files here"}
                </p>
                <p className="text-sm text-muted-foreground">
                  CSV files only
                </p>
              </div>
            </div>
          </div>

          {/* Selected Files */}
          {selectedFiles.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">{selectedFiles.length} file(s) selected</p>
              <ScrollArea className={cn("border rounded-lg", selectedFiles.length > 4 ? "h-40" : "")}>
                <div className="p-2 space-y-1">
                  {selectedFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center gap-2 px-3 py-2 rounded-md text-sm bg-muted/50"
                    >
                      <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="flex-1 truncate">{file.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {(file.size / 1024).toFixed(1)} KB
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => removeFile(idx)}
                        disabled={isUploading}
                        className="h-6 w-6"
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}

          {/* Upload Progress */}
          {isUploading && (
            <div className="space-y-2">
              <div className="h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-xs text-center text-muted-foreground">
                Uploading... {Math.round(uploadProgress)}%
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border bg-muted/20 shrink-0 flex items-center justify-between gap-3">
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isUploading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleUpload}
            disabled={selectedFiles.length === 0 || isUploading}
          >
            {isUploading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Upload {selectedFiles.length > 0 ? `${selectedFiles.length} File(s)` : 'Files'}
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Message Component - Claude/ChatGPT style (no bubbles for assistant)
function MessageBubble({
  role,
  content,
  isLoading,
  toolCalls,
  isLastAssistant,
  onRegenerate,
  artifacts,
  onImageExpand,
  onReportView,
  attachments,
}: {
  role: "user" | "assistant";
  content?: string;
  isLoading?: boolean;
  toolCalls?: ToolCall[];
  isLastAssistant?: boolean;
  onRegenerate?: () => void;
  artifacts?: Artifact[];
  onImageExpand?: (artifact: Artifact) => void;
  onReportView?: (artifact: Artifact) => void;
  attachments?: Attachment[];
}) {
  if (role === "user") {
    // User messages: right-aligned with bubble
    return (
      <div className="flex justify-end mb-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
        <div className="max-w-[80%]">
          {/* Attachments */}
          {attachments && attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-2 justify-end">
              {attachments.map((att, idx) => (
                <div
                  key={idx}
                  className={cn(
                    "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs",
                    att.type === "folder"
                      ? "bg-blue-500/30 text-blue-100"
                      : "bg-primary/20 text-primary-foreground/80"
                  )}
                >
                  {att.type === "folder" ? (
                    <Folder className="w-3 h-3" />
                  ) : (
                    <FileText className="w-3 h-3" />
                  )}
                  <span className="truncate max-w-[200px]">{att.name}</span>
                </div>
              ))}
            </div>
          )}
          <div className="bg-primary text-primary-foreground px-4 py-3 rounded-2xl rounded-tr-sm text-[15px] leading-relaxed">
            <span className="whitespace-pre-wrap">{content}</span>
          </div>
        </div>
      </div>
    );
  }

  // Assistant messages: clean text, no bubble (like Claude/ChatGPT)
  return (
    <div className="mb-8 animate-in fade-in slide-in-from-bottom-2 duration-300 group">
      {/* Tool calls indicator */}
      {toolCalls && toolCalls.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {toolCalls.map((tc, idx) => (
            <div
              key={idx}
              className="inline-flex items-center gap-2 bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-full px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400"
            >
              <Wrench className="w-3 h-3" />
              <span className="font-medium">{tc.name.replace(/_/g, ' ')}</span>
              {tc.result?.status === "success" ? (
                <CheckCircle2 className="w-3 h-3 text-green-500" />
              ) : tc.result?.status === "error" ? (
                <AlertCircle className="w-3 h-3 text-red-500" />
              ) : (
                <Loader2 className="w-3 h-3 animate-spin" />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Loading state */}
      {isLoading && !content ? (
        <div className="flex items-center gap-3 text-slate-500 dark:text-slate-400">
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
            <div className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
            <div className="w-2 h-2 bg-slate-400 dark:bg-slate-500 rounded-full animate-bounce"></div>
          </div>
          <span className="text-sm">Thinking...</span>
        </div>
      ) : content ? (
        <>
          <div className="text-[15px]">
            <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
          </div>

          {/* Artifacts (images, reports) */}
          {artifacts && artifacts.length > 0 && onImageExpand && onReportView && (
            <ArtifactsDisplay artifacts={artifacts} onImageExpand={onImageExpand} onReportView={onReportView} />
          )}

          {/* Regenerate button - only on last assistant message */}
          {isLastAssistant && onRegenerate && (
            <div className="mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
              <button
                onClick={onRegenerate}
                className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Regenerate response
              </button>
            </div>
          )}
        </>
      ) : null}
    </div>
  );
}

// Suggestion Buttons Component
function SuggestionButtons({ onSelect }: { onSelect: (action: string) => void }) {
  const suggestions = [
    { icon: <Database className="w-4 h-4" />, label: "My Data", action: "What data do I have available?" },
    { icon: <Brain className="w-4 h-4" />, label: "Models", action: "Show me my trained models" },
    { icon: <PlayCircle className="w-4 h-4" />, label: "Train", action: "Help me train a new model" },
    { icon: <FileBarChart className="w-4 h-4" />, label: "Test", action: "Help me test a file" },
    { icon: <Settings2 className="w-4 h-4" />, label: "Help", action: "How does this app work?" },
    { icon: <Sparkles className="w-4 h-4" />, label: "Status", action: "What's the system status?" },
  ];

  return (
    <div className="flex gap-2 flex-wrap justify-center">
      {suggestions.map((s) => (
        <Button
          key={s.label}
          onClick={() => onSelect(s.action)}
          variant="outline"
          size="sm"
          className="gap-2 rounded-full border-slate-300 dark:border-border/50 bg-white dark:bg-transparent hover:bg-slate-100 dark:hover:bg-secondary/60 text-slate-700 dark:text-foreground hover:scale-105 active:scale-95 transition-all duration-200"
        >
          {s.icon}
          <span className="text-xs">{s.label}</span>
        </Button>
      ))}
    </div>
  );
}

// Chat Input Component
function ChatInput({
  onSend,
  disabled,
  attachments,
  onAttach,
  onRemoveAttachment,
}: {
  onSend: (message: string, attachments?: Attachment[]) => void;
  disabled?: boolean;
  attachments?: Attachment[];
  onAttach?: () => void;
  onRemoveAttachment?: (index: number) => void;
}) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = () => {
    if ((input.trim() || (attachments && attachments.length > 0)) && !disabled) {
      onSend(input, attachments);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  return (
    <div className="relative w-full max-w-7xl mx-auto">
      {/* Attachments preview */}
      {attachments && attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2 px-2">
          {attachments.map((att, idx) => (
            <div
              key={idx}
              className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs border",
                att.type === "folder"
                  ? "bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800"
                  : "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700"
              )}
            >
              {att.type === "folder" ? (
                <Folder className="w-3.5 h-3.5 text-blue-500" />
              ) : (
                <FileText className="w-3.5 h-3.5 text-slate-500" />
              )}
              <span className="truncate max-w-[200px]">{att.name}</span>
              {onRemoveAttachment && (
                <button
                  onClick={() => onRemoveAttachment(idx)}
                  className="ml-1 hover:text-red-500 transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="relative flex items-end gap-2 bg-slate-50 dark:bg-secondary/40 border border-slate-200 dark:border-border/60 rounded-2xl p-2 shadow-sm focus-within:ring-1 focus-within:ring-primary/50 focus-within:border-primary/50 transition-all">
        {/* Attach button */}
        {onAttach && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onAttach}
            disabled={disabled}
            className="h-9 w-9 rounded-xl shrink-0 text-muted-foreground hover:text-foreground hover:bg-slate-200 dark:hover:bg-slate-700 transition-all"
            title="Attach a file"
          >
            <Paperclip className="w-4 h-4" />
          </Button>
        )}

        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your data, models, or workflows..."
          className="min-h-[36px] max-h-[150px] py-2 px-3 resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 shadow-none placeholder:text-muted-foreground/60 text-sm"
          rows={1}
          disabled={disabled}
        />

        <Button
          onClick={handleSubmit}
          disabled={(!input.trim() && (!attachments || attachments.length === 0)) || disabled}
          size="icon"
          className={cn(
            "h-9 w-9 rounded-xl shrink-0 transition-all duration-200",
            input.trim() || (attachments && attachments.length > 0)
              ? "bg-primary text-primary-foreground hover:scale-105"
              : "bg-secondary/60 text-muted-foreground"
          )}
        >
          {disabled ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
        </Button>
      </div>
    </div>
  );
}

// Storage key for persisting session
const SESSION_STORAGE_KEY = "aryan-senthil-chat-session";

// Main Chat Page Component
export default function ChatPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(() => {
    // Load from localStorage on initial render
    if (typeof window !== "undefined") {
      return localStorage.getItem(SESSION_STORAGE_KEY);
    }
    return null;
  });
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Artifacts and attachments state
  const [currentArtifacts, setCurrentArtifacts] = useState<Artifact[]>([]);
  const [pendingAttachments, setPendingAttachments] = useState<Attachment[]>([]);
  const [showFileBrowser, setShowFileBrowser] = useState(false);
  const [expandedImage, setExpandedImage] = useState<Artifact | null>(null);
  const [viewingReport, setViewingReport] = useState<Artifact | null>(null);

  // Track sessions created during streaming (don't fetch these - we have local state)
  const newSessionCreatedRef = useRef<string | null>(null);

  // Fetch sessions
  const { data: sessions = [], refetch: refetchSessions } = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: fetchSessions,
  });

  // Persist session ID to localStorage when it changes
  useEffect(() => {
    if (currentSessionId) {
      localStorage.setItem(SESSION_STORAGE_KEY, currentSessionId);
    } else {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  }, [currentSessionId]);

  // Load session messages when session changes or on mount
  // BUT skip if this session was just created during streaming (we already have local state)
  useEffect(() => {
    if (currentSessionId) {
      // Skip fetch for sessions we just created - local state is already correct
      if (newSessionCreatedRef.current === currentSessionId) {
        newSessionCreatedRef.current = null;
        return;
      }

      fetchSessionMessages(currentSessionId)
        .then((data) => {
          setMessages(data.messages);
        })
        .catch(() => {
          // Session doesn't exist anymore, clear it
          setCurrentSessionId(null);
          setMessages([]);
        });
    }
  }, [currentSessionId]);

  // Auto scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streamingContent]);

  // Delete session mutation
  const deleteMutation = useMutation({
    mutationFn: deleteSession,
    onSuccess: (_, deletedId) => {
      refetchSessions();
      if (currentSessionId === deletedId) {
        const remaining = sessions.filter((s) => s.id !== deletedId);
        if (remaining.length > 0) {
          setCurrentSessionId(remaining[0].id);
        } else {
          handleNewChat();
        }
      }
    },
  });

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setCurrentToolCalls([]);
    setStreamingContent("");
    setCurrentArtifacts([]);
    setPendingAttachments([]);
  };

  const handleSelectSession = (id: string) => {
    if (id !== currentSessionId) {
      setCurrentSessionId(id);
      setCurrentToolCalls([]);
      setStreamingContent("");
      setCurrentArtifacts([]);
      setPendingAttachments([]);
    }
  };

  const handleCloseTab = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    deleteMutation.mutate(id);
  };

  const handleSendMessage = useCallback(
    async (text: string, attachments?: Attachment[]) => {
      // Build message content with attachments reference
      let messageContent = text;
      if (attachments && attachments.length > 0) {
        const refs = attachments.map((a) => {
          if (a.type === "folder") {
            return `Folder for data ingestion: ${a.path}`;
          }
          const ext = a.name.split('.').pop()?.toLowerCase() || '';
          if (ext === 'csv') {
            return `CSV file for testing: ${a.path}`;
          } else if (ext === 'pdf') {
            return `PDF file to read: ${a.path}`;
          } else {
            return `File: ${a.path}`;
          }
        }).join("\n");

        if (text) {
          messageContent = `${text}\n\nAttached:\n${refs}`;
        } else {
          // No text provided, create a helpful prompt based on attachment types
          const hasFolder = attachments.some(a => a.type === "folder");
          const hasCSV = attachments.some(a => a.type === "file" && a.name.toLowerCase().endsWith('.csv'));
          const hasPDF = attachments.some(a => a.type === "file" && a.name.toLowerCase().endsWith('.pdf'));

          if (hasFolder && !hasCSV && !hasPDF) {
            messageContent = `Please help me with this folder:\n${refs}`;
          } else if (hasCSV && !hasPDF && !hasFolder) {
            messageContent = `Please run inference/testing on this file:\n${refs}`;
          } else if (hasPDF && !hasCSV && !hasFolder) {
            messageContent = `Please read and summarize this PDF:\n${refs}`;
          } else {
            messageContent = `Please analyze these:\n${refs}`;
          }
        }
      }

      const userMsg: ChatMessage = {
        role: "user",
        content: messageContent,
        attachments: attachments
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      setCurrentToolCalls([]);
      setStreamingContent("");
      setCurrentArtifacts([]);
      setPendingAttachments([]); // Clear attachments after sending

      try {
        let newSessionId = currentSessionId;
        let fullContent = "";
        let collectedArtifacts: Artifact[] = [];

        for await (const event of streamChat(messageContent, currentSessionId || undefined)) {
          switch (event.type) {
            case "session":
              newSessionId = event.data.session_id;
              if (!currentSessionId) {
                // Mark this session as created during streaming - don't fetch messages for it
                newSessionCreatedRef.current = newSessionId;
                setCurrentSessionId(newSessionId);
              }
              break;

            case "tool_start":
              setCurrentToolCalls((prev) => [
                ...prev,
                { name: event.data.name, arguments: event.data.arguments },
              ]);
              break;

            case "tool_result":
              setCurrentToolCalls((prev) =>
                prev.map((tc) =>
                  tc.name === event.data.name ? { ...tc, result: event.data.result } : tc
                )
              );
              break;

            case "artifact":
              // Collect artifacts from tool results
              if (event.data.artifact) {
                collectedArtifacts.push(event.data.artifact);
                setCurrentArtifacts((prev) => [...prev, event.data.artifact]);
              }
              break;

            case "content":
              fullContent += event.data.content;
              setStreamingContent(fullContent);
              break;

            case "done":
              setMessages((prev) => [...prev, {
                role: "assistant",
                content: fullContent,
                artifacts: collectedArtifacts.length > 0 ? collectedArtifacts : undefined
              }]);
              setStreamingContent("");
              setCurrentToolCalls([]);
              setCurrentArtifacts([]);
              refetchSessions();
              break;

            case "error":
              // Show toast notification for API errors
              const errorMsg = event.data.error || event.data.message || "Unknown error";
              toast({
                title: "Error",
                description: errorMsg,
                variant: "destructive",
                duration: 8000, // Longer duration for API errors
              });
              setMessages((prev) => [
                ...prev,
                { role: "assistant", content: `Error: ${errorMsg}` },
              ]);
              break;
          }
        }
      } catch (error) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Error: ${error instanceof Error ? error.message : "Unknown error"}` },
        ]);
      } finally {
        setIsStreaming(false);
      }
    },
    [currentSessionId, refetchSessions]
  );

  const showWelcome = messages.length === 0 && !streamingContent && !isStreaming;

  // Handle regenerate - resend the last user message
  const handleRegenerate = useCallback(() => {
    if (messages.length < 2 || isStreaming) return;

    // Find the last user message
    let lastUserMsgIndex = -1;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        lastUserMsgIndex = i;
        break;
      }
    }

    if (lastUserMsgIndex === -1) return;

    const lastUserMsg = messages[lastUserMsgIndex].content;

    // Remove the last assistant message(s) after the last user message
    setMessages((prev) => prev.slice(0, lastUserMsgIndex));

    // Resend the message
    handleSendMessage(lastUserMsg);
  }, [messages, isStreaming, handleSendMessage]);

  // Get display title for a session
  const getTabTitle = (session: ChatSession) => {
    const title = session.title || "New Session";
    return title.length > 35 ? title.slice(0, 35) + "..." : title;
  };

  // Attachment handler for uploaded files
  const handleFilesUploaded = (files: Array<{ path: string; name: string; type: 'test' | 'data' }>) => {
    const newAttachments: Attachment[] = files.map(f => ({
      type: f.type === 'data' ? 'folder' as const : 'file' as const,
      path: f.path,
      name: f.name
    }));
    setPendingAttachments((prev) => [...prev, ...newAttachments]);
  };

  const handleRemoveAttachment = (index: number) => {
    setPendingAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  const handleImageExpand = (artifact: Artifact) => {
    setExpandedImage(artifact);
  };

  const handleReportView = (artifact: Artifact) => {
    setViewingReport(artifact);
  };

  return (
    <div className="absolute inset-0 flex flex-col bg-background">
      {/* Chrome-style Tab Bar */}
      <div className="flex items-center bg-secondary/30 border-b border-border px-2 pt-2 gap-1 overflow-x-auto shrink-0">
        {/* New Session Button - On the left */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-lg hover:bg-secondary/80 shrink-0 mr-1"
          onClick={handleNewChat}
          title="New Session"
        >
          <Plus className="w-4 h-4" />
        </Button>

        {/* New Session Tab (when no session selected) */}
        {currentSessionId === null && (
          <div
            className="flex items-center gap-2 px-3 py-2 rounded-t-lg bg-background border border-b-0 border-border text-foreground min-w-[140px]"
          >
            <Sparkles className="w-3.5 h-3.5 shrink-0 text-primary" />
            <span className="text-xs truncate">New Session</span>
          </div>
        )}

        {/* Existing Session Tabs */}
        {sessions.map((session) => (
          <div
            key={session.id}
            onClick={() => handleSelectSession(session.id)}
            className={cn(
              "group flex items-center gap-2 px-3 py-2 rounded-t-lg cursor-pointer transition-all min-w-[140px] max-w-[280px] border border-b-0",
              currentSessionId === session.id
                ? "bg-background border-border text-foreground"
                : "bg-secondary/50 border-transparent text-muted-foreground hover:bg-secondary/80 hover:text-foreground"
            )}
          >
            <MessageSquare className="w-3.5 h-3.5 shrink-0" />
            <span className="text-xs truncate flex-1">{getTabTitle(session)}</span>
            <button
              onClick={(e) => handleCloseTab(e, session.id)}
              className="opacity-0 group-hover:opacity-100 hover:bg-destructive/20 hover:text-destructive rounded p-0.5 transition-all"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}

        {/* Spacer and Status */}
        <div className="flex-1" />
        <div className="flex items-center gap-2 pr-2 shrink-0">
          {isStreaming && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Processing</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-background overflow-hidden">
        {/* Messages Area */}
        <ScrollArea className="flex-1 px-6 py-4">
          <div className="max-w-7xl mx-auto">
            {/* Welcome Message */}
            {showWelcome && (
              <div className="flex flex-col items-center justify-center h-[50vh] max-w-lg mx-auto text-center">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-5">
                  <Bot className="w-6 h-6 text-primary" />
                </div>
                <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
                  Hi! I'm your AI Assistant
                </h2>
                <p className="text-slate-600 dark:text-slate-400 text-[15px] leading-relaxed">
                  I can help you manage your sensor data, train AI models to detect damage, and test new files. Just ask me anything!
                </p>
              </div>
            )}

            {/* Message History */}
            {messages.map((msg, idx) => {
              // Check if this is the last assistant message
              const isLastAssistant =
                msg.role === "assistant" &&
                idx === messages.length - 1 &&
                !isStreaming;

              return (
                <MessageBubble
                  key={idx}
                  role={msg.role}
                  content={msg.content}
                  isLastAssistant={isLastAssistant}
                  onRegenerate={isLastAssistant ? handleRegenerate : undefined}
                  artifacts={msg.artifacts}
                  onImageExpand={handleImageExpand}
                  onReportView={handleReportView}
                  attachments={msg.attachments}
                />
              );
            })}

            {/* Streaming Response */}
            {(isStreaming || streamingContent) && (
              <MessageBubble
                role="assistant"
                content={streamingContent}
                isLoading={isStreaming && !streamingContent}
                toolCalls={currentToolCalls}
                artifacts={currentArtifacts}
                onImageExpand={handleImageExpand}
                onReportView={handleReportView}
              />
            )}

            <div ref={scrollRef} />
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="p-4 border-t border-border/50 bg-background/80 backdrop-blur-sm">
          {(showWelcome || (messages.length > 0 && messages.length < 4)) && !isStreaming && (
            <div className="mb-3 max-w-7xl mx-auto">
              <SuggestionButtons onSelect={(action) => handleSendMessage(action)} />
            </div>
          )}
          <ChatInput
            onSend={handleSendMessage}
            disabled={isStreaming}
            attachments={pendingAttachments}
            onAttach={() => setShowFileBrowser(true)}
            onRemoveAttachment={handleRemoveAttachment}
          />
        </div>
      </div>

      {/* File Upload Dialog */}
      <FileUploadDialog
        open={showFileBrowser}
        onClose={() => setShowFileBrowser(false)}
        onFilesUploaded={handleFilesUploaded}
      />

      {/* Image Expand Modal */}
      <ImageExpandModal
        open={expandedImage !== null}
        onClose={() => setExpandedImage(null)}
        artifact={expandedImage}
      />

      {/* Report Viewer Modal */}
      <ReportViewerModal
        open={viewingReport !== null}
        onClose={() => setViewingReport(null)}
        artifact={viewingReport}
      />
    </div>
  );
}
