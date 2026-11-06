#!/bin/bash

# Transcribe Setup Script
# This script sets up all dependencies for the Transcribe application

set -e

cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

echo "=========================================="
echo "  Transcribe Setup Installer"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
success() {
  echo -e "${GREEN}✓ $1${NC}"
}

error() {
  echo -e "${RED}✗ $1${NC}"
  exit 1
}

warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

# 1. Check Python
echo "Checking Python..."
PYTHON="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="/usr/local/bin/python3"
fi
if [ ! -x "$PYTHON" ]; then
  PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
fi
if [ ! -x "$PYTHON" ]; then
  error "Python 3 not found. Install Python from https://www.python.org/downloads/macos/"
fi

PYTHON_VERSION=$("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
success "Python $PYTHON_VERSION found"

# 2. Check/Install Homebrew (if needed)
if ! command -v brew &> /dev/null; then
  echo ""
  echo "Installing Homebrew (required for Ollama)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || error "Failed to install Homebrew"
  export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  success "Homebrew installed"
else
  success "Homebrew already installed"
fi

# 3. Check/Install Ollama
echo ""
echo "Checking Ollama..."
OLLAMA="/opt/homebrew/bin/ollama"
if [ ! -x "$OLLAMA" ]; then
  OLLAMA="/usr/local/bin/ollama"
fi

if [ ! -x "$OLLAMA" ]; then
  warning "Ollama not found. Installing via Homebrew..."
  brew install ollama || error "Failed to install Ollama"
  OLLAMA="/opt/homebrew/bin/ollama"
fi
success "Ollama found at $OLLAMA"

# 4. Create virtual environment
echo ""
echo "Setting up Python virtual environment..."
if [ -d ".venv" ]; then
  warning "Virtual environment already exists"
else
  "$PYTHON" -m venv .venv || error "Failed to create virtual environment"
  success "Virtual environment created"
fi

# 5. Install Python dependencies
echo ""
echo "Installing Python dependencies..."
.venv/bin/python -m pip install --upgrade pip > /dev/null 2>&1 || true
.venv/bin/pip install -r requirements.txt || error "Failed to install dependencies"
success "Python dependencies installed"

# 6. Check/Download Ollama model
echo ""
echo "Checking Ollama model (qwen3:8b)..."
if $OLLAMA list | grep -q "qwen3:8b"; then
  success "Model qwen3:8b already downloaded"
else
  warning "Downloading qwen3:8b model (this may take a few minutes)..."
  $OLLAMA pull qwen3:8b || error "Failed to download model"
  success "Model downloaded"
fi

# 7. Disable Ollama cloud (privacy)
echo ""
echo "Configuring Ollama (disabling cloud)..."
OLLAMA_CONFIG="$HOME/.ollama/server.json"
if [ -f "$OLLAMA_CONFIG" ]; then
  python3 << 'EOF'
import json
from pathlib import Path

config_path = Path.home() / ".ollama" / "server.json"
try:
  with open(config_path) as f:
    config = json.load(f)
except:
  config = {}

config["disable_ollama_cloud"] = True

with open(config_path, 'w') as f:
  json.dump(config, f, indent=2)

print("✓ Ollama cloud disabled (privacy protected)")
EOF
else
  warning "Ollama config not found, skipping cloud disable"
fi

# 7. Summary
echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "To start the application, run:"
echo "  ./Start\ Transcriptie.command"
echo ""
echo "Or manually:"
echo "  ollama serve &"
echo "  .venv/bin/python app.py"
echo ""
