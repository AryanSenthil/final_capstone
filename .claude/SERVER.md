# Backend Server Architecture Guide

## Overview
FastAPI backend serving sensor data analysis, model training, and AI chat agent.

**Key Principle**: Server stores ALL data. Clients UPLOAD files from their computer TO the server, and DOWNLOAD results FROM the server back to their computer.

## Directory Structure

```
backend/
├── api.py                  # Main REST API (48 endpoints) - TOO LARGE TO READ
├── chat_api.py             # Chat/agent endpoints (7 endpoints)
├── settings/
│   └── constants.py        # OPENAI_MODEL = "gpt-5.1" (DO NOT use gpt-4o)
├── agent/
│   ├── damage_lab_agent.py # AI agent with tools
│   ├── chat_runner.py      # Agent execution
│   └── __init__.py         # Agent exports
├── database/               # Processed data (ready for training)
│   └── {label}/           # One folder per label
│       ├── chunk_*.csv    # Processed chunks
│       └── metadata.json  # Dataset metadata
├── raw_database/          # Uploaded raw data (unprocessed)
│   └── {folder}/          # User-uploaded folders
│       └── *.csv         # Raw CSV files
├── test_uploads/          # Test CSV files for inference
├── test_database/         # Inference results
└── models/                # Trained models
    └── {model_id}/        # One folder per model
        ├── model.h5       # Keras model
        ├── scaler.pkl     # Data scaler
        └── report.pdf     # Training report
```

## Data Flow Architecture

### UPLOADS (Client → Server)
Users upload files FROM their computer TO the server via:
1. **Raw Data**: Native file picker → `POST /api/raw-database/upload` → `raw_database/{folder}/`
2. **Test Files**: Native file picker → `POST /api/tests/upload` → `test_uploads/`

### PROCESSING (Server-side)
Server processes uploaded data:
1. **Ingestion**: `POST /api/ingest` → processes `raw_database/{folder}` → creates `database/{label}/`
2. **Training**: `POST /api/training/start` → trains on `database/{label}` → creates `models/{id}/`
3. **Inference**: `POST /api/tests/inference` → tests `test_uploads/file.csv` → creates `test_database/{id}/`

### DOWNLOADS (Server → Client)
Users download results FROM server TO their computer:
- Labels: `GET /api/labels/{label_id}/download`
- Raw folders: `GET /api/raw-database/{folder_id}/download`
- Model weights: `GET /api/models/{model_id}/weights`
- Reports: `GET /api/training/report/download`
- Test results: `GET /api/tests/{test_id}/csv`

## IMPORTANT: Do NOT Browse Server Filesystem

**REMOVED**: `/api/browse` endpoint (was allowing clients to browse server filesystem - SECURITY ISSUE)

**Agent Tool**: `list_available_data()` - Shows ONLY data already uploaded to server:
- `raw_database` - Folders in raw_database (pending processing)
- `processed_labels` - Labels in database (ready for training)
- `test_uploads` - CSV files uploaded for testing
- `models` - Trained models available

**Never**:
- ❌ Browse server directories from client
- ❌ Let users specify arbitrary server paths
- ❌ Expose server filesystem structure

**Always**:
- ✅ Users upload files from THEIR computer
- ✅ Server stores in designated folders
- ✅ Agent lists what's ALREADY uploaded

## API Endpoints Summary

See `API-ENDPOINTS.md` for complete endpoint documentation (api.py is too large to read).

### Key Endpoint Groups
1. **Labels/Datasets** (8 endpoints) - Processed data management
2. **Raw Database** (7 endpoints) - Raw upload management
3. **Training** (8 endpoints) - Model training
4. **Models** (9 endpoints) - Model management
5. **Reports** (5 endpoints) - Training reports
6. **Tests** (9 endpoints) - Inference/testing
7. **Chat** (7 endpoints) - AI agent chat

## OpenAI Configuration

**CRITICAL**: Always use the centralized model configuration:

```python
from settings.constants import OPENAI_MODEL

# OPENAI_MODEL = "gpt-5.1"
# DO NOT hardcode model names
# DO NOT use max_tokens parameter (gpt-5.1 doesn't support it)
```

**Wrong**:
```python
model = "gpt-4o"  # ❌ Wrong model
max_tokens = 1000  # ❌ Not supported by gpt-5.1
```

**Correct**:
```python
from settings.constants import OPENAI_MODEL
model = OPENAI_MODEL  # ✅ Uses gpt-5.1
# No max_tokens parameter
```

## Agent Architecture

### Agent System Prompt
Defined in `agent/damage_lab_agent.py` as `SYSTEM_INSTRUCTION`. The agent helps users:
- Manage sensor data (upload, process, delete)
- Train models for damage detection
- Run inference/testing
- Analyze results

### Available Tools (Agent Functions)

**Data Management**:
- `list_datasets()` - List processed labels
- `get_dataset_details(label)` - Get label info
- `list_available_data()` - Show uploaded data (replaced browse_directories)
- `suggest_label(folder_path)` - AI suggests label name
- `ingest_data(folder_path, label)` - Process raw data
- `delete_dataset(label)` - Delete processed label
- `generate_dataset_metadata(label)` - Generate metadata
- `list_raw_folders()` - List raw uploads

**Model Training**:
- `list_models()` - List trained models
- `get_model_details(model_id)` - Get model info
- `suggest_model_name(labels)` - AI suggests model name
- `start_training(labels, model_name, params)` - Train model
- `get_training_status(job_id)` - Check training progress
- `wait_for_training(job_id)` - Wait for completion
- `delete_model(model_id)` - Delete model

**Inference/Testing**:
- `run_inference(csv_path, model_id, notes, tags)` - Run test
- `list_tests()` - List inference results
- `get_test_details(test_id)` - Get test info
- `get_test_statistics(test_ids)` - Compare tests
- `delete_test(test_id)` - Delete test

**Analysis & Reports**:
- `get_workflow_guidance()` - Workflow help
- `compare_models(model_ids)` - Compare models
- `get_dataset_summary(label)` - Dataset stats
- `get_training_recommendations(labels)` - Training advice
- `explain_results(test_id)` - Explain predictions
- `get_model_graphs(model_id)` - Get training graphs
- `get_report_url(model_id)` - Get report URL
- `read_pdf(url)` - Read PDF report
- `read_report(model_id)` - Read model report
- `list_reports()` - List all reports
- `get_system_status()` - System health

### Tool Registration
Tools are registered in 3 places (must match):
1. `agent/damage_lab_agent.py` - `ALL_TOOLS` list
2. `agent/__init__.py` - Exports and `__all__`
3. `agent/chat_runner.py` - `TOOL_FUNCTIONS` dict
4. `chat_api.py` - `TOOL_FUNCTIONS` dict

## CORS Configuration

Located in `api.py:72-86`. Allowed origins:
```python
allow_origins=[
    "http://localhost:5000",      # Frontend dev
    "http://localhost:5001",
    "http://localhost:5173",      # Vite dev
    "http://127.0.0.1:5000",
    "http://34.204.204.26:5000",  # EC2 production
    "http://34.204.204.26",
]
```

**When deploying**: Add your production domain/IP to this list.

## Database Storage

### File-Based Storage (CSV)
- **NOT PostgreSQL** - Uses CSV files for simplicity
- Processed data: `database/{label}/chunk_*.csv`
- Raw data: `raw_database/{folder}/*.csv`
- Metadata: `database/{label}/metadata.json`

### User Auth (Frontend)
- Frontend uses Drizzle + MemStorage for user sessions
- Backend doesn't handle user auth (all endpoints public for now)

## Development Server

### Quick Start (Recommended)
```bash
./dev.sh  # Starts both backend and frontend
```

### Manual Start
```bash
# Backend - MUST use venv
cd /home/ari/Documents/final_capstone/backend
.venv/bin/uvicorn api:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd /home/ari/Documents/final_capstone/frontend
npm run dev  # Runs on port 5000
```

**CRITICAL**:
- Backend MUST use `.venv/bin/uvicorn` (not system uvicorn)
- Backend runs on port 8000
- Frontend runs on port 5000 and proxies `/api/*` to backend

## Common Issues & Debugging

### API requests returning HTML instead of JSON
**Cause**: Vite proxy not forwarding to backend

**Check**:
1. Backend running? `curl http://localhost:8000/api/labels`
2. Frontend proxy config in `frontend/server/vite.ts`:
   ```typescript
   const serverOptions = {
     ...viteConfig.server,  // Must spread to preserve proxy
     middlewareMode: true,
     hmr: { server, path: "/vite-hmr" },
   };
   ```

### Module import errors
**Fix**: Run from correct directory with venv:
```bash
cd /home/ari/Documents/final_capstone/backend
.venv/bin/python -m your_module
```

### Agent tool not found
**Check**:
1. Tool defined in `agent/damage_lab_agent.py`
2. Added to `ALL_TOOLS` list
3. Exported in `agent/__init__.py`
4. Registered in `chat_runner.py` and `chat_api.py`

## Testing

```bash
# Backend tests
cd backend
.venv/bin/pytest

# Check agent imports
.venv/bin/python -c "from agent import list_available_data; print('OK')"

# Test API endpoint
curl http://localhost:8000/api/labels
```

## Security Notes

1. **No server filesystem browsing** - Removed `/api/browse`
2. **Upload validation** - Only accept CSV files
3. **Path traversal protection** - Validate all file paths
4. **CORS** - Only allow specific origins
5. **No auth yet** - All endpoints public (add auth before production)

## When Adding New Features

### Adding a New Endpoint
1. Define Pydantic models for request/response
2. Add route decorator and function in `api.py` or `chat_api.py`
3. Update `API-ENDPOINTS.md` documentation
4. Test with curl or Postman

### Adding a New Agent Tool
1. Define function in `agent/damage_lab_agent.py` with docstring
2. Add to `ALL_TOOLS` list in same file
3. Export in `agent/__init__.py` (import and `__all__`)
4. Register in `agent/chat_runner.py` `TOOL_FUNCTIONS`
5. Register in `chat_api.py` `TOOL_FUNCTIONS`
6. Test agent can call it via chat

### Modifying Data Flow
1. Update directory structure diagram above
2. Update `SERVER.md` and `CLIENT.md`
3. Test upload → process → download cycle
4. Update frontend components if needed
