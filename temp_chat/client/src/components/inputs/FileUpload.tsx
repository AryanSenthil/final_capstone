import { useState, useCallback } from 'react';
import { UploadCloud, FileText, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface FileUploadProps {
  onUploadComplete: (fileName: string) => void;
}

export function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.endsWith('.csv')) {
      handleFileSelection(droppedFile);
    }
  };

  const handleFileSelection = (selectedFile: File) => {
    setFile(selectedFile);
    simulateUpload(selectedFile);
  };

  const simulateUpload = (file: File) => {
    setUploading(true);
    // Simulate upload delay
    setTimeout(() => {
      setUploading(false);
      onUploadComplete(file.name);
    }, 2000);
  };

  const reset = () => {
    setFile(null);
    setUploading(false);
  };

  return (
    <div className="w-full max-w-md">
      {!file ? (
        <div
          className={cn(
            "border-2 border-dashed rounded-lg p-8 text-center transition-colors duration-200 cursor-pointer flex flex-col items-center gap-3",
            isDragging 
              ? "border-primary bg-primary/10" 
              : "border-border hover:border-primary/50 hover:bg-secondary/50"
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-upload')?.click()}
        >
          <input 
            type="file" 
            id="file-upload" 
            className="hidden" 
            accept=".csv"
            onChange={(e) => e.target.files?.[0] && handleFileSelection(e.target.files[0])}
          />
          <div className="p-3 bg-secondary rounded-full">
            <UploadCloud className="w-6 h-6 text-muted-foreground" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">Click to upload or drag and drop</p>
            <p className="text-xs text-muted-foreground mt-1">CSV files only (max 10MB)</p>
          </div>
        </div>
      ) : (
        <div className="border rounded-lg p-4 bg-card animate-in fade-in duration-300">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded text-primary">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">{file.name}</p>
                <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
              </div>
            </div>
            {uploading ? (
              <div className="flex items-center text-xs text-muted-foreground">
                <Loader2 className="w-3 h-3 animate-spin mr-2" /> Uploading...
              </div>
            ) : (
               <div className="text-xs text-green-500 font-medium flex items-center">
                 Uploaded
               </div>
            )}
          </div>
          {uploading && (
            <div className="h-1 w-full bg-secondary mt-3 rounded-full overflow-hidden">
              <div className="h-full bg-primary animate-progress-indeterminate origin-left"></div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
