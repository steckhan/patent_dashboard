#!/bin/bash

# Patent Research Dashboard Launcher
# This script sets up the Python environment and launches the Streamlit dashboard

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Patent Intelligence Dashboard Launcher"
echo "=========================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -q -r requirements.txt

echo "✓ Dependencies installed"

# Launch dashboard
echo ""
echo "🎯 Launching Streamlit dashboard..."
echo "   Local URL: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the dashboard"
echo ""

streamlit run src/app.py
