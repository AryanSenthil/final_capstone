# Frontend Client Architecture Guide

## Overview
React + TypeScript frontend using Express + Vite for sensor data visualization and AI-powered workflow management.

**Key Principle**: Client uploads files FROM user's computer TO server, displays data FROM server, and downloads results FROM server back to user's computer.

## Directory Structure

```
frontend/
├── client/
│   └── src/
│       ├── components/
│       │   ├── ui/              # Shadcn/ui components
│       │   │   ├── dialog.tsx
│       │   │   ├── button.tsx
│       │   │   ├── file-upload.tsx  # New native file uploader
│       │   │   └── ...
│       │   ├── add-data-modal.tsx   # Upload & process raw data
│       │   └── testing/
│       │       └── TestNewFileModal.tsx  # Upload & test files
│       ├── pages/
│       │   ├── chat.tsx         # AI chat interface
│       │   ├── data.tsx         # Data management
│       │   ├── training.tsx     # Model training
│       │   ├── testing.tsx      # Inference testing
│       │   └── reports.tsx      # Training reports
│       ├── lib/
│       │   └── queryClient.ts   # React Query setup
│       └── hooks/
│           └── use-toast.tsx    # Toast notifications
├── server/
│   ├── index.ts                 # Express server
│   └── vite.ts                  # Vite dev server
└── package.json
```

## Architecture Principles

### 1. Upload Flow (User → Server)

**All uploads use native file picker** (never browse server filesystem):

```typescript
// Pattern: Native file input + drag-and-drop
const fileInputRef = useRef<HTMLInputElement>(null);

// Click to browse
<input
  ref={fileInputRef}
  type="file"
  accept=".csv"
  multiple
  onChange={handleFileSelect}
  className="hidden"
/>
<div onClick={() => fileInputRef.current?.click()}>
  Click to browse
</div>

// Drag and drop
<div
  onDragOver={handleDragOver}
  onDrop={handleDrop}
>
  Drop files here
</div>

// Upload to server
const formData = new FormData();
selectedFiles.forEach(file => formData.append('files', file));
await fetch('/api/raw-database/upload', {
  method: 'POST',
  body: formData,
});
```

**Example Components**:
- `add-data-modal.tsx` - Upload raw data for processing
- `TestNewFileModal.tsx` - Upload test files for inference
- `chat.tsx` → `FileUploadDialog` - Upload files in chat

### 2. Download Flow (Server → User)

**All downloads fetch from server and trigger browser download**:

```typescript
// Pattern: Fetch blob and create download link
const downloadFile = async (url: string, filename: string) => {
  const response = await fetch(url);
  const blob = await response.blob();
  const objectUrl = window.URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();

  window.URL.revokeObjectURL(objectUrl);
  link.remove();
};

// Usage
downloadFile('/api/labels/damaged/download', 'damaged.zip');
```

### 3. Display Data from Server

**Fetch server data with React Query**:

```typescript
import { useQuery } from '@tanstack/react-query';

// Fetch processed labels
const { data: labels } = useQuery({
  queryKey: ['/api/labels'],
  // queryFn is automatic with queryClient setup
});

// Fetch specific label
const { data: label } = useQuery({
  queryKey: [`/api/labels/${labelId}`],
});
```

## Key Components

### Data Management Page (`data.tsx`)

**Two sections**:
1. **Processed Labels** (database/)
   - Display cards for each label
   - Download label data
   - Delete labels
   - View/edit metadata

2. **Raw Database** (raw_database/)
   - Display folders with CSV files
   - Download raw folders
   - Trigger ingestion (process → label)

**Upload Modal** (`add-data-modal.tsx`):
```typescript
// User flow:
// 1. Select files from THEIR computer (native picker)
// 2. Optionally name the folder
// 3. Enter classification label
// 4. Upload → POST /api/raw-database/upload
// 5. Process → POST /api/ingest
// 6. Polls until label appears in database
```

### Training Page (`training.tsx`)

**Features**:
- Select labels to train on
- Configure model parameters
- Start training (async job)
- Monitor progress
- View training report (PDF in modal)
- Download reports

**Training Flow**:
```typescript
// 1. Select labels
const [selectedLabels, setSelectedLabels] = useState<string[]>([]);

// 2. Start training
await fetch('/api/training/start', {
  method: 'POST',
  body: JSON.stringify({
    labels: selectedLabels,
    model_name: modelName,
    epochs: 50,
    batch_size: 32,
  }),
});

// 3. Poll status
const { data: status } = useQuery({
  queryKey: [`/api/training/status/${jobId}`],
  refetchInterval: status?.status === 'training' ? 2000 : false,
});

// 4. View report when done
<iframe src={`/api/training/report/view?model_id=${modelId}`} />
```

### Testing Page (`testing.tsx`)

**Features**:
- Upload test CSV files
- Run inference with trained models
- View predictions and confidence scores
- Compare test results
- Download test results

**Test Modal** (`TestNewFileModal.tsx`):
```typescript
// Multi-step wizard:
// Step 1: Select model
// Step 2: Upload files from user's computer (native picker)
// Step 3: Add optional notes (can AI-generate)
// Step 4: Upload & run inference
//   - POST /api/tests/upload (each file)
//   - POST /api/tests/inference (each file)
// Step 5: Show results
```

### Chat Page (`chat.tsx`)

**AI Agent Interface**:
- Chat with AI agent about data/models/workflows
- Agent uses tools to perform actions
- View artifacts (graphs, reports)
- Attach files via `FileUploadDialog`

**Key Features**:
```typescript
// Streaming responses
async function* streamChat(message: string, sessionId?: string) {
  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    body: JSON.stringify({ message, session_id: sessionId }),
  });

  for await (const event of parseSSE(res.body)) {
    switch (event.type) {
      case 'content': // Stream text
      case 'tool_start': // Tool call started
      case 'tool_result': // Tool completed
      case 'artifact': // Image/report generated
      case 'done': // Response complete
    }
  }
}

// Artifact display (images, PDFs)
<ArtifactsDisplay
  artifacts={message.artifacts}
  onImageExpand={showImageModal}
  onReportView={showPDFModal}
/>
```

**File Attachments in Chat**:
```typescript
// FileUploadDialog - Upload files from user's computer
<FileUploadDialog
  open={showFileBrowser}
  onClose={() => setShowFileBrowser(false)}
  onFilesUploaded={(files) => {
    // Attach uploaded files to next message
    setPendingAttachments(files.map(f => ({
      type: f.type === 'data' ? 'folder' : 'file',
      path: f.path,  // Server path after upload
      name: f.name,
    })));
  }}
/>
```

**IMPORTANT**:
- ❌ **DO NOT** use `FileBrowserDialog` (doesn't exist)
- ✅ **USE** `FileUploadDialog` (native file picker)
- Chat attachments reference server paths AFTER upload

## UI Patterns

### Interactive Buttons

**Always add hover/active effects** for better UX:

```typescript
// Action buttons (download, submit, etc.)
className="hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"

// Icon-only buttons
className="hover:scale-110 hover:shadow-md active:scale-95 transition-all duration-200"

// Example
<Button
  onClick={handleDownload}
  className="hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200"
>
  <Download className="w-4 h-4 mr-2" />
  Download
</Button>
```

### Toast Notifications

```typescript
import { useToast } from '@/hooks/use-toast';

const { toast } = useToast();

// Success
toast({
  title: "Success",
  description: "Data uploaded successfully",
});

// Error
toast({
  title: "Error",
  description: error.message,
  variant: "destructive",
  duration: 5000,
});
```

### File Upload Pattern

**Standard pattern for all file uploads**:

```typescript
const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
const [isDragging, setIsDragging] = useState(false);
const fileInputRef = useRef<HTMLInputElement>(null);

// Drag and drop
const handleDragOver = (e: React.DragEvent) => {
  e.preventDefault();
  setIsDragging(true);
};

const handleDrop = (e: React.DragEvent) => {
  e.preventDefault();
  setIsDragging(false);
  const files = Array.from(e.dataTransfer.files).filter(
    f => f.name.endsWith('.csv')
  );
  setSelectedFiles(prev => [...prev, ...files]);
};

// File input
const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
  if (e.target.files) {
    const files = Array.from(e.target.files);
    setSelectedFiles(prev => [...prev, ...files]);
    e.target.value = ''; // Reset for re-selection
  }
};

// JSX
<div
  onDragOver={handleDragOver}
  onDragLeave={() => setIsDragging(false)}
  onDrop={handleDrop}
  onClick={() => fileInputRef.current?.click()}
  className={cn(
    "border-2 border-dashed rounded-lg p-6 cursor-pointer",
    isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25"
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
  <Upload className="w-8 h-8" />
  <p>Click to browse or drag files here</p>
</div>
```

## React Query Setup

### Query Client Configuration (`lib/queryClient.ts`)

```typescript
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: async ({ queryKey }) => {
        const url = queryKey[0] as string;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Request failed');
        return res.json();
      },
    },
  },
});
```

**Usage**: Just specify the URL as queryKey:
```typescript
const { data } = useQuery({ queryKey: ['/api/labels'] });
```

### Mutations

```typescript
const mutation = useMutation({
  mutationFn: async (data: FormData) => {
    const res = await fetch('/api/raw-database/upload', {
      method: 'POST',
      body: data,
    });
    return res.json();
  },
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['/api/raw-database'] });
    toast({ title: "Upload successful" });
  },
  onError: (error) => {
    toast({ title: "Upload failed", variant: "destructive" });
  },
});
```

## Vite Proxy Configuration

**CRITICAL**: Frontend proxies `/api/*` to backend.

`frontend/server/vite.ts`:
```typescript
const serverOptions = {
  ...viteConfig.server,  // MUST spread to preserve proxy config
  middlewareMode: true,
  hmr: { server, path: "/vite-hmr" },
  allowedHosts: true as const,
};
```

`frontend/vite.config.ts`:
```typescript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

**If proxy breaks**:
- Check backend is running on port 8000
- Check `...viteConfig.server` is spread in `vite.ts`
- Restart frontend server

## Common Issues & Debugging

### 1. API Requests Return HTML Instead of JSON

**Symptoms**:
```typescript
// Expected: { labels: [...] }
// Actual: "<!DOCTYPE html>..."
```

**Cause**: Vite proxy not forwarding to backend

**Fix**:
1. Check backend running: `curl http://localhost:8000/api/labels`
2. Check proxy config spread: `...viteConfig.server` in `vite.ts`
3. Restart frontend: `npm run dev`

### 2. Files Not Uploading

**Check**:
1. Using `FormData` correctly
2. `Content-Type` NOT set (browser auto-sets with boundary)
3. Backend endpoint accepts `UploadFile` or `File`

```typescript
// ✅ Correct
const formData = new FormData();
formData.append('files', file);
await fetch('/api/upload', {
  method: 'POST',
  body: formData,  // NO Content-Type header
});

// ❌ Wrong
await fetch('/api/upload', {
  method: 'POST',
  headers: { 'Content-Type': 'multipart/form-data' },  // Don't set this
  body: formData,
});
```

### 3. Component Not Re-rendering After Mutation

**Fix**: Invalidate queries after mutations

```typescript
const mutation = useMutation({
  mutationFn: uploadData,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['/api/labels'] });
  },
});
```

### 4. Chat Agent Not Attaching Files

**Check**:
1. Using `FileUploadDialog` (NOT `FileBrowserDialog`)
2. Files uploaded BEFORE attaching to message
3. Using server paths (not local file objects)

```typescript
// ✅ Correct flow
// 1. User selects files via FileUploadDialog
// 2. Files upload to server → get server paths
// 3. Attach server paths to message
onFilesUploaded={(files) => {
  setPendingAttachments(files.map(f => ({
    type: 'file',
    path: f.path,  // Server path
    name: f.name,
  })));
}}

// ❌ Wrong
setPendingAttachments([{
  type: 'file',
  path: file,  // Local File object - won't work
  name: file.name,
}]);
```

## Styling Guidelines

### Tailwind Classes

```typescript
// Cards
className="bg-card border border-border rounded-lg p-4 shadow-sm"

// Buttons
className="bg-primary text-primary-foreground hover:bg-primary/90"

// Input focus
className="focus:ring-2 focus:ring-primary focus:border-primary"

// Dark mode support (automatic with class-based dark mode)
className="text-slate-800 dark:text-slate-200"
```

### Shadcn/ui Components

All UI components from Shadcn/ui:
- `Button`, `Dialog`, `Input`, `Textarea`
- `Select`, `ScrollArea`, `Progress`
- `Badge`, `Separator`, `Tabs`

**Import pattern**:
```typescript
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader } from "@/components/ui/dialog";
```

## Development Workflow

### Running Dev Server

```bash
# From project root
./dev.sh  # Starts both frontend and backend

# Or manually
cd frontend
npm run dev  # Port 5000
```

### Hot Reload

- **Frontend**: Vite HMR works for most changes
- **Server files**: May need restart for `server/` changes
- **Backend**: Uvicorn --reload handles Python changes

### Building for Production

```bash
cd frontend
npm run build  # Creates dist/

# Serve production build
npm run start
```

## When Adding New Features

### Adding a New Page

1. Create file in `client/src/pages/`
2. Add route in router setup
3. Add navigation link
4. Use React Query for data fetching
5. Follow upload/download patterns above

### Adding a New Modal

1. Use `Dialog` from Shadcn/ui
2. Follow file upload pattern if needed
3. Add hover effects to buttons
4. Use toast for feedback
5. Invalidate queries after mutations

### Modifying Data Flow

1. Check `SERVER.md` for backend changes needed
2. Update API calls in frontend
3. Update React Query keys
4. Test upload → process → display → download cycle
5. Update this documentation

## Testing

```bash
# Type check
npm run type-check

# Lint
npm run lint

# Build (checks for errors)
npm run build

# Test API endpoint
curl http://localhost:5000/api/labels
```

## File Upload Summary

**DO**:
- ✅ Use native file picker (`<input type="file">`)
- ✅ Support drag-and-drop
- ✅ Upload to server immediately
- ✅ Use `FormData` for file uploads
- ✅ Show upload progress
- ✅ Validate file types (CSV only)

**DON'T**:
- ❌ Browse server filesystem
- ❌ Use `FileBrowserDialog` (doesn't exist)
- ❌ Attach local file objects to chat
- ❌ Set Content-Type header for FormData
- ❌ Forget to invalidate queries after upload
