# Anthropic Claude API Integration Guide

The AI Model Gateway running on your **Mac mini M4** natively supports the **Anthropic Messages API specification** (`/v1/messages`).

You can use the official **Anthropic Python SDK**, **Anthropic TypeScript SDK**, **Claude Desktop**, **Claude Code**, **Cursor**, or any Anthropic-compatible tool directly with your private gateway.

---

## 1. Quick Connection Details

| Configuration Parameter | Value |
| :--- | :--- |
| **Anthropic Base URL** | `https://agnes.jobab.chat` *(or `https://agnes.jobab.chat/v1`)* |
| **Local Base URL** | `http://localhost:8000` *(or `http://localhost:8000/v1`)* |
| **API Key Header** | `x-api-key: sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57` |
| **Standard Bearer Header** | `Authorization: Bearer sk-local-...` *(also accepted)* |
| **Version Header** | `anthropic-version: 2023-06-01` |
| **Supported Models** | `kimi-7b`, `qwen-7b`, `llama-8b`, `mock-fast`, `auto` |
| **Claude Model Aliases** | `claude-3-5-sonnet`, `claude-3-opus`, `claude-3-haiku` *(auto-routed to top model)* |

---

## 2. Python (Official `anthropic` SDK)

Install the official package:
```bash
pip install anthropic
```

### Basic Chat Completion
```python
import anthropic

client = anthropic.Anthropic(
    base_url="https://agnes.jobab.chat",
    api_key="sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57",
)

message = client.messages.create(
    model="kimi-7b",
    max_tokens=1024,
    system="You are an expert software engineer running locally on Apple Silicon Metal.",
    messages=[
        {"role": "user", "content": "How does unified memory accelerate AI inference on the Mac mini M4?"}
    ],
)

print(message.content[0].text)
```

### Real-Time Streaming (SSE)
```python
import anthropic

client = anthropic.Anthropic(
    base_url="https://agnes.jobab.chat",
    api_key="sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57",
)

with client.messages.stream(
    model="kimi-7b",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a fast Python async queue demonstration."}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
print()
```

---

## 3. TypeScript / Node.js (Official `@anthropic-ai/sdk`)

Install the official package:
```bash
npm install @anthropic-ai/sdk
```

### TypeScript Example
```typescript
import Anthropic from "@anthropic-ai/sdk";

const anthropic = new Anthropic({
  baseURL: "https://agnes.jobab.chat",
  apiKey: "sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57",
});

async function main() {
  const stream = await anthropic.messages.create({
    model: "kimi-7b",
    max_tokens: 1024,
    system: "You are a helpful AI assistant.",
    messages: [{ role: "user", content: "Explain quantum computing in 3 bullet points." }],
    stream: true,
  });

  for await (const messageStreamEvent of stream) {
    if (
      messageStreamEvent.type === "content_block_delta" &&
      messageStreamEvent.delta.type === "text_delta"
    ) {
      process.stdout.write(messageStreamEvent.delta.text);
    }
  }
  console.log();
}

main();
```

---

## 4. cURL / REST API

### Non-Streaming
```bash
curl -X POST https://agnes.jobab.chat/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "kimi-7b",
    "max_tokens": 1024,
    "system": "You are a concise AI assistant.",
    "messages": [
      {"role": "user", "content": "Say hello!"}
    ]
  }'
```

### Streaming (SSE)
```bash
curl -N -X POST https://agnes.jobab.chat/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "kimi-7b",
    "max_tokens": 512,
    "stream": true,
    "messages": [
      {"role": "user", "content": "Count from 1 to 5"}
    ]
  }'
```

---

## 5. Third-Party Tool Configurations

### A. Claude Code CLI
You can point the official `claude` CLI directly to your private gateway:
```bash
export ANTHROPIC_BASE_URL="https://agnes.jobab.chat"
export ANTHROPIC_API_KEY="sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57"
claude
```

### B. Cursor IDE
1. Open **Cursor Settings** > **Models**.
2. Under **OpenAI API Key** or **Anthropic API Key**:
   - Set Base URL: `https://agnes.jobab.chat/v1`
   - API Key: `sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57`
3. Add model name: `kimi-7b` (or `qwen-7b`, `llama-8b`).

### C. Claude Desktop App
Open `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {},
  "environmentVariables": {
    "ANTHROPIC_BASE_URL": "https://agnes.jobab.chat",
    "ANTHROPIC_API_KEY": "sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57"
  }
}
```

### D. LiteLLM Proxy / Router
```yaml
model_list:
  - model_name: kimi-7b
    litellm_params:
      model: anthropic/kimi-7b
      api_base: https://agnes.jobab.chat
      api_key: sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57
```

### E. Continue.dev (VS Code / JetBrains)
In `~/.continue/config.json`:
```json
{
  "models": [
    {
      "title": "Kimi 7B (Mac mini M4)",
      "provider": "anthropic",
      "model": "kimi-7b",
      "apiBase": "https://agnes.jobab.chat",
      "apiKey": "sk-local-4fe3605bf7939a421eadc54816d3c7e2d038e07fb4892b57"
    }
  ]
}
```

---

## 6. Model Aliasing & Auto-Routing

When external tools request Claude model identifiers, the gateway automatically aliases them to your local models:

| Requested Model | Internal Routing Target | Acceleration |
| :--- | :--- | :--- |
| `kimi-7b` *(or `kimi`)* | Moonshot Kimi 7B | Metal GPU / Ollama |
| `qwen-7b` *(or `qwen`)* | Alibaba Qwen 2.5 7B | Metal GPU / Ollama |
| `llama-8b` *(or `llama`)* | Meta Llama 3.1 8B | Metal GPU / Ollama |
| `claude-3-5-sonnet` | Auto-routed to highest priority local model | Metal GPU |
| `claude-3-opus` | Auto-routed to highest priority local model | Metal GPU |
| `auto` | Dynamic least-latency active model | Metal GPU |
