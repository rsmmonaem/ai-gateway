# API Reference

The AI Model Gateway exposes standard OpenAI-compatible endpoints. Any OpenAI SDK or compatible client library works without modification.

Base URL:
- Local: `http://localhost:8000/v1`
- Cloudflare Tunnel: `https://api.yourdomain.com/v1`

---

## Authentication

Include your gateway API key in the `Authorization` header:
```http
Authorization: Bearer sk-local-xxxxxxxxxxxxxxxx
```

---

## 1. List Models

### Request
```http
GET /v1/models
Authorization: Bearer sk-local-xxxxxxxxxxxxxxxx
```

### Response
```json
{
  "object": "list",
  "data": [
    {
      "id": "kimi-7b",
      "object": "model",
      "created": 1710000000,
      "owned_by": "local-mlx",
      "context_length": 32768,
      "description": "Moonshot Kimi 7B running on Apple Silicon MLX-LM with Metal acceleration."
    },
    {
      "id": "qwen-7b",
      "object": "model",
      "created": 1710000000,
      "owned_by": "local-ollama",
      "context_length": 32768,
      "description": "Alibaba Qwen 2.5 7B model running natively via Ollama on macOS."
    }
  ]
}
```

---

## 2. Chat Completions

### Non-Streaming Request
```bash
curl https://api.yourdomain.com/v1/chat/completions \
  -H "Authorization: Bearer sk-local-xxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kimi-7b",
    "messages": [
      {"role": "user", "content": "Explain unified memory in two sentences."}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

### Streaming Request (SSE)
```bash
curl -N https://api.yourdomain.com/v1/chat/completions \
  -H "Authorization: Bearer sk-local-xxxxxxxxxxxxxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-7b",
    "messages": [
      {"role": "user", "content": "Write a Python function to check for prime numbers."}
    ],
    "stream": true
  }'
```

---

## 3. Official OpenAI Python SDK Example

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://api.yourdomain.com/v1",
    api_key="sk-local-xxxxxxxxxxxxxxxx"
)

response = client.chat.completions.create(
    model="kimi-7b",
    messages=[
        {"role": "user", "content": "Hello!"}
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

## Error Handling

Standard HTTP status codes and OpenAI error structures:

| Status | Code | Description |
| :--- | :--- | :--- |
| `400` | `invalid_request_error` | Malformed JSON or invalid parameters |
| `401` | `invalid_api_key` | Missing, incorrect, or expired API key |
| `403` | `model_permission_denied` | User lacks access to this specific model |
| `404` | `model_not_found` | Requested model or alias does not exist |
| `429` | `rate_limit_exceeded` | Requests per minute (RPM) or token quota exceeded |
| `503` | `gateway_busy` | Inference queue saturated; retry after delay |
| `504` | `backend_timeout` | Downstream inference engine timed out |
