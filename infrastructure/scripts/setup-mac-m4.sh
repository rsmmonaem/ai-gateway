#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " Mac mini M4 - AI Model Gateway & Inference Setup"
echo "=========================================================="

# 1. Check for Apple Silicon
ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    echo "Warning: Expected arm64 (Apple Silicon), detected $ARCH."
fi

# 2. Check Xcode Command Line Tools
if ! xcode-select -p &>/dev/null; then
    echo "Installing Xcode Command Line Tools..."
    xcode-select --install
    echo "Please finish the Apple developer prompt and rerun this script."
    exit 1
fi

# 3. Check Homebrew
if ! command -v brew &>/dev/null; then
    echo "Installing Homebrew..."
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi

# 4. Install Runtime Dependencies via Brew
echo "Installing Python 3.11, Ollama, and Cloudflared..."
brew install python@3.11 ollama cloudflared postgresql@16 redis || true

# 5. Setup Python Virtual Environment for Gateway
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR/backend"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment at backend/.venv..."
    /opt/homebrew/bin/python3.11 -m venv .venv || python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
echo "Installing gateway dependencies..."
pip install -r requirements.txt

# 6. Install Apple MLX & MLX-LM with Metal acceleration
echo "Installing Apple MLX and MLX-LM..."
pip install mlx mlx-lm

# 7. Initialize Gateway Database
echo "Bootstrapping AI Gateway database & initial admin user..."
python3 -m app.cli init

echo ""
echo "=========================================================="
echo " Setup Complete!"
echo " Start Gateway:   make run"
echo " Start Kimi 7B:   ./infrastructure/scripts/run-mlx-kimi.sh"
echo " Start Ollama:    ./infrastructure/scripts/run-ollama.sh"
echo "=========================================================="
