#!/usr/bin/env bash
set -e

echo "Starting native Ollama server on macOS..."
# Start Ollama background daemon if not already running
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &
    sleep 3
fi

echo "Pulling recommended Qwen 2.5 7B model..."
ollama pull qwen2.5:7b

echo "Ollama is ready on http://127.0.0.1:11434"
