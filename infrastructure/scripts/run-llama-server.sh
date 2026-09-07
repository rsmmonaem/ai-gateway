#!/usr/bin/env bash
set -e

MODEL_PATH="${1:-models/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf}"
PORT="${2:-8082}"

if ! command -v llama-server &> /dev/null; then
    echo "llama-server not found in PATH."
    echo "Install via Homebrew: 'brew install llama.cpp'"
    exit 1
fi

echo "Starting llama-server with Metal GPU acceleration on port $PORT..."
llama-server \
    -m "$MODEL_PATH" \
    --port "$PORT" \
    --host "127.0.0.1" \
    -ngl 99 \
    -c 32768
