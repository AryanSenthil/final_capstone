# Environment Variables Setup Guide

## Overview

This project uses a **web-based UI** for configuring the OpenAI API key. Users paste the API key in the frontend, and it gets saved to `backend/.env` automatically.

The API key is used by the backend for:
- AI agent chat functionality
- Label suggestion (`suggest_label`)
- Model name suggestion (`suggest_model_name`)
- Test notes generation (`generate_notes`)

---

## How It Works

### User Flow

1. **User opens the app** (frontend at `http://ip:5000`)
2. **Clicks settings/API key dialog** (usually in header/navbar)
3. **Pastes OpenAI API key** in the dialog input field
4. **Clicks "Save API Key"**
5. **Frontend sends key to backend** via `POST /api/settings/api-key`
6. **Backend saves to `.env` file** and updates environment variable
7. **API key is ready to use** - no server restart needed!

### Technical Flow

```
Frontend (Browser)
    ↓
User pastes key: "sk-proj-xxxxx..."
    ↓
POST /api/settings/api-key
    ↓
Backend (settings_api.py:185)
    ↓
Write to backend/.env file
    ↓
Update os.environ["OPENAI_API_KEY"]
    ↓
Reinitialize OpenAI client
    ↓
✓ Key active immediately
```

---

## Frontend Component

### ApiKeyDialog Component

**Location**: `frontend/client/src/components/api-key-dialog.tsx`

**Features**:
- Password input with show/hide toggle
- Displays masked existing key (e.g., `sk-proj...xy12`)
- "Where to get API key" instructions
- Saves key to backend `.env` file

**Usage in App**:
```typescript
import { ApiKeyDialog } from "@/components/api-key-dialog";

function App() {
  const [apiKeyDialogOpen, setApiKeyDialogOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setApiKeyDialogOpen(true)}>
        Configure API Key
      </Button>

      <ApiKeyDialog
        open={apiKeyDialogOpen}
        onOpenChange={setApiKeyDialogOpen}
      />
    </>
  );
}
```

### How It Sends the Key

```typescript
// frontend/client/src/components/api-key-dialog.tsx:72-78
const response = await fetch("/api/settings/api-key", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ api_key: apiKey }),
});
```

---

## Backend API

### Endpoints

**File**: `backend/settings_api.py`

#### `GET /api/settings/api-key`
**Description**: Check if API key is configured
**Response**:
```json
{
  "configured": true,
  "masked_key": "sk-proj...xy12"
}
```
**Logic**:
1. Checks `backend/.env` file for `OPENAI_API_KEY=`
2. Falls back to environment variable
3. Returns masked version (first 7 chars + last 4 chars)

#### `POST /api/settings/api-key`
**Description**: Save API key to `.env` file
**Request**:
```json
{
  "api_key": "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```
**Response**:
```json
{
  "success": true,
  "message": "API key saved to .env file successfully"
}
```

**What It Does** (`settings_api.py:186-226`):
1. Reads existing `backend/.env` file
2. Updates `OPENAI_API_KEY=` line (or adds if missing)
3. Writes back to `.env` file
4. Sets `os.environ["OPENAI_API_KEY"]` for current session
5. Reinitializes OpenAI client in `api.py`

**No restart needed!** The backend updates the client immediately.

---

## Backend .env File

### Location
```
backend/.env
```

### Format
```bash
OPENAI_API_KEY="sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### How It's Created

**Automatically** when user saves key via frontend dialog:
1. User pastes key in UI
2. Backend receives POST request
3. Backend creates/updates `.env` file
4. Backend sets environment variable
5. Backend reinitializes OpenAI client

**Manually** (for development):
```bash
cd backend
echo 'OPENAI_API_KEY="sk-proj-xxxxx..."' > .env
```

### Security

- `.env` is in `.gitignore` (never committed)
- File permissions: `chmod 600 .env` (recommended)
- Key is stored server-side only (never exposed to browser)
- Frontend sends key once, backend stores it

---

## Development Setup

### First-Time Setup

1. **Start the servers**:
   ```bash
   ./dev.sh
   # Or manually:
   # Backend: cd backend && .venv/bin/uvicorn api:app --reload --port 8000
   # Frontend: cd frontend && npm run dev  # Port 5000
   ```

2. **Open frontend**: `http://localhost:5000`

3. **Click "Settings" or "Configure API Key"** (usually in navbar)

4. **Get OpenAI API key**:
   - Go to https://platform.openai.com/api-keys
   - Sign in or create account
   - Click "Create new secret key"
   - Copy the key (starts with `sk-proj-...`)

5. **Paste key in dialog** and click "Save"

6. **Done!** The key is now in `backend/.env`

### Verify Setup

```bash
# Check .env file exists
cat backend/.env

# Should show:
# OPENAI_API_KEY="sk-proj-xxxxx..."

# Test API key works
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# Should get response (not error about missing key)
```

---

## Production Deployment (EC2)

### Setup Steps

1. **Deploy code to EC2**:
   ```bash
   # SSH to server
   ssh -i your-key.pem ubuntu@34.204.204.26

   # Pull latest code
   cd /path/to/final_capstone
   git pull
   ```

2. **Start backend**:
   ```bash
   cd backend
   .venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000

   # Or as systemd service:
   sudo systemctl start damage-lab-backend
   ```

3. **Start frontend**:
   ```bash
   cd frontend
   npm run build  # Build production
   npm run start  # Start on port 5000
   ```

4. **Access frontend**: `http://34.204.204.26:5000`

5. **Configure API key via UI**:
   - Open settings dialog
   - Paste OpenAI API key
   - Click "Save API Key"
   - Backend creates/updates `.env` automatically

6. **Done!** No need to SSH or edit files manually

### Alternative: Manual .env Creation (Optional)

If you prefer to create `.env` manually on EC2:

```bash
ssh ubuntu@34.204.204.26
cd /path/to/backend
nano .env

# Add:
OPENAI_API_KEY="sk-proj-xxxxx..."

# Save and restart backend
sudo systemctl restart damage-lab-backend
```

But the **UI method is recommended** - easier and doesn't require SSH.

---

## Troubleshooting

### Issue: "API Key Not Configured" Error

**Check 1**: Verify key in `.env`
```bash
cd backend
cat .env
# Should show: OPENAI_API_KEY="sk-proj-..."
```

**Check 2**: Verify key loaded
```bash
cd backend
.venv/bin/python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('✓ Key loaded' if os.getenv('OPENAI_API_KEY') else '✗ Key NOT found')"
```

**Check 3**: Test via frontend
- Open settings dialog
- Should show masked key if configured
- If not, paste and save new key

### Issue: Key Saved But Not Working

**Solution 1**: Reload backend manually
```bash
# Development
# Just save key via UI - it reloads automatically

# Production (if using systemd)
sudo systemctl restart damage-lab-backend
```

**Solution 2**: Check backend logs
```bash
# Look for errors
tail -f backend/logs/app.log

# Or check systemd logs
journalctl -u damage-lab-backend -f
```

### Issue: Frontend Dialog Not Showing Masked Key

**Cause**: Backend not reading `.env` correctly

**Fix**:
1. Check `.env` file format: `OPENAI_API_KEY="sk-proj-..."`
2. Ensure no extra spaces or quotes
3. Restart backend if needed

### Issue: Permission Denied Writing .env

**Cause**: Backend doesn't have write permissions

**Fix**:
```bash
cd backend
chmod 664 .env
chown $USER:$USER .env

# Or for systemd service
sudo chown www-data:www-data .env
```

---

## Security Best Practices

### ✅ DO:
- Use the frontend UI to configure API key (easiest and safest)
- Keep `.env` in `.gitignore` (already configured)
- Set restrictive file permissions: `chmod 600 backend/.env`
- Rotate API key if exposed
- Monitor API usage in OpenAI dashboard
- Use environment variables in production (the UI saves to both `.env` and `os.environ`)

### ❌ DON'T:
- Commit `.env` to git
- Share `.env` file or screenshots showing the key
- Hardcode API key in source code
- Put API key in frontend code (it's only sent once to backend)
- Include API key in docker images (use volumes/secrets)
- Log API key values

---

## Frontend Dialog Locations

The API key dialog may be accessible from:

1. **Settings button** in navbar/header
2. **Profile/account menu**
3. **First-run setup wizard**
4. **Settings page** (`/settings`)

**Check**: `frontend/client/src/components/layout.tsx` or similar for the button that opens `ApiKeyDialog`.

---

## Backend Implementation Details

### File: `backend/settings_api.py`

**Key Functions**:

#### `get_api_key_status()` (line 149-182)
```python
# Checks .env file and environment variable
# Returns masked key: "sk-proj...xy12"
```

#### `update_api_key(update: ApiKeyUpdate)` (line 185-226)
```python
# 1. Read .env file
# 2. Update/add OPENAI_API_KEY line
# 3. Write to .env
# 4. Set os.environ["OPENAI_API_KEY"]
# 5. Reinitialize OpenAI client
```

**Router**:
```python
router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("/api-key")
async def get_api_key_status(): ...

@router.post("/api-key")
async def update_api_key(update: ApiKeyUpdate): ...
```

**Included in**: `backend/api.py` imports this router
```python
from settings_api import router as settings_router
app.include_router(settings_router)
```

---

## Summary

### Key Points

1. **UI-Based Configuration**: Users paste API key in frontend dialog
2. **Automatic .env Creation**: Backend saves key to `.env` file automatically
3. **No Restart Needed**: Backend reloads OpenAI client immediately
4. **Server-Side Only**: Key is stored and used only on backend
5. **Persists Across Restarts**: Key in `.env` survives server restarts

### Quick Setup

**Development**:
```bash
./dev.sh                           # Start servers
# Open http://localhost:5000
# Click settings → Paste API key → Save
# Done!
```

**Production (EC2)**:
```bash
# Deploy code and start servers
# Open http://34.204.204.26:5000
# Click settings → Paste API key → Save
# Done!
```

### Architecture

```
USER
  ↓ Pastes API key in browser
FRONTEND (ApiKeyDialog)
  ↓ POST /api/settings/api-key
BACKEND (settings_api.py)
  ↓ Writes to backend/.env
  ↓ Sets os.environ["OPENAI_API_KEY"]
  ↓ Reinitializes OpenAI client
  ↓
✓ API key active - no restart needed
```

---

## Related Documentation

- **Backend Architecture**: See `SERVER.md`
- **Frontend Components**: See `CLIENT.md`
- **API Endpoints**: See `API-ENDPOINTS.md`
- **Settings API**: This document
- **OpenAI Configuration**: See `CLAUDE.md` > "OpenAI API Configuration"

---

## Version

Last updated: 2025-01-15

This configuration method was designed for ease of use - users don't need SSH access or command-line knowledge. They simply paste the key in the UI!
