#!/bin/bash
# Cloudsnake Server Setup Script
# This script creates a virtual environment and installs dependencies

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"

echo "============================================"
echo "Cloudsnake Server Setup"
echo "============================================"
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Found Python $PYTHON_VERSION"

# Create virtual environment if it doesn't exist or is incomplete
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    echo "✓ Virtual environment already exists at $VENV_DIR"
else
    if [ -d "$VENV_DIR" ]; then
        echo "⚠ Virtual environment exists but is incomplete, recreating..."
        rm -rf "$VENV_DIR"
    else
        echo "Creating virtual environment..."
    fi
    python3 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created at $VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies from requirements.txt..."
pip install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "============================================"
echo "✓ Setup complete!"
echo "============================================"
echo ""
echo "Virtual environment: $VENV_DIR"
echo "Python: $(which python)"
echo ""
echo "To manually activate the virtual environment:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To start the server manually:"
echo "  $VENV_DIR/bin/python server.py"
echo ""
echo "To install as a systemd service:"
echo "  sudo ./install-service.sh"
echo ""
