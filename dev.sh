#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🧹 Cleaning up previous processes...${NC}"

# Kill processes on port 8000 (backend)
BACKEND_PID=$(lsof -ti:8000)
if [ ! -z "$BACKEND_PID" ]; then
    echo -e "${YELLOW}Killing backend process on port 8000 (PID: $BACKEND_PID)${NC}"
    kill -9 $BACKEND_PID 2>/dev/null
    echo -e "${GREEN}✓ Backend port cleared${NC}"
else
    echo -e "${GREEN}✓ Port 8000 already free${NC}"
fi

# Kill processes on port 5000 (frontend)
FRONTEND_PID=$(lsof -ti:5000)
if [ ! -z "$FRONTEND_PID" ]; then
    echo -e "${YELLOW}Killing frontend process on port 5000 (PID: $FRONTEND_PID)${NC}"
    kill -9 $FRONTEND_PID 2>/dev/null
    echo -e "${GREEN}✓ Frontend port cleared${NC}"
else
    echo -e "${GREEN}✓ Port 5000 already free${NC}"
fi

# Wait a moment for ports to be released
sleep 1

echo -e "\n${GREEN}🚀 Starting development servers...${NC}\n"

# Start backend in background
echo -e "${YELLOW}Starting backend on port 8000...${NC}"
cd /home/ari/Documents/final_capstone/backend && .venv/bin/uvicorn api:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"

# Start frontend in background
echo -e "${YELLOW}Starting frontend on port 5000...${NC}"
cd /home/ari/Documents/final_capstone/frontend && npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"

echo -e "\n${GREEN}✅ Development servers started!${NC}"
echo -e "${YELLOW}Backend: http://localhost:8000${NC}"
echo -e "${YELLOW}Frontend: http://localhost:5000${NC}"
echo -e "\n${YELLOW}Logs:${NC}"
echo -e "  Backend:  tail -f /tmp/backend.log"
echo -e "  Frontend: tail -f /tmp/frontend.log"
echo -e "\n${YELLOW}To stop servers:${NC}"
echo -e "  kill $BACKEND_PID $FRONTEND_PID"
echo -e "\nPress Ctrl+C to exit (servers will continue running in background)"

# Keep script running and show combined logs
trap "echo -e '\n${YELLOW}Script exited. Servers still running in background.${NC}'; exit" INT

# Show combined logs
tail -f /tmp/backend.log /tmp/frontend.log
