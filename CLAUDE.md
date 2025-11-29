# Dev Server Instructions

When asked to "run dev" or start development, ALWAYS start BOTH servers in parallel (background mode):

## Backend (FastAPI) - Port 8000
```bash
cd /home/ari/Documents/final_capstone/backend && .venv/bin/uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

## Frontend (Express + Vite) - Port 5000
```bash
cd /home/ari/Documents/final_capstone/frontend && npm run dev
```

## Important Notes
- Backend MUST use the virtual environment (`.venv/bin/uvicorn`) - do NOT use system uvicorn
- Frontend proxies `/api/*` requests to backend on port 8000
- Both servers must be running for the app to work

## Debugging: Common Issues

### API requests returning HTML instead of JSON
**Symptom**: `curl http://localhost:5000/api/labels` returns HTML page instead of JSON
**Cause**: Vite proxy not forwarding requests to backend
**Check**:
1. Verify backend is running: `curl http://localhost:8000/api/labels` should return JSON
2. Check `frontend/server/vite.ts` - the `serverOptions` must spread `...viteConfig.server` to preserve proxy settings
3. If proxy config is missing, the fix is in `vite.ts`:
```typescript
const serverOptions = {
  ...viteConfig.server,  // <-- This line preserves proxy config from vite.config.ts
  middlewareMode: true,
  hmr: { server, path: "/vite-hmr" },
  allowedHosts: true as const,
};
```

### Database not connecting
**Note**: This project uses file-based storage (CSV files), NOT PostgreSQL
- Processed data: `backend/database/`
- Raw data: `backend/raw_database/`
- The drizzle config in frontend is for user auth only (currently using MemStorage)

### Backend module import errors
**Fix**: Ensure running from correct directory with venv:
```bash
cd /home/ari/Documents/final_capstone/backend && .venv/bin/uvicorn api:app --reload
```

### Frontend not auto-reloading after changes
**Fix**: Kill and restart the frontend server - tsx doesn't always hot reload server files

## OpenAI API Configuration

- **Model**: Use `gpt-5.1` ONLY - do NOT use gpt-4o or any other model
- **No max_tokens**: The gpt-5.1 model does not support `max_tokens` parameter - never include it
- **Centralized config**: Model name is defined in `backend/settings/constants.py` as `OPENAI_MODEL`
- All code must import from constants - never hardcode the model name
