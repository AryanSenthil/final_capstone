# Claude AI Context - Sensor Data Management System

## Project Overview
A full-stack application for managing and visualizing sensor data with features for data import, processing, visualization, and download capabilities.

## Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **Port**: 5000
- **Location**: `/home/ari/Documents/final_capstone/backend`
- **Main file**: `api.py`
- **Virtual env**: `.venv` (Python 3.10)

### Frontend
- **Framework**: React + TypeScript with Vite
- **Port**: 5173
- **Location**: `/home/ari/Documents/final_capstone/frontend`
- **UI Library**: Tailwind CSS + shadcn/ui components
- **Charts**: Recharts
- **Routing**: Wouter
- **Data fetching**: TanStack Query (React Query)

## Key Features

### 1. Database View (`/database` - Main page)
- Lists all labeled datasets (processed sensor data)
- Shows metadata: label, chunks count, measurement type, duration
- Click on dataset to view details

### 2. Label Detail View (`/database/:id`)
- **Left sidebar**: File list with individual download buttons
- **Right panel**:
  - Dataset metadata card
  - Time-series chart visualization
- **Download features**:
  - Individual file download (per CSV)
  - Download All button (downloads as ZIP)

### 3. Raw Database View (`/raw-database`)
- Shows imported raw data organized by folders
- Collapsible folder view with file lists
- **Download features**:
  - Individual file download buttons
  - Download All per folder (ZIP)

### 4. Add Data Modal
- Upload CSV files
- Configure processing parameters
- Triggers backend data processing

## API Endpoints

### Labels (Processed Data)
- `GET /api/labels` - List all labeled datasets
- `GET /api/labels/:id` - Get dataset details
- `GET /api/labels/:id/files` - List files in dataset
- `GET /api/labels/:id/files/:filename` - Get file data for chart
- `GET /api/labels/:id/files/:filename/download` - Download single file
- `GET /api/labels/:id/download` - Download all files as ZIP

### Raw Database
- `GET /api/raw-database` - List all raw folders
- `GET /api/raw-database/:folder_id` - Get folder details
- `GET /api/raw-database/:folder_id/files/:filename/download` - Download single file
- `GET /api/raw-database/:folder_id/download` - Download all files in folder as ZIP

## Directory Structure

```
/home/ari/Documents/final_capstone/
├── backend/
│   ├── api.py              # Main FastAPI application
│   ├── database.py         # Database management
│   ├── requirements.txt    # Python dependencies
│   └── .venv/             # Virtual environment
├── frontend/
│   ├── client/
│   │   └── src/
│   │       ├── pages/
│   │       │   ├── database.tsx           # Main database view
│   │       │   ├── label-detail.tsx       # Dataset detail view
│   │       │   └── raw-database.tsx       # Raw data view
│   │       └── components/
│   │           ├── line-chart.tsx         # Chart component
│   │           └── add-data-modal.tsx     # Upload modal
│   └── vite.config.ts     # Vite config (proxy to backend)
└── data/
    ├── labels/            # Processed labeled data
    └── raw_database/      # Raw imported data
```

## Recent Changes (This Session)

### Download Functionality
- Fixed broken individual download buttons in raw-database page
- Added backend endpoint for individual raw file downloads
- Changed download behavior from opening new tab to same-tab download using anchor elements
- Added loading states and visual feedback to all download buttons

### Button Interactivity
- Added hover effects to all download buttons:
  - Scale animation on hover
  - Shadow effects
  - Primary color highlight
  - Active state (press-in effect)
- Individual file buttons: appear on row hover, scale up on hover
- Download All buttons: full-width interactive buttons with prominent hover states

### Chart Improvements
- Increased chart height: 450px → 550px (card), 380px → 480px (chart)
- Added dark mode support with theme detection
- Made axis text bold for better readability
- Thicker line stroke: 1.5px → 2.5px
- Theme-aware colors:
  - **Light mode**: White background, light grey padding areas
  - **Dark mode**: Black background, grey padding areas
- Real-time theme switching with MutationObserver

### Configuration
- Updated Vite proxy to point to backend on port 5000 (was 8000)

## Running the Application

### Start Backend
```bash
cd /home/ari/Documents/final_capstone/backend
source .venv/bin/activate
uvicorn api:app --host 0.0.0.0 --port 5000 --reload
```

### Start Frontend
```bash
cd /home/ari/Documents/final_capstone/frontend
npm run dev:client -- --port 5173
```

### Access
- Frontend: http://localhost:5173
- Backend API: http://localhost:5000

## Current State

### Working Features ✅
- All download buttons functional (individual + Download All)
- Interactive hover effects on all buttons
- Theme-aware chart visualization
- Real-time data visualization
- File management and organization

### Known Configuration
- Backend runs on port 5000
- Frontend runs on port 5173
- Vite proxy forwards `/api/*` requests to `http://localhost:5000`

## Next Steps / TODO
- Test download functionality with actual data
- Consider adding progress indicators for large downloads
- Potential improvements:
  - Batch download selection
  - Search/filter capabilities
  - More chart customization options
