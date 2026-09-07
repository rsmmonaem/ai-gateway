# Mac mini M4 Hardware & Inference Setup Guide

This guide details configuring an Apple Silicon **Mac mini M4** to serve local models with maximum throughput.

---

## 1. Unified Memory Profiles

Apple Silicon Unified Memory is dynamically allocated between macOS, the CPU, and the Metal GPU:

| RAM Config | Recommended Model Configuration | Concurrency |
| :--- | :--- | :--- |
| **16 GB Unified** | 1x 7B 4-bit model loaded (e.g. Kimi 7B 4-bit or Qwen 2.5 7B Q4_K_M) | 1 - 2 streams |
| **24 GB Unified** | 2x 7B 4-bit models simultaneously, OR 1x 14B model (Q4) | 2 - 4 streams |
| **32 GB+ Unified** | Multiple 7B/8B models loaded concurrently, OR 1x 32B model (Q4) | 4 - 8 streams |

---

## 2. Setting Up macOS Prerequisites

### Step 1: Install Xcode Command Line Tools
Open Terminal on your Mac mini M4:
```bash
xcode-select --install
```
Click "Install" on the Apple prompt and wait for the download to complete.

### Step 2: Install Homebrew
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### Step 3: Install Core Runtimes
```bash
brew install python@3.11 ollama cloudflared postgresql@16 redis
```

---

## 3. Running Model Inference Engines Natively

> [!IMPORTANT]
> **Always run inference engines directly on macOS**, not inside a Docker container! Docker for Mac uses a virtual machine hypervisor which limits Metal GPU hardware access.

### Backend 1: Apple MLX-LM (Optimized for Kimi 7B)
```bash
pip3.11 install mlx mlx-lm

# Launch MLX server with Metal acceleration
python3.11 -m mlx_lm.server \
    --model mlx-community/Kimi-7B-Instruct-4bit \
    --port 8081 \
    --host 127.0.0.1
```

### Backend 2: Ollama (Optimized for Qwen 2.5 7B & Llama 3.1 8B)
```bash
# Start Ollama service
ollama serve &

# Pull models
ollama pull qwen2.5:7b
ollama pull llama3.1:8b
```
Ollama is now reachable on `http://127.0.0.1:11434`.

---

## 4. Launching the AI Gateway

```bash
cd ai-gateway

# Setup virtual environment and dependencies
make setup

# Run the gateway locally
make run
```
Open your browser at `http://localhost:8000` to access the Web Dashboard.
