import pytest
from app.providers.registry import provider_registry
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.ollama import OllamaProvider
from app.providers.mlx import MLXProvider
from app.providers.llamacpp import LlamaCppProvider
from app.schemas.openai import ChatCompletionRequest, ChatMessage


def test_provider_registry():
    prov_mock = provider_registry.get_provider("openai_compatible", "http://127.0.0.1:8000/v1/_mock", "mock-fast")
    assert isinstance(prov_mock, OpenAICompatibleProvider)

    prov_ollama = provider_registry.get_provider("ollama", "http://127.0.0.1:11434", "qwen2.5:7b")
    assert isinstance(prov_ollama, OllamaProvider)

    prov_mlx = provider_registry.get_provider("mlx", "http://127.0.0.1:8081", "kimi-7b")
    assert isinstance(prov_mlx, MLXProvider)

    prov_llama = provider_registry.get_provider("llamacpp", "http://127.0.0.1:8082", "llama-8b")
    assert isinstance(prov_llama, LlamaCppProvider)


@pytest.mark.asyncio
async def test_mock_provider_execution():
    prov = provider_registry.get_provider("openai_compatible", "http://127.0.0.1:8000/v1/_mock", "mock-fast")
    req = ChatCompletionRequest(
        model="mock-fast",
        messages=[ChatMessage(role="user", content="Hello Mac M4")],
        stream=False,
    )
    resp = await prov.chat_completion(req)
    assert resp.choices[0].message.role == "assistant"
    assert "Mock response" in resp.choices[0].message.content

    is_healthy, status_str, lat = await prov.health_check()
    assert is_healthy is True
    assert "ONLINE" in status_str
