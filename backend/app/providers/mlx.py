import time
from typing import Optional, Tuple
import httpx
from app.providers.openai_compatible import OpenAICompatibleProvider


class MLXProvider(OpenAICompatibleProvider):
    """
    Adapter for Apple MLX-LM server (`python -m mlx_lm.server`) running natively on Apple Silicon.
    Natively supports OpenAI-compatible chat completions with Metal GPU hardware acceleration.
    """

    async def health_check(self) -> Tuple[bool, str, Optional[float]]:
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                resp = await client.get(f"{self.endpoint}/v1/models")
                latency = round((time.time() - start) * 1000, 2)
                if resp.status_code == 200:
                    return True, "ONLINE (MLX Metal)", latency
        except Exception:
            pass
        return False, "OFFLINE", None
