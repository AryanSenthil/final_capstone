# UI Interactive Elements Reference

**Total: 119 Interactive Elements**

This document maps every button and browsing element to its data source (read from) and destination (write to).

---

## Summary by Data Flow

| Flow Type | Count | Description |
|-----------|-------|-------------|
| **Client → Server** | 15 | File uploads, form submissions |
| **Server → Client** | 18 | Downloads, data fetching |
| **Server → Display** | 42 | Read-only data display |
| **Client-Only** | 28 | UI state, navigation, modals |
| **Server → Server** | 16 | Processing, training, inference |

---

## CHAT PAGE (`pages/chat.tsx`)

| # | Element | Label | Action | Read From | Write To | 
|---|---------|-------|--------|-----------|----------|
| 1c | Button | "New Session" (Plus) | `handleNewChat()` | - | Server: `POST /api/chat/sessions` |  
| 2c | Button | X (close tab) | `handleCloseTab()` | - | Server: `DELETE /api/chat/sessions/{id}` |
| 3c | Button | Suggestion chips | `onSelect(action)` | - | Server: `POST /api/chat/stream` | 
| 4c | Button | Paperclip (attach) | Opens file upload | - | Client: UI state | 
| 5c | Button | Send arrow | `handleSubmit()` | Client: message input | Server: `POST /api/chat/stream` |  
| 6c | Button | Regenerate | `onRegenerate()` | Server: session history | Server: `POST /api/chat/stream` |  
| 7c | Image | Artifact thumbnail | `onExpand()` | Server: base64 artifact | Client: modal state | Correct 
| 8c | Button | "Download" image | `handleDownload()` | Server: base64 artifact | Client: browser download | 
| 9c | Button | "Expand" image | Opens modal | Server: artifact data | Client: modal state | Correct 
| 10c | Button | "Download Image" (modal) | Downloads expanded | Server: base64 artifact | Client: browser download | Correct 
| 11c | Button | "View" report | Opens viewer | Server: `/api/training/report/view` | Client: iframe modal | Correct 
| 12c | Button | "Download" report | Downloads PDF | Server: `/api/training/report/download` | Client: browser download | Correct 
| 13c | Button | "Download" (viewer) | `handleDownload()` | Server: report PDF | Client: browser download |
| 14c | Button | "For Testing/Inference" | `setUploadType('test')` | - | Client: UI state | 
| 15c | Button | "For Data Import" | `setUploadType('data')` | - | Client: UI state |
| 16c | Drop Zone | Drag/drop area | `handleDrop()` | Client: user's computer | Client: file list state |
| 17c | Button | X (remove file) | `removeFile(idx)` | - | Client: file list state |
| 18c | Button | "Cancel" | `handleClose()` | - | Client: modal state |
| 19c | Button | "Upload Files" | `handleUpload()` | Client: selected files | Server: `POST /api/tests/upload` or `POST /api/raw-database/upload` |

---

## DATABASE PAGE (`pages/database.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 20c | Input | Search field | `setSearchQuery()` | - | Client: filter state |
| 21c | Select | Sort dropdown | `setSortBy()` | - | Client: sort state |
| 22c | Dialog | "Add Data" | Opens AddDataModal | - | Client: modal state |

**Data Display (implicit):**
- Labels list: Read from Server `GET /api/labels`

---

## TRAINING PAGE (`pages/training.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 23c | Input | Model name | `setModelName()` | - | Client: form state |
| 24c | Button | Wand (AI name) | `generateNameMutation.mutate()` | Server: `POST /api/suggest-model-name` | Client: model name input |
| 25c | Button | "Choose Training Data" | Opens FolderSelector | Server: `GET /api/labels` | Client: modal state |
| 26c | Button | X (remove badge) | `removeFolder()` | - | Client: selection state |
| 27c| Button | "CNN" | `onChange("CNN")` | - | Client: architecture state |
| 28c | Button | "ResNet" | `onChange("ResNet")` | - | Client: architecture state |
| 29c | Button | "Start Training" | `startTraining()` | Client: form data | Server: `POST /api/training/start` → `models/{id}/` |
| 30c | Button | "Stop Training" | `stopTraining()` | - | Server: `POST /api/training/stop/{job_id}` |
| 31c | Button | "Start New" | `resetTraining()` | - | Client: reset form state |
| 32c | Button | "View Report" | `setShowReport(true)` | Server: `/api/training/report/view` | Client: modal state |
| 33c | Button | Download (report) | `handleDownloadReport()` | Server: `/api/training/report/download` | Client: browser download |

**Data Display (implicit):**
- Training status: Read from Server `GET /api/training/status/{job_id}` (polling)

---

## TESTING PAGE (`pages/testing.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 34c | Button | "Test New File" | `setIsModalOpen(true)` | - | Client: modal state |
| 35c | Input | Search tests | `setSearchQuery()` | - | Client: filter state |
| 36c | Select | Model filter | `setModelFilter()` | Server: `GET /api/models` | Client: filter state |
| 37c | Select | Status filter | `setStatusFilter()` | - | Client: filter state |
| 38c | Select | Sort dropdown | `setSortBy()` | - | Client: sort state |
| 39c | Row | Test row (expand) | `onToggle()` | Server: `GET /api/tests/{id}` | Client: expand state |
| 40c | Button | "Download CSV" | `handleDownload()` | Server: `GET /api/tests/{id}/csv` | Client: browser download |
| 41c | Dropdown | "Actions" menu | Opens menu | - | Client: menu state |
| 42c | MenuItem | "View/Edit Notes" | `handleViewNotes()` | Server: `GET /api/tests/{id}` | Client: editor state |
| 43c | MenuItem | "Delete Test" | `onDelete()` | - | Server: `DELETE /api/tests/{id}` |
| 44c | Button | "Cancel" (notes) | Close editor | - | Client: editor state |
| 45c | Button | "Save Notes" | `handleSaveNotes()` | Client: notes input | Server: `PUT /api/tests/{id}/notes` |
| 46c | Tab | "Predictions" | Switch view | Server: test predictions | Client: tab state |
| 47c | Tab | "Raw Signal" | Switch view | Server: test raw data | Client: tab state |

**Data Display (implicit):**
- Tests list: Read from Server `GET /api/tests`

---

## REPORTS PAGE (`pages/reports.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 48c | Button | "Export All" | `handleExportAll()` | Server: `GET /api/reports/export-all` | Client: browser download (ZIP) |
| 49c | Input | Search reports | `setSearchQuery()` | - | Client: filter state |
| 50c | Select | Model filter | `setModelFilter()` | Server: `GET /api/models` | Client: filter state |
| 51c | Select | Sort dropdown | `setSortBy()` | - | Client: sort state |
| 52c | Row | Report row | `handleViewReport()` | Server: `/api/training/report/view` | Client: viewer modal |
| 53c | Button | Download icon | `handleDownload()` | Server: `/api/training/report/download` | Client: browser download |
| 54c | Dropdown | 3-dot menu | Opens menu | - | Client: menu state |
| 55c | MenuItem | "View Report" | Opens viewer | Server: report PDF | Client: modal state |
| 56c | MenuItem | "Download PDF" | Downloads | Server: report PDF | Client: browser download |
| 57c | MenuItem | "Open in New Tab" | `window.open()` | Server: report URL | Client: new browser tab |
| 58c | MenuItem | "Delete Report" | `handleDeleteClick()` | - | Client: confirm dialog |
| 59c | AlertDialog | "Delete" confirm | `confirmDelete()` | - | Server: `DELETE /api/reports/{id}` |

**Data Display (implicit):**
- Reports list: Read from Server `GET /api/reports`

---

## MODELS PAGE (`pages/models.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 60c | Input | Search models | `setSearchQuery()` | - | Client: filter state |
| 61c | Select | Sort dropdown | `setSortBy()` | - | Client: sort state |
| 62c | Card | Model card | Navigate | - | Client: router `/models/{id}` |
| 63c | Button | Trash icon | `handleDeleteClick()` | - | Client: confirm dialog |
| 64c | Button | "Weights" | `handleDownloadWeights()` | Server: `GET /api/models/{id}/weights` | Client: browser download (.h5) |
| 65c | AlertDialog | "Delete" confirm | `confirmDelete()` | - | Server: `DELETE /api/models/{id}` |

**Data Display (implicit):**
- Models list: Read from Server `GET /api/models`
- Model details: Read from Server `GET /api/models/{id}`

---

## RAW DATABASE PAGE (`pages/raw-database.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 66c | Input | Search folders | `setSearchQuery()` | - | Client: filter state |
| 67c | Select | Sort dropdown | `setSortBy()` | - | Client: sort state |
| 68c | Collapsible | Folder row | `toggleFolder()` | Server: `GET /api/raw-database/{id}` | Client: expand state |
| 69c | Button | "Download All" | Downloads ZIP | Server: `GET /api/raw-database/{id}/download` | Client: browser download |
| 70c | Button | Download (file) | Downloads file | Server: `GET /api/raw-database/{id}/files/{name}/download` | Client: browser download |

**Data Display (implicit):**
- Folders list: Read from Server `GET /api/raw-database`

---

## LAYOUT / NAVIGATION (`components/layout.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 71c | Link | "Database" | Navigate | - | Client: router `/` |
| 72c | Link | "Raw Files" | Navigate | - | Client: router `/raw` |
| 73c | Link | "Training" | Navigate | - | Client: router `/training` |
| 74c | Link | "Models" | Navigate | - | Client: router `/models` |
| 75c| Link | "Testing" | Navigate | - | Client: router `/testing` |
| 76c | Link | "Reports" | Navigate | - | Client: router `/reports` |
| 77c | Link | "Assistant" | Navigate | - | Client: router `/chat` |
| 78c | Button | "API Key" | `setApiKeyOpen(true)` | Server: `GET /api/settings/api-key` | Client: modal state |
| 79c | Button | "Settings" | `setSettingsOpen(true)` | - | Client: modal state |
| 80c | Button | Theme toggle | `setTheme()` | Client: localStorage | Client: localStorage + CSS |
| 81c | Button | Collapse | `setIsCollapsed()` | - | Client: sidebar state |
| 82c | Button | Hamburger | Opens mobile menu | - | Client: sheet state |
| 83c | Link | Mobile nav | Navigate + close | - | Client: router + sheet state |

---

## ADD DATA MODAL (`components/add-data-modal.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 84c | DialogTrigger | "Add Data" | Opens dialog | - | Client: modal state |
| 85c | Drop Zone | Drag/drop | `handleDrop()` | Client: user's computer | Client: file list state |
| 86c | Button | "Clear All" | `clearFiles()` | - | Client: file list state |
| 87c | Button | X (remove) | `removeFile()` | - | Client: file list state |
| 88c | Input | Folder name | Set name | - | Client: form state |
| 89c | Input | Label | Set label | - | Client: form state |
| 90c | Button | Wand (AI label) | `suggestLabelMutation.mutate()` | Server: `POST /api/suggest-label` | Client: label input |
| 91c | Button | "Cancel" | `setOpen(false)` | - | Client: modal state |
| 92c | Button | "Upload & Process" | `onSubmit()` | Client: files + form | Server: `POST /api/raw-database/upload` → `raw_database/` then `POST /api/ingest` → `database/{label}/` |

---

## TEST NEW FILE MODAL (`components/testing/TestNewFileModal.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 93c | Select | Model selector | `setSelectedModel()` | Server: `GET /api/models` | Client: form state |
| 94c | Drop Zone | Drag/drop | `handleDrop()` | Client: user's computer | Client: file list state |
| 95c | Button | X (remove) | `removeFile()` | - | Client: file list state |
| 96c | Button | "Generate Notes" | `handleGenerateNotes()` | Server: `POST /api/tests/{id}/generate-notes` | Client: notes textarea |
| 97c | Textarea | Test notes | `setNotes()` | - | Client: form state |
| 98c | Button | "Back" | `setStep(step-1)` | - | Client: wizard state |
| 99c | Button | "Continue" | `setStep(step+1)` | - | Client: wizard state |
| 100c | Button | "Upload & Run" | `uploadAndRunInference()` | Client: files + form | Server: `POST /api/tests/upload` → `test_uploads/` then `POST /api/tests/inference` → `test_database/{id}/` |
| 101c | Button | "Done" | `resetAndClose()` | - | Client: modal + form state |

---

## FOLDER SELECTOR (`components/training/FolderSelector.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 102c | DialogTrigger | "Choose Training Data" | Opens selector | Server: `GET /api/labels` | Client: modal state |
| 103c | Checkbox | Dataset checkbox | `toggleFolder()` | - | Client: selection state |
| 104c | Button | Info icon | `setExpandedFolder()` | Server: `GET /api/labels/{id}` | Client: metadata panel |
| 105c | Button | "Confirm Selection" | `confirmSelection()` | Client: selection | Client: parent form state |

---

## SETTINGS DIALOG (`components/settings-dialog.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 106c | Button | Download (report modal) | `handleDownload()` | Server: report PDF | Client: browser download |
| 107c | Button | Time windows | `setSelectedTimeWindow()` | - | Client: settings state |
| 108c | Button | Duration | `setSelectedDuration()` | - | Client: settings state |
| 109c | Button | Val split | `setSelectedSplit()` | - | Client: settings state |
| 110c | Button | "Reset to Defaults" | `handleResetToDefaults()` | - | Client: settings state |
| 111c | Button | "Cancel" | `onOpenChange(false)` | - | Client: modal state |
| 112c | Button | "Save Changes" | `handleSave()` | Client: settings | Client: localStorage |

---

## API KEY DIALOG (`components/api-key-dialog.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 113c | Input | API key | `setApiKey()` | - | Client: form state |
| 114c | Button | Eye (toggle) | `setShowKey()` | - | Client: visibility state |
| 115c | Button | "Cancel" | Close dialog | - | Client: modal state |
| 116c | Button | "Save API Key" | `handleSave()` | Client: API key input | Server: `POST /api/settings/api-key` → `backend/.env` |

---

## CLASSIFICATION CARD (`components/classification-card.tsx`)

| # | Element | Label | Action | Read From | Write To |
|---|---------|-------|--------|-----------|----------|
| 117c | Card | Dataset card | Navigate | - | Client: router `/database/{id}` |
| 118c | Button | Trash icon | `handleDelete()` | - | Client: confirm dialog |
| 119c | AlertDialog | "Delete" confirm | `confirmDelete()` | - | Server: `DELETE /api/labels/{id}` → removes `database/{label}/` |

---

## Data Flow Summary by Server Directory

### Uploads (Client → Server)

| Source | Endpoint | Server Directory |
|--------|----------|------------------|
| User's computer (CSV) | `POST /api/raw-database/upload` | `backend/raw_database/{folder}/` |
| User's computer (CSV) | `POST /api/tests/upload` | `backend/test_uploads/` |
| API key input | `POST /api/settings/api-key` | `backend/.env` |

### Processing (Server → Server)

| Trigger | Endpoint | Source → Destination |
|---------|----------|----------------------|
| "Upload & Process" | `POST /api/ingest` | `raw_database/{folder}/` → `database/{label}/` |
| "Start Training" | `POST /api/training/start` | `database/{labels}/` → `models/{id}/` |
| "Upload & Run Inference" | `POST /api/tests/inference` | `test_uploads/` + `models/{id}/` → `test_database/{id}/` |

### Downloads (Server → Client)

| Button | Endpoint | Server Source |
|--------|----------|---------------|
| Download label | `GET /api/labels/{id}/download` | `database/{label}/` → ZIP |
| Download raw folder | `GET /api/raw-database/{id}/download` | `raw_database/{folder}/` → ZIP |
| Download raw file | `GET /api/raw-database/{id}/files/{name}/download` | `raw_database/{folder}/{file}` |
| Download weights | `GET /api/models/{id}/weights` | `models/{id}/model.h5` |
| Download report | `GET /api/training/report/download` | `models/{id}/report.pdf` |
| Export all reports | `GET /api/reports/export-all` | All `models/*/report.pdf` → ZIP |
| Download test CSV | `GET /api/tests/{id}/csv` | `test_database/{id}/results.csv` |

### Read-Only Display (Server → UI)

| Page | Endpoint | Server Source |
|------|----------|---------------|
| Database | `GET /api/labels` | `database/*/metadata.json` |
| Raw Database | `GET /api/raw-database` | `raw_database/*/` |
| Models | `GET /api/models` | `models/*/` |
| Testing | `GET /api/tests` | `test_database/*/` |
| Reports | `GET /api/reports` | `models/*/report.pdf` |
| Chat | `GET /api/chat/sessions` | `chat_sessions/*.json` |

---

## Quick Reference: Button Categories

### File Upload Buttons (Client → Server)
- #16, #85, #94: Drop zones for CSV files
- #19, #92, #100: Upload & process buttons

### Download Buttons (Server → Client)
- #8, #10: Image artifact downloads
- #12, #13, #33, #53, #56, #106: PDF report downloads
- #40: Test CSV download
- #48: Export all reports (ZIP)
- #64: Model weights (.h5)
- #69, #70: Raw folder/file downloads

### Delete Buttons (Server modification)
- #2: Delete chat session
- #43: Delete test
- #59: Delete report
- #65: Delete model
- #119: Delete dataset/label

### Navigation (Client-only)
- #71-77, #83: Sidebar/mobile nav links
- #62, #117: Card click navigation

### Form Controls (Client state)
- #20, #35, #49, #60, #66: Search inputs
- #21, #38, #51, #61, #67: Sort dropdowns
- #36, #37, #50, #93: Filter selects

### AI Generation (Server → Client)
- #24: AI model name suggestion
- #90: AI label suggestion
- #96: AI test notes generation
