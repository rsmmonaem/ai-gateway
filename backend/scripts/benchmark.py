#!/usr/bin/env python3
import asyncio
import json
import time
import urllib.request
import urllib.error
import sys
import argparse

DEFAULT_BASE_URL = "http://127.0.0.1:8000/v1"
DEFAULT_API_KEY = "sk-local-test"


def run_benchmark(base_url: str, api_key: str, model_alias: str, iterations: int = 5):
    print("=" * 70)
    print(f"🚀 AI Gateway Benchmark Utility (Apple Silicon M5 16 GB)")
    print(f"Target Gateway: {base_url}")
    print(f"Target Model:   {model_alias}")
    print(f"Iterations:     {iterations}")
    print("=" * 70)

    url = f"{base_url}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    test_prompts = [
        "Write a Python function to compute the Fibonacci sequence using memoization.",
        "Explain the architectural trade-offs between monolithic and microservice architectures.",
        "What is the difference between synchronous and asynchronous I/O in high-performance networking?",
        "Design a REST API schema for a multi-tenant SaaS application.",
        "Summarize quantum entanglement and quantum teleportation in 3 bullet points."
    ]

    latencies = []
    ttfts = []
    tps_list = []
    success_count = 0

    for i in range(iterations):
        prompt = test_prompts[i % len(test_prompts)]
        payload = {
            "model": model_alias,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "max_tokens": 150,
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        t0 = time.time()
        ttft = None
        tokens_received = 0
        success = False

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                first_token = True
                for line in response:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: ") and not line_str.startswith("data: [DONE]"):
                        if first_token:
                            ttft = (time.time() - t0) * 1000
                            first_token = False
                        try:
                            chunk = json.loads(line_str[6:])
                            choices = chunk.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                if delta.get("content"):
                                    tokens_received += 1
                        except Exception:
                            pass
                total_latency = (time.time() - t0) * 1000
                success = True

        except urllib.error.HTTPError as e:
            total_latency = (time.time() - t0) * 1000
            print(f"  [Iter {i+1}] HTTP Error: {e.code} - {e.reason}")
        except Exception as e:
            total_latency = (time.time() - t0) * 1000
            print(f"  [Iter {i+1}] Connection Error: {e}")

        if success:
            success_count += 1
            latencies.append(total_latency)
            if ttft is not None:
                ttfts.append(ttft)
            gen_duration_sec = (total_latency - (ttft or 0)) / 1000.0
            tps = (tokens_received / gen_duration_sec) if gen_duration_sec > 0 else 0
            tps_list.append(tps)

            print(f"  [Iter {i+1}] Success | TTFT: {ttft:.1f}ms | Total Latency: {total_latency:.1f}ms | Tokens: {tokens_received} | TPS: {tps:.1f} tok/s")
        else:
            print(f"  [Iter {i+1}] Failed | Duration: {total_latency:.1f}ms")

    print("-" * 70)
    print("📊 BENCHMARK RESULTS SUMMARY:")
    print(f"  Total Attempts:  {iterations}")
    print(f"  Success Rate:    {(success_count/iterations)*100:.1f}%")
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        avg_ttft = (sum(ttfts) / len(ttfts)) if ttfts else 0
        avg_tps = (sum(tps_list) / len(tps_list)) if tps_list else 0
        print(f"  Avg TTFT:        {avg_ttft:.1f} ms")
        print(f"  Avg Total Latency:{avg_lat:.1f} ms")
        print(f"  Avg Throughput:  {avg_tps:.1f} tokens/sec")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Gateway Benchmark Script")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="Gateway base URL")
    parser.add_argument("--key", default=DEFAULT_API_KEY, help="API Key")
    parser.add_argument("--model", default="universal", help="Model alias (universal, fast, coding, reasoning, mock-fast)")
    parser.add_argument("--iterations", type=int, default=5, help="Number of benchmark iterations")
    args = parser.parse_args()

    run_benchmark(base_url=args.url, api_key=args.key, model_alias=args.model, iterations=args.iterations)
