#!/bin/bash
# Development server startup script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting ALPROJ GUI development servers...${NC}"

# Function to kill process and all its children
kill_tree() {
    local pid=$1
    local sig=${2:-TERM}

    # Get all child processes
    local children=$(pgrep -P $pid 2>/dev/null || true)

    # Kill children first (recursively)
    for child in $children; do
        kill_tree $child $sig
    done

    # Kill the process itself
    kill -$sig $pid 2>/dev/null || true
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"

    # Kill process trees gracefully first
    if [ -n "$BACKEND_PID" ]; then
        kill_tree $BACKEND_PID TERM
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill_tree $FRONTEND_PID TERM
    fi

    # Wait a moment for graceful shutdown
    sleep 1

    # Force kill any remaining processes
    if [ -n "$BACKEND_PID" ]; then
        kill_tree $BACKEND_PID KILL
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill_tree $FRONTEND_PID KILL
    fi

    # Also kill any process using our ports (belt and suspenders)
    lsof -ti :8765 | xargs kill -9 2>/dev/null || true
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true

    echo -e "${GREEN}Servers stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Start backend
echo -e "${GREEN}Starting backend server...${NC}"
cd backend
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
uvicorn app.main:app --reload --port 8765 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
sleep 2

# Start frontend
echo -e "${GREEN}Starting frontend dev server...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo -e "${GREEN}Development servers started!${NC}"
echo -e "  Backend:  http://localhost:8765"
echo -e "  Frontend: http://localhost:5173"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"

# Wait for both processes
wait
