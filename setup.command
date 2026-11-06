#!/bin/bash

# Transcribe Setup Script
# This script sets up all dependencies for the Transcribe application

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
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
success() {
  echo -e "${GREEN}✓ $1${NC}"
}

error() {
  echo -e "${RED}✗ $1${NC}"
}

warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

info() {
  echo -e "${BLUE}ℹ $1${NC}"
}

# ==============================================================================
# PHASE 1: CHECK DEPENDENCIES
# ==============================================================================

echo "Checking dependencies..."
echo ""

ALL_OK=true
PYTHON_MISSING=false
HOMEBREW_MISSING=false
DISK_SPACE_LOW=false
NO_INTERNET=false

# 1. Check Python
echo -n "Checking Python 3... "
PYTHON="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="/usr/local/bin/python3"
fi
if [ ! -x "$PYTHON" ]; then
  PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
fi
if [ ! -x "$PYTHON" ]; then
  error "not found"
  PYTHON_MISSING=true
  ALL_OK=false
else
  PYTHON_VERSION=$("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null || echo "unknown")
  success "Python $PYTHON_VERSION found"
fi

# 2. Check Homebrew
echo -n "Checking Homebrew... "
if command -v brew &> /dev/null; then
  BREW_VERSION=$(brew --version | head -n1)
  success "$BREW_VERSION"
else
  warning "not found (will install automatically)"
  HOMEBREW_MISSING=true
fi

# 3. Check Internet connectivity
echo -n "Checking internet connectivity... "
if ping -c 1 8.8.8.8 &> /dev/null || curl -s -m 2 https://www.google.com &> /dev/null; then
  success "OK"
else
  error "no internet connection"
  NO_INTERNET=true
  ALL_OK=false
fi

# 4. Check disk space
echo -n "Checking disk space... "
AVAILABLE_SPACE=$(($(df "$HOME" | tail -1 | awk '{print $4}') / 1024 / 1024))  # in GB
if [ "$AVAILABLE_SPACE" -lt 6 ]; then
  error "only ${AVAILABLE_SPACE}GB available (need 6GB)"
  DISK_SPACE_LOW=true
  ALL_OK=false
else
  success "${AVAILABLE_SPACE}GB available"
fi

# 5. Check if already set up
echo -n "Checking for existing setup... "
if [ -d ".venv" ]; then
  warning "virtual environment already exists"
else
  success "clean install"
fi

echo ""
echo "=========================================="

# ==============================================================================
# PHASE 2: REPORT ISSUES
# ==============================================================================

if [ "$PYTHON_MISSING" = true ]; then
  echo ""
  echo -e "${RED}ERROR: Python 3 is required but not found.${NC}"
  echo ""
  echo "Python must be installed manually:"
  echo "  1. Download Python 3.12+ from: https://www.python.org/downloads/macos/"
  echo "  2. Run the installer"
  echo "  3. Run this setup script again"
  echo ""
  exit 1
fi

if [ "$NO_INTERNET" = true ]; then
  echo ""
  echo -e "${RED}ERROR: No internet connection.${NC}"
  echo ""
  echo "An internet connection is required to download:"
  echo "  - Homebrew (if not installed)"
  echo "  - Ollama"
  echo "  - Python packages"
  echo "  - ML models (5+ GB)"
  echo ""
  echo "Please connect to the internet and try again."
  echo ""
  exit 1
fi

if [ "$DISK_SPACE_LOW" = true ]; then
  echo ""
  echo -e "${RED}ERROR: Not enough disk space.${NC}"
  echo ""
  echo "The setup requires at least 6 GB free space for:"
  echo "  - Python packages"
  echo "  - Whisper model (~2 GB)"
  echo "  - Qwen model (~5 GB)"
  echo ""
  echo "Please free up disk space and try again."
  echo ""
  exit 1
fi

# ==============================================================================
# PHASE 2.5: DETECT EXISTING SETUP
# ==============================================================================

SETUP_COMPLETE=false
if [ -d ".venv" ]; then
  # Find Ollama path for model check
  OLLAMA="/opt/homebrew/bin/ollama"
  if [ ! -x "$OLLAMA" ]; then
    OLLAMA="/usr/local/bin/ollama"
  fi
  
  # Check if Qwen model exists (this requires Ollama to be available)
  if [ -x "$OLLAMA" ] && $OLLAMA list 2>/dev/null | grep -q "qwen3:8b"; then
    SETUP_COMPLETE=true
  fi
fi

# ==============================================================================
# PHASE 3: ASK FOR PERMISSION
# ==============================================================================

echo ""
if [ "$SETUP_COMPLETE" = true ]; then
  echo "Setup is already complete."
  echo ""
  echo "Options:"
  echo "  [1] Update packages and models (recommended periodically)"
  echo "  [2] Skip setup (use existing installation)"
  echo ""
  read -r -p "Choose option (1 or 2, default=2): " SETUP_MODE
  if [ -z "$SETUP_MODE" ]; then
    SETUP_MODE="2"
  fi
  
  if [ "$SETUP_MODE" = "2" ]; then
    echo ""
    echo "Setup skipped. To start the app, run:"
    echo "  ./Start\ Transcriptie.command"
    echo ""
    exit 0
  fi
  
  # Mode 1: Update - modify prompts
  echo ""
  echo "Will update:"
  echo "  - Python packages (latest versions)"
  echo "  - Ollama and models (check for updates)"
  echo ""
else
  if [ "$HOMEBREW_MISSING" = true ]; then
    echo "Setup will:"
    echo "  1. Install Homebrew (required for Ollama)"
    echo "  2. Install Ollama"
    echo "  3. Create Python virtual environment"
    echo "  4. Install Python packages"
    echo "  5. Download ML models (~7 GB, may take 10-30 minutes)"
    echo ""
  else
    echo "Setup will:"
    echo "  1. Install Ollama (if not present)"
    echo "  2. Create Python virtual environment"
    echo "  3. Install Python packages"
    echo "  4. Download ML models (~7 GB, may take 10-30 minutes)"
    echo ""
  fi
fi

read -r -p "Proceed? (y/n) " -n 1
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Setup cancelled."
  exit 0
fi

# ==============================================================================
# PHASE 4: INSTALLATION
# ==============================================================================

echo ""
echo "Starting installation..."
echo ""

set -e

if [ "$SETUP_COMPLETE" = true ] && [ "$SETUP_MODE" = "1" ]; then
  echo "Updating packages and models..."
else
  echo "Complete setup in progress..."
fi
echo ""

# 2. Check/Install Homebrew (if needed)
if ! command -v brew &> /dev/null; then
  echo ""
  echo "Installing Homebrew (required for Ollama)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
    error "Failed to install Homebrew"
    exit 1
  }
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
  brew install ollama || {
    error "Failed to install Ollama"
    exit 1
  }
  OLLAMA="/opt/homebrew/bin/ollama"
fi
success "Ollama found at $OLLAMA"

# 4. Create virtual environment
echo ""
echo "Setting up Python virtual environment..."
if [ -d ".venv" ]; then
  warning "Virtual environment already exists"
else
  "$PYTHON" -m venv .venv || {
    error "Failed to create virtual environment"
    exit 1
  }
  success "Virtual environment created"
fi

# 5. Install Python dependencies
echo ""
echo "Installing Python dependencies..."
.venv/bin/python -m pip install --upgrade pip > /dev/null 2>&1 || true
.venv/bin/pip install -r requirements.txt || {
  error "Failed to install dependencies"
  exit 1
}
success "Python dependencies installed"

# 6. Check/Download Ollama model
echo ""
echo "Checking Ollama model (qwen3:8b)..."
if $OLLAMA list | grep -q "qwen3:8b"; then
  success "Model qwen3:8b already downloaded"
else
  warning "Downloading qwen3:8b model (this may take a few minutes)..."
  $OLLAMA pull qwen3:8b || {
    error "Failed to download model"
    exit 1
  }
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

# 8. Summary
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
