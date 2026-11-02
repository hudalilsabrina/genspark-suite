#!/bin/bash
set -e

echo "=========================================================="
echo "      Genspark Suite Auto-Installer & Setup Script        "
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[1/4] Checking and installing system dependencies (APT)..."
which apt-get >/dev/null 2>&1 && {
    sudo apt-get update -y || apt-get update -y
    sudo apt-get install -y ffmpeg libgl1 libglib2.0-0 python3-venv python3-pip curl || apt-get install -y ffmpeg libgl1 libglib2.0-0 python3-venv python3-pip curl
} || echo "[!] Non-Debian system; skipping apt-get."

echo "[2/4] Setting up dedicated Python Virtual Environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "[+] Virtualenv created at $SCRIPT_DIR/.venv"
fi

echo "[3/4] Installing Python dependencies into .venv..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install \
    curl_cffi \
    aiohttp \
    onnxruntime \
    ddddocr \
    faster-whisper \
    numpy \
    Pillow \
    opencv-python-headless

# Install unofficial genspark-py for web chat relay
.venv/bin/pip install "git+https://github.com/SharpWizard/genspark-py.git" || true

echo "[4/4] Verifying critical modules..."
.venv/bin/python -c "
import _cffi_backend
from curl_cffi import requests as cr
import aiohttp
import onnxruntime
import ddddocr
import genspark
print('[+] All dependencies verified successfully!')
"

echo "=========================================================="
echo "    Setup Complete! You can now run: ./run.sh farm -n 10  "
echo "=========================================================="
