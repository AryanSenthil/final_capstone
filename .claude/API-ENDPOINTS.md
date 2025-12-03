# API Endpoints Reference

**File**: `backend/api.py` (2813 lines - too large to read directly)

This document provides a complete reference for all REST API endpoints. Use this instead of reading `api.py` directly.

## Endpoint Summary

**Total**: 48 endpoints across 7 categories

| Category | Endpoints | Description |
|----------|-----------|-------------|
| Health | 1 | API status check |
| Labels/Datasets | 10 | Processed data management |
| Raw Database | 5 | Upload management |
| Ingestion | 3 | Data processing |
| Training | 8 | Model training |
| Models | 9 | Model management |
| Reports | 5 | Training reports |
| Tests | 10 | Inference/testing |

---

## Health Check

### `GET /`
**Description**: API health check
**Response**: `{ "status": "ok", "message": "Damage Lab API is running" }`

---

## Labels / Datasets (Processed Data)

Processed data ready for training, located in `backend/database/{label}/`

### `GET /api/labels`
**Description**: Get all processed datasets/labels
**Response**: `list[Dataset]`
**Example**:
```json
[
  {
    "id": "damaged",
    "label": "damaged",
    "chunks": 150,
    "measurement": "Acceleration",
    "unit": "g",
    "lastUpdated": "2025-01-15T10:30:00Z",
    ...
  }
]
```

### `GET /api/labels/{label_id}`
**Description**: Get metadata for specific label
**Response**: `Dataset`
**Errors**: 404 if label not found

### `DELETE /api/labels/{label_id}`
**Description**: Delete processed label
**Query Params**:
- `delete_raw: bool = true` - Also delete source raw folder

**Response**: `{ "success": true, "message": "..." }`
**Errors**: 404 if label not found

### `POST /api/labels/{label_id}/generate-metadata`
**Description**: Generate/regenerate metadata for label
**Response**: `{ "success": true, "metadata": {...} }`
**Errors**: 404 if label not found

### `POST /api/labels/generate-all-metadata`
**Description**: Batch generate metadata for all labels
**Query Params**:
- `force: bool = false` - Regenerate even if exists

**Response**: `{ "success": true, "generated": [...], "skipped": [...], "errors": [...] }`

### `GET /api/labels/{label_id}/files`
**Description**: List all chunk files for label
**Response**: `list[FileInfo]`
**Example**:
```json
[
  {
    "name": "chunk_0.csv",
    "size": 1024000,
    "modified": "2025-01-15T10:30:00Z"
  }
]
```

### `GET /api/labels/{label_id}/files/{filename}`
**Description**: Get chunk file data as JSON
**Response**: `{ "data": [[...]], "columns": [...], "shape": [rows, cols] }`

### `GET /api/labels/{label_id}/files/{filename}/download`
**Description**: Download specific chunk file
**Response**: CSV file download

### `GET /api/labels/{label_id}/download`
**Description**: Download entire label as ZIP
**Response**: ZIP file containing all chunks + metadata
**Filename**: `{label_id}.zip`

---

## Raw Database (Uploaded Data)

Raw uploaded data pending processing, located in `backend/raw_database/{folder}/`

### `GET /api/raw-database`
**Description**: List all raw folders
**Response**: `list[RawFolder]`
**Example**:
```json
[
  {
    "id": "upload_2025-01-15_10-30-00",
    "name": "upload_2025-01-15_10-30-00",
    "files": ["data1.csv", "data2.csv"],
    "file_count": 2,
    "total_size": 2048000,
    "created": "2025-01-15T10:30:00Z"
  }
]
```

### `POST /api/raw-database/upload`
**Description**: Upload raw CSV files from client
**Body**: `FormData` with:
- `files: File[]` - Multiple CSV files
- `folder_name?: string` - Optional folder name (auto-generated if omitted)

**Response**: `{ "success": true, "folder_path": "...", "files": [...] }`
**Errors**: 400 if no files or invalid format

**Example**:
```typescript
const formData = new FormData();
formData.append('files', file1);
formData.append('files', file2);
formData.append('folder_name', 'my-data');
await fetch('/api/raw-database/upload', {
  method: 'POST',
  body: formData,
});
```

### `GET /api/raw-database/{folder_id}`
**Description**: Get raw folder details
**Response**: `RawFolder`
**Errors**: 404 if folder not found

### `GET /api/raw-database/{folder_id}/download`
**Description**: Download entire raw folder as ZIP
**Response**: ZIP file with all CSVs
**Filename**: `{folder_id}.zip`

### `GET /api/raw-database/{folder_id}/files/{filename}/download`
**Description**: Download specific file from raw folder
**Response**: CSV file download

---

## Data Ingestion / Processing

Process raw data into labeled chunks ready for training.

### `POST /api/ingest`
**Description**: Process raw folder into labeled dataset
**Body**:
```json
{
  "folderPath": "/path/to/raw_database/folder",
  "classificationLabel": "damaged"
}
```
**Response**: `{ "success": true, "message": "..." }`
**Process**:
1. Reads all CSVs from raw folder
2. Chunks data (1000 samples per chunk)
3. Saves to `database/{label}/chunk_*.csv`
4. Generates metadata

**Errors**: 400 if folder not found or invalid

### `POST /api/suggest-label`
**Description**: AI suggests label name from folder path
**Body**: `{ "folder_path": "/path/to/folder" }`
**Response**: `{ "success": true, "suggested_label": "damaged_0.75" }`
**Uses**: OpenAI GPT-5.1 to clean folder names

### `POST /api/suggest-model-name`
**Description**: AI suggests model name from selected labels
**Body**: `{ "labels": ["damaged", "healthy", "baseline"] }`
**Response**: `{ "success": true, "suggested_name": "3class_damage_detector" }`

---

## Training

Train neural network models on processed labels.

### `GET /api/training/state`
**Description**: Get current training state (if any)
**Response**: `TrainingState` or 404 if no training
**State stored**: `backend/training_state.json`

### `POST /api/training/state`
**Description**: Save/update training state
**Body**: `TrainingState`
**Use**: Internal - updates during training

### `DELETE /api/training/state`
**Description**: Clear training state
**Use**: Called when training completes/fails

### `POST /api/training/start`
**Description**: Start training a new model
**Body**:
```json
{
  "labels": ["damaged", "healthy"],
  "model_name": "2class_detector",
  "epochs": 50,
  "batch_size": 32,
  "validation_split": 0.2,
  "learning_rate": 0.001,
  "patience": 10,
  "hidden_layers": [128, 64],
  "dropout": 0.3
}
```
**Response**: `{ "success": true, "job_id": "uuid", "model_id": "2class_detector" }`
**Process**:
1. Validates labels exist
2. Starts background training job
3. Returns immediately (async)
4. Poll `/api/training/status/{job_id}` for progress

**Errors**: 400 if labels not found or invalid params

### `GET /api/training/status/{job_id}`
**Description**: Get training job status
**Response**:
```json
{
  "job_id": "uuid",
  "status": "training",  // queued, training, completed, failed
  "progress": 0.45,      // 0.0 to 1.0
  "current_epoch": 23,
  "total_epochs": 50,
  "message": "Training in progress...",
  "model_id": "2class_detector"
}
```
**Poll**: Every 2-5 seconds while status is "training"

### `POST /api/training/stop/{job_id}`
**Description**: Stop training job
**Response**: `{ "success": true, "message": "Training stopped" }`
**Note**: May take a moment to stop cleanly

---

## Models

Trained models located in `backend/models/{model_id}/`

### `GET /api/models`
**Description**: List all trained models
**Response**: `list[ModelInfo]`
**Example**:
```json
[
  {
    "id": "2class_detector",
    "name": "2class_detector",
    "labels": ["damaged", "healthy"],
    "accuracy": 0.94,
    "created": "2025-01-15T10:30:00Z",
    "epochs": 50,
    "validation_accuracy": 0.92
  }
]
```

### `GET /api/models/{model_id}`
**Description**: Get model details
**Response**: `ModelInfo` with full metadata
**Errors**: 404 if model not found

### `GET /api/models/{model_id}/graphs`
**Description**: Get training graphs (accuracy, loss)
**Response**:
```json
{
  "accuracy": "data:image/png;base64,...",
  "loss": "data:image/png;base64,...",
  "confusion_matrix": "data:image/png;base64,..."
}
```
**Format**: Base64-encoded PNG images

### `GET /api/models/{model_id}/history`
**Description**: Get training history data
**Response**:
```json
{
  "history": {
    "accuracy": [0.5, 0.7, 0.85, 0.94],
    "val_accuracy": [0.48, 0.68, 0.82, 0.92],
    "loss": [0.693, 0.4, 0.2, 0.1],
    "val_loss": [0.71, 0.42, 0.22, 0.12]
  },
  "epochs": 50
}
```

### `GET /api/models/{model_id}/dependencies`
**Description**: Check if model is used by any tests
**Response**: `{ "tests": [...], "can_delete": true/false }`

### `DELETE /api/models/{model_id}`
**Description**: Delete model and all files
**Query Params**:
- `force: bool = false` - Delete even if tests depend on it

**Response**: `{ "success": true, "message": "..." }`
**Deletes**: Model files, report, graphs

### `GET /api/models/{model_id}/weights`
**Description**: Download model weights file
**Response**: HDF5 file download
**Filename**: `{model_id}_weights.h5`

---

## Reports

Training reports (PDFs with results, graphs, metrics)

### `GET /api/reports`
**Description**: List all training reports
**Response**: `list[ReportInfo]`
**Example**:
```json
[
  {
    "id": "2class_detector",
    "model_id": "2class_detector",
    "filename": "training_report_2class_detector.pdf",
    "created": "2025-01-15T10:30:00Z",
    "size": 524288
  }
]
```

### `GET /api/reports/{model_id}/{filename}`
**Description**: Get specific report file
**Use**: Internal - serves report files

### `GET /api/training/report/view`
**Description**: View report in browser (iframe)
**Query Params**:
- `model_id: str` - Model ID

**Response**: PDF with `Content-Disposition: inline`
**Example**: `<iframe src="/api/training/report/view?model_id=2class_detector" />`

### `GET /api/training/report/download`
**Description**: Download report file
**Query Params**:
- `model_id: str` - Model ID

**Response**: PDF with `Content-Disposition: attachment`

### `DELETE /api/reports/{report_id}`
**Description**: Delete report file
**Response**: `{ "success": true }`

### `GET /api/reports/export-all`
**Description**: Download all reports as ZIP
**Response**: ZIP file with all PDFs
**Filename**: `training_reports.zip`

---

## Tests / Inference

Run inference on test files with trained models.

### `POST /api/tests/upload`
**Description**: Upload test CSV file from client
**Body**: `FormData` with:
- `file: File` - Single CSV file

**Response**: `{ "success": true, "file_path": "..." }`
**Saves to**: `backend/test_uploads/{filename}`
**Errors**: 400 if not CSV or too large

### `POST /api/tests/inference`
**Description**: Run inference on uploaded test file
**Body**:
```json
{
  "csv_path": "/path/to/test_uploads/file.csv",
  "model_id": "2class_detector",
  "notes": "Testing damaged sample",
  "tags": ["batch1", "field-test"],
  "log_to_database": true
}
```
**Response**:
```json
{
  "success": true,
  "test_id": "uuid",
  "majority_class": "damaged",
  "class_distribution": {"damaged": 0.85, "healthy": 0.15},
  "probabilities": [[0.9, 0.1], [0.8, 0.2], ...],
  "num_chunks": 10,
  "csv_file": "results.csv"
}
```
**Process**:
1. Chunks test file (1000 samples per chunk)
2. Runs model inference on each chunk
3. Aggregates predictions
4. Saves results to `test_database/{test_id}/`

### `GET /api/tests`
**Description**: List all test results
**Response**: `list[TestSummary]`
**Example**:
```json
[
  {
    "id": "uuid",
    "filename": "test_sample.csv",
    "model_id": "2class_detector",
    "prediction": "damaged",
    "confidence": 0.85,
    "chunks": 10,
    "created": "2025-01-15T10:30:00Z",
    "notes": "Testing damaged sample",
    "tags": ["batch1"]
  }
]
```

### `GET /api/tests/stats`
**Description**: Get aggregate test statistics
**Response**:
```json
{
  "total_tests": 42,
  "by_model": {
    "2class_detector": 30,
    "3class_detector": 12
  },
  "by_prediction": {
    "damaged": 25,
    "healthy": 17
  },
  "avg_confidence": 0.87
}
```

### `GET /api/tests/{test_id}`
**Description**: Get test details
**Response**: `TestDetail` with full metadata
**Errors**: 404 if test not found

### `GET /api/tests/{test_id}/csv`
**Description**: Get test results as CSV data
**Response**: JSON with:
```json
{
  "data": [[...]],
  "columns": ["prediction", "confidence", ...],
  "summary": { "majority_class": "damaged", ... }
}
```

### `GET /api/tests/{test_id}/chunk/{chunk_idx}`
**Description**: Get specific chunk predictions
**Response**: Chunk data with predictions

### `GET /api/tests/{test_id}/raw-data`
**Description**: Download original test CSV file
**Response**: CSV file download

### `DELETE /api/tests/{test_id}`
**Description**: Delete test result
**Response**: `{ "success": true, "message": "..." }`
**Deletes**: Test directory with all files

### `PUT /api/tests/{test_id}/notes`
**Description**: Update test notes
**Body**: `{ "notes": "Updated notes text" }`
**Response**: `{ "success": true, "notes": "..." }`

### `POST /api/tests/{test_id}/generate-notes`
**Description**: AI generate notes for test
**Response**: `{ "success": true, "notes": "..." }`
**Uses**: OpenAI GPT-5.1 to generate professional notes

---

## Response Models (Pydantic)

Common response types:

```python
class Dataset(BaseModel):
    id: str
    label: str
    chunks: int
    measurement: str
    unit: str
    lastUpdated: str
    # ... more fields

class RawFolder(BaseModel):
    id: str
    name: str
    files: list[str]
    file_count: int
    total_size: int
    created: str

class ModelInfo(BaseModel):
    id: str
    name: str
    labels: list[str]
    accuracy: float
    created: str
    epochs: int
    # ... more fields

class TestSummary(BaseModel):
    id: str
    filename: str
    model_id: str
    prediction: str
    confidence: float
    chunks: int
    created: str
    notes: Optional[str]
    tags: list[str]

class TrainingState(BaseModel):
    job_id: str
    model_id: str
    status: str  # queued, training, completed, failed
    progress: float  # 0.0 to 1.0
    current_epoch: int
    total_epochs: int
    message: str
```

---

## Error Responses

All endpoints return standard error format:

```json
{
  "detail": "Error message here"
}
```

**Common Status Codes**:
- `200` - Success
- `400` - Bad request (invalid input)
- `404` - Not found
- `500` - Server error

---

## CORS Configuration

Located in `api.py:72-86`:

```python
allow_origins=[
    "http://localhost:5000",
    "http://localhost:5001",
    "http://localhost:5173",
    "http://127.0.0.1:5000",
    "http://34.204.204.26:5000",  # EC2
    "http://34.204.204.26",
]
```

Add your domain before deploying.

---

## File Upload Guidelines

**Accepted**:
- CSV files only
- Multiple files per upload
- Max size: Check server config

**Endpoints**:
- `/api/raw-database/upload` - Training data
- `/api/tests/upload` - Test data

**Format**:
```typescript
const formData = new FormData();
formData.append('files', file1);  // Multiple files
formData.append('files', file2);
await fetch('/api/raw-database/upload', {
  method: 'POST',
  body: formData,  // NO Content-Type header
});
```

---

## Quick Reference

**Upload Flow**:
1. Upload files → `/api/raw-database/upload`
2. Process → `/api/ingest`
3. Train → `/api/training/start`
4. Test → `/api/tests/upload` + `/api/tests/inference`

**Download Flow**:
- Labels → `/api/labels/{id}/download`
- Models → `/api/models/{id}/weights`
- Reports → `/api/training/report/download?model_id={id}`
- Tests → `/api/tests/{id}/raw-data`

**Common Patterns**:
```bash
# List all data
GET /api/labels
GET /api/raw-database
GET /api/models
GET /api/tests

# Get details
GET /api/labels/{id}
GET /api/models/{id}
GET /api/tests/{id}

# Delete
DELETE /api/labels/{id}
DELETE /api/models/{id}
DELETE /api/tests/{id}
```
