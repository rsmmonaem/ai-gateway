from typing import Dict, Type
from app.providers.base import InferenceProvider
from app.providers.llamacpp import LlamaCppProvider
from app.providers.mlx import MLXProvider
from app.providers.ollama import OllamaProvider
from app.providers.openai_compatible import OpenAICompatibleProvider


class ProviderRegistry:
    """Factory creating the appropriate provider instance for each model backend."""

    _BACKENDS: Dict[str, Type[InferenceProvider]] = {
        "mlx": MLXProvider,
        "ollama": OllamaProvider,
        "llamacpp": LlamaCppProvider,
        "openai_compatible": OpenAICompatibleProvider,
    }

    @classmethod
    def get_provider(
        cls,
        backend: str,
        endpoint: str,
        model_name: str,
        timeout: float = 300.0,
    ) -> InferenceProvider:
        provider_cls = cls._BACKENDS.get(backend.lower(), OpenAICompatibleProvider)
        return provider_cls(endpoint=endpoint, model_name=model_name, timeout=timeout)


provider_registry = ProviderRegistry()
