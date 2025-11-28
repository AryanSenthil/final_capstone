# Claude AI Context - Sensor Data Management System

## Project Overview
A full-stack application for managing and visualizing sensor data with features for data import, processing, visualization, and download capabilities.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Port**: 8000
- **Location**: `backend/`
- **Main file**: `api.py`
- **Virtual env**: `.venv` (managed with `uv`)

### Frontend
- **Framework**: React + TypeScript with Vite
- **Port**: 5000 (or 5001 if 5000 is in use)
- **Location**: `frontend/`
- **UI Library**: Tailwind CSS + shadcn/ui components
- **Charts**: Recharts
- **Routing**: Wouter
- **Data fetching**: TanStack Query (React Query)

## CRITICAL: Files That Must Be Tracked in Git

The following files are essential and MUST be committed:

### Frontend
- `frontend/client/src/lib/queryClient.ts` - **Contains URL building logic for API calls**
- `frontend/client/src/lib/utils.ts` - Utility functions
- `frontend/vite.config.ts` - Vite config with proxy settings

### Backend
- `backend/requirements.txt` - Must include: fastapi, uvicorn, pandas, numpy, scipy, pydantic, pydantic-settings, python-dotenv, openai

## Quick Start

### 1. Backend Setup
```bash
cd backend
uv venv .venv
uv pip install -r requirements.txt
.venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev:client
```

### Access
- **Frontend**: http://localhost:5000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Architecture

### API URL Building (IMPORTANT)
The frontend uses TanStack Query with a custom `defaultQueryFn` in `queryClient.ts` that builds URLs from queryKey arrays:
- `["/api/labels"]` → `/api/labels`
- `["/api/labels", "myLabel"]` → `/api/labels/myLabel`
- `["/api/browse", "?path=/home"]` → `/api/browse?path=/home`

Query strings (starting with `?`) are appended directly, path segments get `/` prefix.

### Vite Proxy
Frontend proxies `/api/*` requests to `http://localhost:8000` (configured in `vite.config.ts`)

### CORS
Backend allows origins: localhost:5000, localhost:5001, localhost:5173

## Directory Structure

```
├── backend/
│   ├── api.py                    # FastAPI application
│   ├── requirements.txt          # Python dependencies
│   ├── database_management/      # Data ingestion module
│   │   ├── ingest_sensor_data.py # CSV processing pipeline
│   │   └── delete_dataset.py     # Dataset deletion
│   ├── settings/
│   │   ├── constants.py          # Paths, file patterns
│   │   └── configs.py            # Processing parameters
│   ├── database/                 # Processed data storage
│   └── raw_database/             # Raw data backup
├── frontend/
│   ├── client/src/
│   │   ├── lib/
│   │   │   ├── queryClient.ts    # API client config (CRITICAL)
│   │   │   └── utils.ts
│   │   ├── pages/
│   │   │   ├── database.tsx      # Main view
│   │   │   ├── label-detail.tsx  # Dataset detail
│   │   │   └── raw-database.tsx  # Raw data view
│   │   └── components/
│   │       └── add-data-modal.tsx # Import dialog
│   └── vite.config.ts            # Proxy config
└── claude.md                     # This file
```

## API Endpoints

### Labels (Processed Data)
- `GET /api/labels` - List all datasets
- `GET /api/labels/{id}` - Get dataset metadata
- `GET /api/labels/{id}/files` - List files in dataset
- `GET /api/labels/{id}/files/{filename}` - Get file data for chart
- `GET /api/labels/{id}/files/{filename}/download` - Download single CSV
- `GET /api/labels/{id}/download` - Download all as ZIP
- `DELETE /api/labels/{id}` - Delete dataset

### Raw Database
- `GET /api/raw-database` - List all raw folders
- `GET /api/raw-database/{folder_id}` - Get folder details
- `GET /api/raw-database/{folder_id}/download` - Download folder as ZIP
- `GET /api/raw-database/{folder_id}/files/{filename}/download` - Download single file

### Data Ingestion
- `GET /api/browse?path=...` - Browse filesystem for folder selection
- `POST /api/ingest` - Start data processing
- `POST /api/suggest-label` - AI-generated label suggestion

## Common Issues & Fixes

### "Failed to load datasets" or 404 errors
**Cause**: queryClient.ts not properly building URLs
**Fix**: Ensure `queryClient.ts` joins queryKey parts with `/` for path segments

### "ModuleNotFoundError: No module named 'scipy'"
**Cause**: Missing dependency in requirements.txt
**Fix**: `uv pip install scipy numpy`

### Frontend can't connect to backend
**Cause**: CORS or proxy misconfiguration
**Fix**:
1. Check backend CORS includes frontend port
2. Check vite.config.ts proxy target is correct
3. Ensure both servers are running

## Data Processing Pipeline

1. User selects folder via `/api/browse`
2. POST to `/api/ingest` with folder path and label
3. Backend copies raw files to `raw_database/{folder_name}/`
4. Processes CSVs: interpolation, chunking, padding
5. Saves to `database/{label}/` with metadata.json
