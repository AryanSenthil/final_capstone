#!/bin/bash
# =============================================================================
# Production Deployment Script for Damage Lab Application
# =============================================================================
# This script deploys the application on an AWS EC2 instance.
# It handles both backend (FastAPI) and frontend (Express + React) servers.
# =============================================================================

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/pids"

BACKEND_PORT=8000
FRONTEND_PORT=5000

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   Damage Lab Production Deployment${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Create directories
mkdir -p "$LOG_DIR" "$PID_DIR"

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on a port
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}Stopping process on port $port...${NC}"
        kill -9 $pids 2>/dev/null || true
        sleep 1
        echo -e "${GREEN}✓ Port $port cleared${NC}"
    fi
}

# Function to check Python dependencies
check_backend_deps() {
    echo -e "${YELLOW}Checking backend dependencies...${NC}"

    if [ ! -d "$BACKEND_DIR/.venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        cd "$BACKEND_DIR"
        python3 -m venv .venv
    fi

    # Activate and install dependencies
    source "$BACKEND_DIR/.venv/bin/activate"

    # Check if requirements are installed
    if ! pip show fastapi > /dev/null 2>&1; then
        echo -e "${YELLOW}Installing Python dependencies...${NC}"
        pip install -r "$BACKEND_DIR/requirements.txt" --quiet
    fi

    echo -e "${GREEN}✓ Backend dependencies ready${NC}"
}

# Function to check Node.js dependencies
check_frontend_deps() {
    echo -e "${YELLOW}Checking frontend dependencies...${NC}"

    cd "$FRONTEND_DIR"

    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
        npm install --silent
    fi

    echo -e "${GREEN}✓ Frontend dependencies ready${NC}"
}

# Function to check for .env file
check_env() {
    if [ ! -f "$BACKEND_DIR/.env" ]; then
        echo -e "${YELLOW}Creating .env file...${NC}"
        echo '# OpenAI API Key - Add your key here or via the web interface' > "$BACKEND_DIR/.env"
        echo 'OPENAI_API_KEY=""' >> "$BACKEND_DIR/.env"
        echo -e "${YELLOW}Note: Add your OpenAI API key via the web interface (Settings -> API Key)${NC}"
    fi

    # Check if API key is set
    if grep -q 'OPENAI_API_KEY=""' "$BACKEND_DIR/.env" 2>/dev/null; then
        echo -e "${YELLOW}⚠ OpenAI API key not configured. AI features will be limited.${NC}"
        echo -e "${YELLOW}  Configure via web interface: Settings -> API Key${NC}"
    fi
}

# Function to start backend
start_backend() {
    echo -e "${YELLOW}Starting backend server on port $BACKEND_PORT...${NC}"

    # Kill existing process
    kill_port $BACKEND_PORT

    cd "$BACKEND_DIR"
    source .venv/bin/activate

    # Start uvicorn in production mode
    nohup .venv/bin/uvicorn api:app \
        --host 0.0.0.0 \
        --port $BACKEND_PORT \
        --workers 2 \
        --log-level info \
        > "$LOG_DIR/backend.log" 2>&1 &

    BACKEND_PID=$!
    echo $BACKEND_PID > "$PID_DIR/backend.pid"

    # Wait for backend to start
    sleep 3

    if check_port $BACKEND_PORT; then
        echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
    else
        echo -e "${RED}✗ Backend failed to start. Check logs: $LOG_DIR/backend.log${NC}"
        exit 1
    fi
}

# Function to start frontend
start_frontend() {
    echo -e "${YELLOW}Starting frontend server on port $FRONTEND_PORT...${NC}"

    # Kill existing process
    kill_port $FRONTEND_PORT

    cd "$FRONTEND_DIR"

    # Start in production mode
    NODE_ENV=production nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &

    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$PID_DIR/frontend.pid"

    # Wait for frontend to start
    sleep 5

    if check_port $FRONTEND_PORT; then
        echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
    else
        echo -e "${RED}✗ Frontend failed to start. Check logs: $LOG_DIR/frontend.log${NC}"
        exit 1
    fi
}

# Function to stop all servers
stop_servers() {
    echo -e "${YELLOW}Stopping all servers...${NC}"

    if [ -f "$PID_DIR/backend.pid" ]; then
        kill $(cat "$PID_DIR/backend.pid") 2>/dev/null || true
        rm -f "$PID_DIR/backend.pid"
    fi

    if [ -f "$PID_DIR/frontend.pid" ]; then
        kill $(cat "$PID_DIR/frontend.pid") 2>/dev/null || true
        rm -f "$PID_DIR/frontend.pid"
    fi

    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT

    echo -e "${GREEN}✓ All servers stopped${NC}"
}

# Function to show status
show_status() {
    echo ""
    echo -e "${BLUE}Server Status:${NC}"
    echo "----------------------------------------"

    if check_port $BACKEND_PORT; then
        echo -e "Backend (port $BACKEND_PORT):  ${GREEN}RUNNING${NC}"
    else
        echo -e "Backend (port $BACKEND_PORT):  ${RED}STOPPED${NC}"
    fi

    if check_port $FRONTEND_PORT; then
        echo -e "Frontend (port $FRONTEND_PORT): ${GREEN}RUNNING${NC}"
    else
        echo -e "Frontend (port $FRONTEND_PORT): ${RED}STOPPED${NC}"
    fi

    echo "----------------------------------------"
}

# Function to show logs
show_logs() {
    echo -e "${YELLOW}Showing combined logs (Ctrl+C to exit)...${NC}"
    tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log"
}

# Function to get public IP
get_public_ip() {
    # Try multiple methods to get public IP
    PUBLIC_IP=$(curl -s --connect-timeout 5 http://checkip.amazonaws.com 2>/dev/null || \
                curl -s --connect-timeout 5 http://ipecho.net/plain 2>/dev/null || \
                curl -s --connect-timeout 5 http://icanhazip.com 2>/dev/null || \
                echo "Unable to detect")
    echo "$PUBLIC_IP"
}

# Main deployment function
deploy() {
    echo -e "${YELLOW}Starting deployment...${NC}"
    echo ""

    # Check dependencies
    check_backend_deps
    check_frontend_deps
    check_env

    echo ""

    # Start servers
    start_backend
    start_frontend

    echo ""
    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}   Deployment Complete!${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""

    # Get public IP for access info
    PUBLIC_IP=$(get_public_ip)

    echo -e "${BLUE}Access the application:${NC}"
    echo -e "  Local:   http://localhost:$FRONTEND_PORT"
    if [ "$PUBLIC_IP" != "Unable to detect" ]; then
        echo -e "  Public:  http://$PUBLIC_IP:$FRONTEND_PORT"
    fi
    echo ""
    echo -e "${BLUE}API Endpoints:${NC}"
    echo -e "  Backend: http://localhost:$BACKEND_PORT/api"
    echo ""
    echo -e "${BLUE}Logs:${NC}"
    echo -e "  Backend:  tail -f $LOG_DIR/backend.log"
    echo -e "  Frontend: tail -f $LOG_DIR/frontend.log"
    echo ""
    echo -e "${BLUE}Commands:${NC}"
    echo -e "  Stop:     ./deploy.sh stop"
    echo -e "  Restart:  ./deploy.sh restart"
    echo -e "  Status:   ./deploy.sh status"
    echo -e "  Logs:     ./deploy.sh logs"
    echo ""
}

# Handle command line arguments
case "${1:-start}" in
    start|deploy)
        deploy
        ;;
    stop)
        stop_servers
        ;;
    restart)
        stop_servers
        sleep 2
        deploy
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start   - Start all servers (default)"
        echo "  stop    - Stop all servers"
        echo "  restart - Restart all servers"
        echo "  status  - Show server status"
        echo "  logs    - Show live logs"
        exit 1
        ;;
esac
