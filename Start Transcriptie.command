#!/bin/bash
cd "$(dirname "$0")"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

# Store PIDs for cleanup
OLLAMA_PID=""
PYTHON_PID=""

# Cleanup function: runs when script exits or receives interrupt
cleanup() {
  echo ""
  echo "Afsluiten en opruimen..."
  if [ -n "$PYTHON_PID" ]; then
    kill "$PYTHON_PID" 2>/dev/null || true
  fi
  if [ -n "$OLLAMA_PID" ]; then
    kill "$OLLAMA_PID" 2>/dev/null || true
  fi
  exit 0
}

# Set trap to run cleanup on exit and interrupt
trap cleanup EXIT INT TERM

# Kill any previous process on port 8765
PID=$(lsof -ti :8765 2>/dev/null || true)
if [ -n "$PID" ]; then
  echo "Stopping previous session on port 8765 (PID: $PID)..."
  kill -9 "$PID" 2>/dev/null || true
  sleep 1
fi

# Kill any previous ollama serve processes
pkill -f "ollama serve" 2>/dev/null || true
sleep 1

# Find Python
PYTHON="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
fi
if [ ! -x "$PYTHON" ]; then
  echo "Python 3 is niet gevonden. Installeer Python via https://www.python.org/downloads/macos/"
  read -r -p "Druk op Enter om af te sluiten."
  exit 1
fi

# Find Ollama
OLLAMA="/opt/homebrew/bin/ollama"
if [ ! -x "$OLLAMA" ]; then
  OLLAMA="/usr/local/bin/ollama"
fi
if [ ! -x "$OLLAMA" ]; then
  echo "Ollama is niet gevonden. Download Ollama via https://ollama.com/download"
  read -r -p "Druk op Enter om af te sluiten."
  exit 1
fi

# Start Ollama in background
echo "Ollama wordt gestart..."
"$OLLAMA" serve > /dev/null 2>&1 &
OLLAMA_PID=$!
sleep 2

# Verify Ollama is ready
if ! kill -0 "$OLLAMA_PID" 2>/dev/null; then
  echo "Ollama kon niet worden gestart."
  exit 1
fi

# Start the Python app in foreground
"$PYTHON" app.py &
PYTHON_PID=$!
wait "$PYTHON_PID"
