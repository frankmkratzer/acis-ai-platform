#!/bin/bash
# Start FastAPI Backend Server

cd "$(dirname "$0")/.."
source venv/bin/activate

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "============================================"
echo "ACIS AI Platform - FastAPI Backend"
echo "============================================"
echo ""
echo "Starting server..."
echo "  URL: http://localhost:8000"
echo "  API Docs: http://localhost:8000/api/docs"
echo "  ReDoc: http://localhost:8000/api/redoc"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run with uvicorn
cd backend/api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
