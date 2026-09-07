# Local Model Guide for Apple Silicon M4

This guide covers model selection, quantization, and memory footprints for common open-source models running on the Mac mini M4.

---

## Model Selection Matrix

### 1. Moonshot Kimi 7B
- **Recommended Backend**: MLX-LM (`python -m mlx_lm.server`)
- **Recommended Quantization**: 4-bit (`mlx-community/Kimi-7B-Instruct-4bit`)
- **VRAM Footprint**: ~4.8 GB
- **Context Length**: 32,768 tokens
- **Strengths**: Strong reasoning, bilingual Chinese/English comprehension, long-context attention.

### 2. Alibaba Qwen 2.5 7B
- **Recommended Backend**: Ollama (`ollama pull qwen2.5:7b`)
- **Recommended Quantization**: Q4_K_M
- **VRAM Footprint**: ~5.1 GB
- **Context Length**: 32,768 tokens (up to 128k supported)
- **Strengths**: Top-tier coding, mathematics, and structured JSON output.

### 3. Meta Llama 3.1 8B
- **Recommended Backend**: Ollama (`ollama pull llama3.1:8b`) or llama-server Metal
- **Recommended Quantization**: Q4_K_M (`Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf`)
- **VRAM Footprint**: ~5.5 GB
- **Context Length**: 131,072 tokens
- **Strengths**: General conversation, tool calling, and high instruction obedience.

---

## Quantization Guide

| Precision | Bits/Weight | Quality Retention | Memory (7B Model) | Generation Speed |
| :--- | :--- | :--- | :--- | :--- |
| **FP16** | 16 | 100% | ~14.5 GB | Slow on 16GB RAM |
| **Q8_0** | 8 | 99.8% | ~7.8 GB | Moderate |
| **Q4_K_M / 4-bit** | 4.5 | 98.9% | ~4.8 GB - 5.2 GB | **Fastest on M4** (Recommended) |

---

## Context Window Memory Footprint

KV-Cache memory scales linearly with context length:
$$\text{KV Memory} \approx 2 \times \text{layers} \times \text{heads} \times \text{head\_dim} \times \text{precision} \times \text{tokens}$$

For a 7B model at 16-bit KV cache:
- 4k tokens: ~0.5 GB
- 16k tokens: ~2.0 GB
- 32k tokens: ~4.0 GB

Keep default context limits configured in the gateway to prevent runaway memory allocation.
