import time
from typing import Optional, Tuple
import httpx
from app.providers.openai_compatible import OpenAICompatibleProvider


class LlamaCppProvider(OpenAICompatibleProvider):
    """
    Adapter for llama-server (llama.cpp compiled with Apple Metal support).
    Natively supports high-performance quantized GGUF models on Apple Silicon.
    """

    async def health_check(self) -> Tuple[bool, str, Optional[float]]:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"{self.endpoint}/health")
                latency = round((time.time() - start) * 1000, 2)
                if resp.status_code == 200:
                    status_text = resp.json().get("status", "ok")
                    return True, f"ONLINE ({status_text})", latency
        except Exception:
            pass
        return False, "OFFLINE", None
