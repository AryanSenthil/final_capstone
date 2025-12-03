# Claude Code Documentation

This directory contains comprehensive documentation for working with the Damage Lab project in Claude Code.

## Documentation Files

### 1. **CLAUDE.md** (Main Instructions)
The main project instructions that Claude reads automatically. Contains:
- Dev server startup instructions
- OpenAI configuration (use gpt-5.1)
- UI patterns and styling guidelines
- Common debugging issues

**When to read**: Claude reads this automatically for every session.

### 2. **SERVER.md** (Backend Architecture)
Comprehensive backend guide covering:
- Directory structure and data flow
- Upload/Download architecture (Client ↔ Server)
- Agent tools and system
- CORS, database storage, common issues
- Guidelines for adding features

**When to read**:
- Working on backend code
- Adding new API endpoints
- Modifying agent tools
- Debugging server issues

### 3. **CLIENT.md** (Frontend Architecture)
Complete frontend guide covering:
- Component architecture
- Upload/Download patterns
- React Query setup
- UI patterns and styling
- Common issues and debugging

**When to read**:
- Working on frontend code
- Adding new components
- Implementing file uploads
- Debugging frontend issues

### 4. **API-ENDPOINTS.md** (REST API Reference)
Complete API endpoint reference (48 endpoints):
- Labels/Datasets (10)
- Raw Database (5)
- Ingestion (3)
- Training (8)
- Models (9)
- Reports (5)
- Tests (10)

**When to read**:
- `api.py` is too large to read directly (2813 lines)
- Need to understand endpoint behavior
- Implementing frontend API calls
- Adding new endpoints

### 5. **CHAT-API-ENDPOINTS.md** (Chat API Reference)
Chat/agent endpoint reference (7 endpoints):
- Streaming and non-streaming chat
- Session management
- Tool execution
- Artifact generation

**When to read**:
- Working with chat interface
- Debugging agent behavior
- Understanding tool execution
- Implementing streaming

### 6. **ENV-SETUP.md** (Environment Variables)
OpenAI API key configuration guide:
- How to set up API key on backend server
- Development vs Production setup
- Security best practices
- Troubleshooting

**When to read**:
- Setting up development environment
- Deploying to EC2 production
- API key not working errors
- Chat/agent features not responding

---

## Quick Navigation

### I need to...

**Start the dev server**
→ Read: `CLAUDE.md` > "Dev Server Instructions"

**Upload files from client to server**
→ Read: `CLIENT.md` > "Upload Flow" & `SERVER.md` > "UPLOADS"

**Add a new API endpoint**
→ Read: `SERVER.md` > "When Adding New Features" & `API-ENDPOINTS.md` for patterns

**Add a new agent tool**
→ Read: `SERVER.md` > "Adding a New Agent Tool"

**Work with the chat interface**
→ Read: `CLIENT.md` > "Chat Page" & `CHAT-API-ENDPOINTS.md`

**Debug API proxy issues**
→ Read: `CLIENT.md` > "Common Issues" > "API requests returning HTML"

**Understand data flow**
→ Read: `SERVER.md` > "Data Flow Architecture"

**Add a new React component**
→ Read: `CLIENT.md` > "When Adding New Features"

**Set up OpenAI API key**
→ Read: `ENV-SETUP.md`

**Deploy to production (EC2)**
→ Read: `ENV-SETUP.md` > "Production (EC2 Server)"

---

## Key Principles

### 🔄 Upload/Download Architecture

**CRITICAL**: The server stores ALL data. Clients NEVER browse server filesystem.

```
UPLOADS (Client → Server):
User's Computer → Native File Picker → POST /api/upload → Server Storage

DOWNLOADS (Server → Client):
Server Storage → GET /api/download → User's Computer

BROWSE:
Only show what's ALREADY uploaded (never browse server filesystem)
```

See: `SERVER.md` > "Data Flow Architecture" & `CLIENT.md` > "Architecture Principles"

### 🤖 OpenAI Configuration

**Model**: `gpt-5.1` ONLY (configured in `settings/constants.py`)

```python
from settings.constants import OPENAI_MODEL  # "gpt-5.1"

# ✅ Correct
client.chat.completions.create(
    model=OPENAI_MODEL,
    messages=[...],
)

# ❌ Wrong
model="gpt-4o"           # Wrong model
max_tokens=1000          # Not supported by gpt-5.1
```

See: `CLAUDE.md` > "OpenAI API Configuration" & `SERVER.md` > "OpenAI Configuration"

### 📁 File Structure

```
backend/
├── api.py              # Main API (TOO LARGE - use API-ENDPOINTS.md)
├── chat_api.py         # Chat API (use CHAT-API-ENDPOINTS.md)
├── agent/              # AI agent system
│   └── damage_lab_agent.py  # All tools defined here
├── database/           # Processed data (ready for training)
├── raw_database/       # Uploaded raw data (unprocessed)
├── test_uploads/       # Test CSV files
├── test_database/      # Inference results
└── models/            # Trained models

frontend/
└── client/src/
    ├── pages/         # Main pages (chat, data, training, testing)
    ├── components/    # Reusable components + modals
    └── lib/           # React Query, utils
```

See: `SERVER.md` & `CLIENT.md` > "Directory Structure"

---

## Common Tasks

### Start Development

```bash
# Quick start (recommended)
./dev.sh

# Manual start
cd backend && .venv/bin/uvicorn api:app --reload --port 8000
cd frontend && npm run dev  # Port 5000
```

See: `CLAUDE.md` > "Dev Server Instructions"

### Add File Upload Feature

1. Read: `CLIENT.md` > "File Upload Pattern"
2. Create native file picker with drag & drop
3. Upload to appropriate endpoint:
   - Training data → `POST /api/raw-database/upload`
   - Test data → `POST /api/tests/upload`
4. Never browse server filesystem

### Add Agent Tool

1. Define function in `agent/damage_lab_agent.py`
2. Add to `ALL_TOOLS` list
3. Export in `agent/__init__.py`
4. Register in `chat_runner.py` and `chat_api.py`

See: `SERVER.md` > "Adding a New Agent Tool"

### Debug Proxy Issues

**Symptom**: API returns HTML instead of JSON

**Check**:
1. Backend running on port 8000? `curl http://localhost:8000/api/labels`
2. Proxy config spread? Check `frontend/server/vite.ts`
3. Restart frontend

See: `CLIENT.md` > "Common Issues" > "API requests returning HTML"

---

## Architecture Diagrams

### Data Flow (Upload → Process → Train → Test)

```
1. UPLOAD
   User's Computer → Native Picker → POST /api/raw-database/upload
   └─> raw_database/{folder}/*.csv

2. PROCESS
   POST /api/ingest (folder_path, label)
   └─> database/{label}/chunk_*.csv

3. TRAIN
   POST /api/training/start (labels, model_name)
   └─> models/{model_id}/*.h5

4. TEST
   User's Computer → Native Picker → POST /api/tests/upload
   └─> test_uploads/file.csv
   POST /api/tests/inference (csv_path, model_id)
   └─> test_database/{test_id}/results.csv

5. DOWNLOAD
   GET /api/{resource}/download
   └─> User's Computer
```

### Agent Tool Execution

```
User Message
    ↓
Agent Planning
    ↓
Tool Selection
    ↓
Sequential Tool Execution:
    tool_start event → execute → tool_result event
    tool_start event → execute → tool_result event
    ↓
Response Generation
    ↓
Stream content chunks
    ↓
Done event
```

---

## When Files Are Too Large

### api.py (2813 lines)
**Use instead**: `API-ENDPOINTS.md`
- Contains all 48 endpoints documented
- Request/response examples
- Error handling

### chat_api.py (797 lines)
**Use instead**: `CHAT-API-ENDPOINTS.md`
- All 7 chat endpoints
- Streaming guide
- Tool execution flow

---

## Best Practices

### ✅ DO

- Use `API-ENDPOINTS.md` instead of reading `api.py`
- Follow upload/download patterns from `CLIENT.md`
- Use centralized `OPENAI_MODEL` constant
- Add hover effects to interactive buttons
- Invalidate React Query cache after mutations
- Show toast notifications for user feedback
- Use native file pickers (never browse server filesystem)

### ❌ DON'T

- Browse server filesystem from client
- Hardcode model name (use `OPENAI_MODEL`)
- Use `max_tokens` parameter (gpt-5.1 doesn't support it)
- Set `Content-Type` header for `FormData` uploads
- Reference `FileBrowserDialog` (doesn't exist - use `FileUploadDialog`)
- Forget to spread `...viteConfig.server` in Vite setup

---

## Getting Help

1. **Check this README** for navigation
2. **Read relevant .md file** for detailed info
3. **Check CLAUDE.md** for quick fixes
4. **Search API-ENDPOINTS.md** for endpoint details

---

## File Summaries

| File | Lines | Purpose | Read When |
|------|-------|---------|-----------|
| `CLAUDE.md` | Auto-loaded | Quick reference, dev setup | Always (auto) |
| `SERVER.md` | Comprehensive | Backend architecture | Backend work |
| `CLIENT.md` | Comprehensive | Frontend architecture | Frontend work |
| `API-ENDPOINTS.md` | Reference | All REST endpoints | API work |
| `CHAT-API-ENDPOINTS.md` | Reference | Chat/agent endpoints | Chat work |
| `ENV-SETUP.md` | Guide | Environment variables, API key | Setup/Deploy |
| `README.md` | Navigation | Index and guide | Finding docs |

---

## Maintenance

When updating the project:

- **New endpoint** → Add to `API-ENDPOINTS.md`
- **New agent tool** → Update `SERVER.md` > "Agent Tools"
- **New component pattern** → Update `CLIENT.md`
- **Config change** → Update `CLAUDE.md`
- **Architecture change** → Update relevant .md files

---

## Version

Documentation created: 2025-01-15
Last updated: 2025-01-15

For latest project instructions, always check `CLAUDE.md` first.
