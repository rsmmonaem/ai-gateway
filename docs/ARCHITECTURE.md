# AI Model Gateway Architecture

The AI Model Gateway is a high-performance, private, OpenAI-compatible proxy designed specifically for Apple Silicon hardware (such as the **Mac mini M4**). It completely decouples external client applications from internal inference backends, unifying multiple local models behind a single public API endpoint, authenticated with API keys.

---

## High-Level Topology

```
                       INTERNET
                          │
                          ▼
            Cloudflare Tunnel (TLS 1.3)
           (Exposes ONLY port 8000 safely)
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

## Core Principles

### 1. Separation of Concerns
- **Client Facing**: Clients only see `https://api.yourdomain.com/v1`, using standard OpenAI SDKs with `sk-local-...` bearer keys. Internal network ports (`11434`, `8081`, `8082`), model paths, and backend architectures remain strictly private.
- **Inference Engines**: Inference engines run natively on macOS to maximize Apple Silicon Metal acceleration and unified memory bandwidth, while the gateway manages routing, rate limiting, and accounting.

### 2. Zero-Buffering Streaming (SSE)
- When a client issues `stream: true`, the gateway establishes an asynchronous HTTP streaming pipeline with the target model backend.
- Chunks are forwarded immediately to the client as Server-Sent Events (`data: {...}\n\n`).
- The gateway simultaneously accumulates token counts asynchronously to guarantee zero-latency token delivery while ensuring 100% accurate usage tracking.

### 3. Concurrency Protection for Unified Memory
- The Mac mini M4 shares memory between CPU and GPU. Over-subscribing concurrent inferences will cause memory paging (swap thrashing) and degrade token generation speed.
- The Gateway's `ConcurrencyManager` enforces global and per-model concurrent execution semaphores with a configurable queue timeout (`DEFAULT_QUEUE_TIMEOUT_SECONDS=30.0`).
- If saturated, it returns `503 Service Unavailable` with `Retry-After: 5` rather than dropping requests or crashing the server.

### 4. Privacy by Default
- Through `STORE_REQUEST_CONTENT=false`, prompts and model responses are never recorded in database tables or log files. Only metadata (duration, token count, status code, model slug) is stored.
