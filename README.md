# Universal Local AI Gateway (Apple Silicon M5, 16 GB Unified Memory)

A complete, production-grade, self-hosted universal AI model router and gateway optimized for **Apple Silicon M5 (16 GB Unified Memory)**. Unifies local models served via **Ollama (0.34.0)**, **llama.cpp / llama-server (Metal GGUF)**, and **MLX-LM** behind a single, high-performance OpenAI-compatible API endpoint.

---

## Architecture

```mermaid
flowchart TD
    Client[Client / OpenAI SDK] --> API[OpenAI-Compatible API<br/>:8000]
    API --> Auth[HMAC SHA-256 Auth & Rate Limiter]
    Auth --> Router[Universal Smart Router<br/>Zero-LLM Classifier]
    
    subgraph Routing ["Universal Model Aliases"]
        Router --> |simple / fast| Fast[Fast Alias: Qwen 2.5 7B]
        Router --> |code / syntax| Coder[Coding Alias: Qwen 2.5 Coder 7B]
        Router --> |math / logic| Heavy[Reasoning Alias: Qwen 27B Q3 GGUF]
        Router --> |images| Vis[Vision Alias: Qwen 2 VL]
    end

    subgraph MemoryQueue ["16 GB Concurrency Queue"]
        Fast --> OllamaSem[Ollama Semaphore: max 2]
        Coder --> OllamaSem
        Heavy --> LlamaSem[llama-server Semaphore: max 1]
        Vis --> OllamaSem
    end

    subgraph Backends ["Local Inference Backends"]
        OllamaSem --> Ollama[Ollama Server<br/>127.0.0.1:11434]
        LlamaSem --> LlamaServer[llama-server Metal<br/>127.0.0.1:8082]
    end

    Ollama --> Metal[Apple Silicon M5 GPU & Unified Memory]
    LlamaServer --> Metal
```

---

## Key Features

- **Universal Model Alias (`model: "universal"`)**: Automatic, zero-LLM request classification routing queries to `fast`, `coding`, `reasoning`, or `vision` models based on content features.
- **OpenAI API Compatibility**: Full compliance with OpenAI wire spec (`/v1/chat/completions`, `/v1/models`, `/v1/completions`, `/v1/embeddings`).
- **Memory-Aware 16 GB Allocation**: Protects Apple M5 Unified Memory from RAM exhaustion using bounded context limits (e.g. 4096 tokens for Qwen 27B Q3 GGUF) and per-backend concurrency semaphores.
- **Multi-Backend Provider System**:
  - **Ollama (0.34.0)** (`127.0.0.1:11434`)
  - **llama.cpp / llama-server** (`127.0.0.1:8082`)
  - **MLX-LM** (`127.0.0.1:8081`)
  - **OpenAI-Compatible** (Universal HTTP adapter)
- **Resilience & Bounded Retries**: Retries failed backend connections with exponential backoff & jitter, automatically failing over to healthy secondary providers.
- **Non-Buffering SSE Streaming**: True real-time Server-Sent Events token streaming with concurrent token metering.
- **Built-In Benchmarking Utility**: Measure TTFT (Time To First Token), TPS (Tokens/sec), and total latency using `make benchmark`.

---

## Model Strategy for Apple M5 (16 GB RAM)

| Model Alias | Target Backend | Model Specs | Context Budget | Task Profile |
| :--- | :--- | :--- | :--- | :--- |
| `universal` | Gateway Router | Smart Classification | 8192 | Automatic task routing |
| `fast` | Ollama | Qwen 2.5 7B Q4 | 8192 | Fast everyday Q&A |
| `coding` | Ollama / MLX | Qwen 2.5 Coder 7B | 8192 | Software development & code refactoring |
| `reasoning` | llama-server | Qwen 27B Q3_K_M GGUF | 4096 | Complex math, proofs & architecture |
| `vision` | Ollama | Qwen 2 VL 7B | 4096 | Multimodal image understanding |
| `embedding` | Ollama | Nomic Embed Text | 8192 | Vector embeddings |

---

## Quick Start

### 1. Installation
```bash
git clone https://github.com/rsmmonaem/ai-gateway.git
cd ai-gateway
make setup
```

### 2. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 3. Start Inference Engine Backends
In separate terminal windows:

#### Ollama (0.34.0)
```bash
ollama serve
ollama pull qwen2.5:7b
ollama pull qwen2.5-coder:7b
```

#### llama-server (Qwen 27B Q3 GGUF for Heavy Reasoning)
Download `qwen2.5-27b-instruct-q3_k_m.gguf` and start:
```bash
llama-server --host 127.0.0.1 --port 8082 -m ./models/qwen2.5-27b-instruct-q3_k_m.gguf -c 4096 --ngl 99
```

### 4. Start AI Gateway
```bash
make run
```
Gateway will run at `http://127.0.0.1:8000`.

---

## Usage Examples

### 1. Universal Smart Routing (cURL)
```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-local-testkey123456" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "universal",
    "messages": [
      {
        "role": "user",
        "content": "Design a scalable Laravel SaaS architecture with Redis queues."
      }
    ],
    "stream": true
  }'
```

### 2. OpenAI Python SDK
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="sk-local-testkey123456"
)

# Use smart universal routing
response = client.chat.completions.create(
    model="universal",
    messages=[
        {"role": "system", "content": "You are a senior software architect."},
        {"role": "user", "content": "Write a Python binary search function with tests."}
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

## Benchmarking

Run performance benchmarks against the gateway measuring TTFT (Time To First Token), throughput (TPS), and total latency:

```bash
make benchmark
```

Options:
```bash
cd backend && .venv/bin/python scripts/benchmark.py --model universal --iterations 5
```

---

## Verification & Testing

Run the automated pytest test suite:
```bash
make test
```

---

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Model & Quantization Guide](docs/MODEL_GUIDE.md)
