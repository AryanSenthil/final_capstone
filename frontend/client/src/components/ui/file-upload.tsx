import React, { useState, useRef, useCallback } from 'react';
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Upload, X, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { cn } from '@/lib/utils';

export interface FileUploadProps {
  accept?: string;
  multiple?: boolean;
  maxSizeMB?: number;
  maxFiles?: number;
  uploadEndpoint?: string;
  onFilesSelected?: (files: File[]) => void;
  onUploadComplete?: (results: UploadResult[]) => void;
  onUploadError?: (error: string) => void;
  disabled?: boolean;
  className?: string;
  compact?: boolean;
}

export interface UploadResult {
  filename: string;
  success: boolean;
  file_path?: string;
  error?: string;
}

interface SelectedFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  result?: UploadResult;
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

export function FileUpload({
  accept = ".csv",
  multiple = true,
  maxSizeMB = 100,
  maxFiles = 50,
  uploadEndpoint,
  onFilesSelected,
  onUploadComplete,
  onUploadError,
  disabled = false,
  className,
  compact = false,
}: FileUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<SelectedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [overallProgress, setOverallProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((file: File): string | null => {
    // Check file type
    if (accept) {
      const acceptedTypes = accept.split(',').map(t => t.trim().toLowerCase());
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
      const fileMime = file.type.toLowerCase();

      const isAccepted = acceptedTypes.some(type => {
        if (type.startsWith('.')) {
          return fileExt === type;
        }
        if (type.includes('*')) {
          return fileMime.startsWith(type.split('*')[0]);
        }
        return fileMime === type;
      });

      if (!isAccepted) {
        return `File type not allowed. Accepted: ${accept}`;
      }
    }

    // Check file size
    const maxBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxBytes) {
      return `File too large. Maximum size: ${maxSizeMB}MB`;
    }

    return null;
  }, [accept, maxSizeMB]);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const filesArray = Array.from(newFiles);
    const validFiles: SelectedFile[] = [];
    const errors: string[] = [];

    for (const file of filesArray) {
      // Check max files limit
      if (selectedFiles.length + validFiles.length >= maxFiles) {
        errors.push(`Maximum ${maxFiles} files allowed`);
        break;
      }

      // Check for duplicates
      const isDuplicate = selectedFiles.some(sf => sf.file.name === file.name && sf.file.size === file.size);
      if (isDuplicate) {
        errors.push(`${file.name} is already selected`);
        continue;
      }

      // Validate file
      const error = validateFile(file);
      if (error) {
        errors.push(`${file.name}: ${error}`);
        continue;
      }

      validFiles.push({
        file,
        id: `${file.name}-${Date.now()}-${Math.random()}`,
        status: 'pending',
        progress: 0,
      });
    }

    if (errors.length > 0 && onUploadError) {
      onUploadError(errors.join('; '));
    }

    if (validFiles.length > 0) {
      const newSelection = multiple ? [...selectedFiles, ...validFiles] : validFiles;
      setSelectedFiles(newSelection);
      onFilesSelected?.(newSelection.map(sf => sf.file));
    }
  }, [selectedFiles, multiple, maxFiles, validateFile, onFilesSelected, onUploadError]);

  const removeFile = useCallback((id: string) => {
    setSelectedFiles(prev => {
      const newSelection = prev.filter(sf => sf.id !== id);
      onFilesSelected?.(newSelection.map(sf => sf.file));
      return newSelection;
    });
  }, [onFilesSelected]);

  const clearFiles = useCallback(() => {
    setSelectedFiles([]);
    onFilesSelected?.([]);
  }, [onFilesSelected]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled && !isUploading) {
      setIsDragging(true);
    }
  }, [disabled, isUploading]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (!disabled && !isUploading && e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  }, [disabled, isUploading, addFiles]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(e.target.files);
      e.target.value = ''; // Reset input
    }
  }, [addFiles]);

  const uploadFiles = useCallback(async () => {
    if (!uploadEndpoint || selectedFiles.length === 0 || isUploading) return;

    setIsUploading(true);
    const results: UploadResult[] = [];
    let completedCount = 0;

    for (const selectedFile of selectedFiles) {
      // Update status to uploading
      setSelectedFiles(prev => prev.map(sf =>
        sf.id === selectedFile.id ? { ...sf, status: 'uploading', progress: 0 } : sf
      ));

      try {
        const formData = new FormData();
        formData.append('file', selectedFile.file);

        const response = await fetch(uploadEndpoint, {
          method: 'POST',
          body: formData,
        });

        const result = await response.json();

        if (response.ok && result.success !== false) {
          const uploadResult: UploadResult = {
            filename: selectedFile.file.name,
            success: true,
            file_path: result.file_path || result.path,
          };
          results.push(uploadResult);

          setSelectedFiles(prev => prev.map(sf =>
            sf.id === selectedFile.id ? { ...sf, status: 'success', progress: 100, result: uploadResult } : sf
          ));
        } else {
          const uploadResult: UploadResult = {
            filename: selectedFile.file.name,
            success: false,
            error: result.detail || result.error || 'Upload failed',
          };
          results.push(uploadResult);

          setSelectedFiles(prev => prev.map(sf =>
            sf.id === selectedFile.id ? { ...sf, status: 'error', progress: 0, result: uploadResult } : sf
          ));
        }
      } catch (error) {
        const uploadResult: UploadResult = {
          filename: selectedFile.file.name,
          success: false,
          error: error instanceof Error ? error.message : 'Upload failed',
        };
        results.push(uploadResult);

        setSelectedFiles(prev => prev.map(sf =>
          sf.id === selectedFile.id ? { ...sf, status: 'error', progress: 0, result: uploadResult } : sf
        ));
      }

      completedCount++;
      setOverallProgress((completedCount / selectedFiles.length) * 100);
    }

    setIsUploading(false);
    setOverallProgress(0);
    onUploadComplete?.(results);
  }, [uploadEndpoint, selectedFiles, isUploading, onUploadComplete]);

  const hasSuccessfulUploads = selectedFiles.some(sf => sf.status === 'success');
  const hasPendingFiles = selectedFiles.some(sf => sf.status === 'pending');

  return (
    <div className={cn("space-y-4", className)}>
      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && !isUploading && fileInputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-lg transition-all cursor-pointer",
          compact ? "p-4" : "p-8",
          isDragging && "border-primary bg-primary/5 scale-[1.02]",
          disabled || isUploading ? "opacity-50 cursor-not-allowed" : "hover:border-primary hover:bg-muted/50",
          !isDragging && !disabled && "border-muted-foreground/25"
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleFileInputChange}
          className="hidden"
          disabled={disabled || isUploading}
        />

        <div className={cn("flex flex-col items-center gap-2 text-center", compact && "gap-1")}>
          <div className={cn(
            "rounded-full bg-muted p-3",
            compact && "p-2",
            isDragging && "bg-primary/10"
          )}>
            <Upload className={cn("h-6 w-6 text-muted-foreground", compact && "h-4 w-4", isDragging && "text-primary")} />
          </div>
          <div>
            <p className={cn("font-medium text-foreground", compact && "text-sm")}>
              {isDragging ? "Drop files here" : "Click to browse or drag files here"}
            </p>
            <p className={cn("text-sm text-muted-foreground", compact && "text-xs")}>
              {accept} files, up to {maxSizeMB}MB each
              {multiple && ` (max ${maxFiles} files)`}
            </p>
          </div>
        </div>
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-foreground">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
            </p>
            {!isUploading && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFiles}
                className="h-7 text-xs text-muted-foreground hover:text-foreground"
              >
                Clear All
              </Button>
            )}
          </div>

          <ScrollArea className={cn("border rounded-lg", selectedFiles.length > 4 ? "h-48" : "")}>
            <div className="p-2 space-y-1">
              {selectedFiles.map((sf) => (
                <div
                  key={sf.id}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors",
                    sf.status === 'success' && "bg-green-500/10",
                    sf.status === 'error' && "bg-red-500/10",
                    sf.status === 'uploading' && "bg-blue-500/10",
                    sf.status === 'pending' && "bg-muted/50"
                  )}
                >
                  {sf.status === 'success' ? (
                    <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0" />
                  ) : sf.status === 'error' ? (
                    <AlertCircle className="h-4 w-4 text-red-600 flex-shrink-0" />
                  ) : sf.status === 'uploading' ? (
                    <Loader2 className="h-4 w-4 text-blue-600 animate-spin flex-shrink-0" />
                  ) : (
                    <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                  )}

                  <div className="flex-1 min-w-0">
                    <p className="truncate font-medium">{sf.file.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatFileSize(sf.file.size)}
                      {sf.result?.error && (
                        <span className="text-red-600 ml-2">{sf.result.error}</span>
                      )}
                    </p>
                  </div>

                  {!isUploading && sf.status !== 'success' && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(sf.id);
                      }}
                      className="h-6 w-6 text-muted-foreground hover:text-foreground hover:bg-muted flex-shrink-0"
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>

          {/* Upload Progress */}
          {isUploading && (
            <div className="space-y-2">
              <Progress value={overallProgress} className="h-2" />
              <p className="text-xs text-center text-muted-foreground">
                Uploading... {Math.round(overallProgress)}%
              </p>
            </div>
          )}

          {/* Upload Button */}
          {uploadEndpoint && hasPendingFiles && !isUploading && (
            <Button
              onClick={uploadFiles}
              disabled={disabled}
              className="w-full hover:shadow-md hover:scale-[1.02] active:scale-[0.98] transition-all duration-200"
            >
              <Upload className="h-4 w-4 mr-2" />
              Upload {selectedFiles.filter(sf => sf.status === 'pending').length} File{selectedFiles.filter(sf => sf.status === 'pending').length !== 1 ? 's' : ''}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

export default FileUpload;
