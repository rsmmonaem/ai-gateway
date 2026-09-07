# Self-Hosted OpenRouter-Style AI Model Gateway (Mac mini M4)

A complete, production-grade, self-hosted AI model router and gateway designed for Apple Silicon (Mac mini M4). Unifies local models (Kimi 7B, Qwen 2.5 7B, Llama 3.1 8B, and MLX/GGUF models) behind a single OpenAI-compatible API endpoint with API key authentication, rate limiting, dynamic model routing, real-time SSE streaming, usage tracking, and secure public exposure through Cloudflare Tunnel.

---

## Key Features

- **OpenAI-Compatible API**: Works out-of-the-box with the official OpenAI Python & JS SDKs, LangChain, LlamaIndex, Cursor, and any OpenAI client (`/v1/models`, `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`).
- **Apple Silicon Optimized (M4)**: Decouples the gateway from inference engines. Backends run natively with Metal GPU acceleration and Unified Memory bandwidth.
- **Multi-Backend Provider Adapters**:
  - **MLX-LM**: Native Apple MLX server (`mlx_lm.server`) for Kimi 7B and fast quantized models.
  - **Ollama**: Native macOS Ollama server for Qwen 2.5 7B, Llama 3.1 8B, etc.
  - **llama.cpp**: `llama-server` compiled with Metal support for GGUF models.
  - **OpenAI-Compatible**: Universal adapter for any OpenAI-compatible server.
- **API Key System**: Full lifecycle API keys (`sk-local-...`). Raw keys are never stored in the database; verified securely via HMAC-SHA256.
- **Concurrency & Queue Management**: Protects Unified Memory and prevents GPU thrashing on Mac mini M4.
- **Dynamic Model Routing**: Exact slug routing (`kimi-7b`), alias routing (`kimi`), and `auto` routing.
- **Non-Buffering SSE Streaming**: True real-time token streaming with simultaneous token metering.
- **Web Dashboard**: Modern SPA with Admin Controls, Metrics Overview, Model Registry, Key Management, and Interactive Chat Playground.
- **Command-Line Interface (CLI)**: `ai-gateway` CLI for administrative automation.
- **Cloudflare Tunnel Ready**: Keep the Mac mini safely behind your firewall while exposing only the gateway publicly.

---

## Architecture

```
                       INTERNET
                          │
                          ▼
            Cloudflare Tunnel (TLS 1.3)
                          │
                          ▼
        ┌───────────────────────────────────┐
        │        AI Model Gateway           │
        │   FastAPI / Uvicorn (Port 8000)   │
        └─┬───────────────┬───────────────┬─┘
          │               │               │
    Authentication   Rate Limiter    Model Router
    (SHA-256 HMAC)   (Sliding Win)   & Load Balancer
          │               │               │
          └───────────────┼───────────────┘
                          │
           Semaphore Concurrency Queue
           (Protects Unified Memory & GPU)
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   [MLX-LM Server]  [Ollama Server]  [llama-server Metal]
     Port 8081        Port 11434        Port 8082
      Kimi 7B          Qwen 7B           Llama 8B
        │                 │                 │
        └─────────────────┼─────────────────┘
                          │
                          ▼
             macOS Metal Unified Memory
```

---

## Quick Start

### 1. One-Click macOS Setup
```bash
git clone <repo-url> ai-gateway
cd ai-gateway

# Installs runtimes, python venv, and bootstraps DB
make setup
```

### 2. Start the AI Gateway
```bash
make run
```
Open your browser at **`http://localhost:8000`** to access the Web Dashboard and interactive playground.

### 3. Launch Local Inference Backends (Native macOS)
In separate terminal windows:
```bash
# Launch Kimi 7B via Apple MLX-LM
make run-kimi

# Launch Qwen 2.5 7B via Ollama
make run-ollama
```

---

## Using with OpenAI Python SDK

```python
from openai import OpenAI

# Connect to your Mac mini M4 Gateway
client = OpenAI(
    base_url="http://localhost:8000/v1",  # Or https://api.yourdomain.com/v1
    api_key="sk-local-xxxxxxxxxxxxxxxx"
)

# Call Kimi 7B with real-time streaming
response = client.chat.completions.create(
    model="kimi-7b",
    messages=[
        {"role": "system", "content": "You are an expert AI assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ],
    stream=True
)

for chunk in response:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="", flush=True)
print()
```

---

## CLI Administration

Manage the gateway directly from your terminal:

```bash
# Health check of all backends
ai-gateway health

# List models
ai-gateway model list

# Test a model backend
ai-gateway model test kimi-7b

# Create and list users
ai-gateway user create --email dev@local.test --name "Developer" --role user
ai-gateway user list

# Create a new API key for a user
ai-gateway key create --email dev@local.test --name "Prod Key" --rpm 120

# Revoke a key
ai-gateway key revoke 1
```

---

## Cloudflare Tunnel Setup

To expose the gateway securely to the internet:
```bash
./infrastructure/cloudflare/setup-tunnel.sh
```
Follow the interactive prompts to authenticate and bind `api.yourdomain.com` to `http://127.0.0.1:8000`.

---

## Running with Docker Compose (PostgreSQL & Redis)

If you prefer containerized PostgreSQL and Redis for production:
```bash
make docker-up
```

---

## Verification & Tests

```bash
make test
```

---

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Mac mini M4 Setup & Hardware Tuning](docs/MAC_M4_SETUP.md)
- [Model Guide & Quantization](docs/MODEL_GUIDE.md)
- [API Reference](docs/API_REFERENCE.md)
- [Cloudflare Tunnel Guide](docs/CLOUDFLARE_TUNNEL.md)
