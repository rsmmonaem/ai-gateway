# Local Model & Quantization Guide (Apple Silicon M5 16 GB)

This guide covers model selection, quantization choices, and memory footprints for local open-source models running on an **Apple Silicon M5 machine with 16 GB Unified Memory**.

---

## Model Selection & Memory Matrix

| Model Alias | Target Backend | Model Tag / GGUF File | Quantization | Memory Footprint | Recommended Context |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `fast` | Ollama | `qwen2.5:7b` | Q4_K_M | ~5.1 GB | 8192 |
| `coding` | Ollama / MLX | `qwen2.5-coder:7b` | Q4_K_M | ~5.2 GB | 8192 |
| `reasoning` | llama-server | `qwen2.5-27b-instruct-q3_k_m.gguf` | **Q3_K_M** | **~11.8 GB** | **4096** |
| `vision` | Ollama | `qwen2-vl:7b` | Q4_K_M | ~5.5 GB | 4096 |
| `embedding` | Ollama | `nomic-embed-text` | FP16 | ~0.6 GB | 8192 |

---

## Qwen 27B Quantization on 16 GB Unified Memory

To run **Qwen 2.5 27B** on a 16 GB M5 machine alongside macOS system overhead (~3–4 GB RAM), aggressive quantization is required.

> [!IMPORTANT]
> **Recommended Quantization**: `Q3_K_M` GGUF.
> - **Size on disk**: ~11.8 GB
> - **Inference RAM**: Fits within the available 12 GB RAM window.
> - **Context window limit**: Keep context length set to `4096` tokens max to prevent KV-cache expansion from causing memory swap thrashing.

### Starting Qwen 27B via llama-server Metal:
```bash
llama-server \
  --host 127.0.0.1 \
  --port 8082 \
  -m ./models/qwen2.5-27b-instruct-q3_k_m.gguf \
  -c 4096 \
  --ngl 99
```

---

## Context Window KV-Cache Footprint

KV-Cache memory scales linearly with context length:
$$\text{KV Cache Memory} \approx 2 \times N_{\text{layers}} \times d_{\text{head}} \times N_{\text{heads}} \times \text{tokens} \times \text{bytes\_per\_element}$$

- For 7B models (8k tokens): ~1.0 GB KV cache
- For 27B models (4k tokens): ~1.8 GB KV cache

The AI Gateway enforces model-specific context budgets to guarantee stable, low-latency token generation on 16 GB RAM.
