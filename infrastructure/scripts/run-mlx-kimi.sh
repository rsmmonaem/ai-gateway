#!/usr/bin/env bash
set -e

# Model can be 4-bit quantized Kimi 7B or any MLX-compatible repository
MODEL_ID="${1:-mlx-community/Kimi-7B-Instruct-4bit}"
PORT="${2:-8081}"

echo "Starting Apple MLX-LM server with Metal acceleration..."
echo "Model: $MODEL_ID"
echo "Port:  $PORT (http://127.0.0.1:$PORT)"

# Run MLX server with native OpenAI compatibility
python3 -m mlx_lm.server \
    --model "$MODEL_ID" \
    --port "$PORT" \
    --host "127.0.0.1"
