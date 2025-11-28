# Changelog

All notable changes to the Sensor Data Management System.

## [2025-01-28] - Download Improvements & UI Enhancements

### Added

#### Backend
- **New API Endpoint**: `GET /api/raw-database/{folder_id}/files/{filename}/download`
  - Enables individual file downloads from raw database folders
  - Returns single CSV file with proper headers
  - Location: `backend/api.py:440-457`

#### Frontend - Download Functionality
- **Individual file download buttons** in raw-database page
  - Previously non-functional (missing onClick handler)
  - Now triggers download via new backend endpoint
  - Location: `frontend/client/src/pages/raw-database.tsx:188-213`

- **Loading states for all download buttons**
  - Individual file buttons show spinner during download
  - Download All buttons show "Downloading..." text with spinner
  - Auto-reset after 1.5-2 seconds
  - Buttons disabled during download to prevent duplicate clicks

- **Download state management**
  - Added `downloadingFiles` state tracking per file
  - Added `downloadingFolders` state tracking per folder
  - Added `downloadingAll` state for label detail page

#### Frontend - Button Interactivity
- **Hover effects on all download buttons**
  - Scale animation: `hover:scale-110` for icon buttons, `hover:scale-[1.02]` for full-width buttons
  - Shadow effects: `hover:shadow-md` and `hover:shadow-lg`
  - Color change: `hover:bg-primary` with `hover:text-primary-foreground`
  - Active state: `active:scale-95` (press-in effect)
  - Smooth transitions: `duration-200`

- **Individual download button improvements**
  - Appears on row hover (opacity transition)
  - Stays visible during download with highlighted background
  - Consistent styling across raw-database and label-detail pages

- **Download All button improvements**
  - Prominent hover states with background color change
  - Border color change on hover
  - Full-width buttons with gap spacing for icon + text

#### Chart Enhancements
- **Increased chart size**
  - Card container: `min-h-[450px]` → `min-h-[550px]`
  - Chart height prop: `380px` → `480px`
  - Location: `frontend/client/src/pages/label-detail.tsx:280,302`

- **Dark mode support**
  - Added theme detection using `MutationObserver`
  - Real-time theme switching without page reload
  - Theme-specific color schemes
  - Location: `frontend/client/src/components/line-chart.tsx`

- **Theme-aware styling**
  - **Light mode**:
    - White background (`bg-white`)
    - Light grey padding areas (`#f3f4f6`)
    - Dark text and labels (`#374151`)
    - Blue line (`#1e40af`)
  - **Dark mode**:
    - Black background (`bg-black`)
    - Grey padding areas (`#4b5563`)
    - Light text and labels (`#e5e7eb`, `#d1d5db`)
    - Light blue line (`#60a5fa`)

- **Improved readability**
  - Bold axis labels and tick values
  - Thicker line stroke: `1.5px` → `2.5px`
  - Thicker axis lines: `strokeWidth={1.5}`
  - Larger active dot: `r: 4` → `r: 5`

### Changed

#### Backend Configuration
- No breaking changes to existing endpoints
- Added new endpoint maintains backward compatibility

#### Frontend - Download Behavior
- **Changed from new tab to same-tab downloads**
  - Before: Used `window.open(url, '_blank')`
  - After: Uses hidden anchor element with `download` attribute
  - Prevents opening new Chrome tabs
  - Downloads directly to user's download folder
  - Location: Both `raw-database.tsx` and `label-detail.tsx`

#### Frontend - Vite Configuration
- **Updated API proxy target**
  - Before: `http://localhost:8000`
  - After: `http://localhost:5000`
  - Matches actual backend port
  - Location: `frontend/vite.config.ts:56`

### Fixed

#### Critical Fixes
- **Individual download buttons in raw-database page**
  - Issue: Buttons rendered but had no onClick handler
  - Fix: Added `handleDownloadFile` function with proper state management
  - Files: `frontend/client/src/pages/raw-database.tsx`

- **Missing backend endpoint**
  - Issue: Frontend was calling `/api/raw-database/{folder_id}/files/{filename}/download` but endpoint didn't exist
  - Fix: Created new endpoint in `backend/api.py`
  - Returns file with proper Content-Disposition headers

#### UI/UX Fixes
- **Download button visibility**
  - Individual buttons now properly show/hide on row hover
  - Loading state keeps button visible during download
  - Consistent opacity transitions

- **Theme consistency**
  - Chart now matches overall application theme
  - Proper contrast in both light and dark modes
  - Text remains readable in both themes

### Technical Details

#### File Changes Summary
- **Backend**:
  - `backend/api.py`: Added new download endpoint
  - `backend/requirements.txt`: Updated with `pip freeze`

- **Frontend**:
  - `frontend/client/src/pages/raw-database.tsx`: Fixed download buttons, added interactivity
  - `frontend/client/src/pages/label-detail.tsx`: Added download states, hover effects
  - `frontend/client/src/components/line-chart.tsx`: Complete theme overhaul
  - `frontend/vite.config.ts`: Updated proxy configuration

#### State Management
- Added React state for tracking download progress per file/folder
- Implemented timeout-based state reset for user feedback
- Used `useState` hooks for `downloadingFiles`, `downloadingFolders`, `downloadingAll`

#### Performance Considerations
- Download state auto-resets after short delay (1.5-2s)
- Chart uses `MutationObserver` for efficient theme detection
- Transitions use CSS for hardware acceleration

### Documentation
- Created `claude.md`: Full project context and architecture
- Created `CHANGELOG.md`: This file
- Updated `requirements.txt`: Latest Python dependencies

---

## Format
Each entry follows this structure:
- **[Date]** - Brief description
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Fixed**: Bug fixes
- **Technical Details**: Implementation specifics
