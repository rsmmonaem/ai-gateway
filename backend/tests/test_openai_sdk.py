import pytest


@pytest.mark.asyncio
async def test_openai_wire_compatibility(client, auth_headers):
    """
    Verifies that the gateway responses match the exact schema expected by the
    official OpenAI SDK (choices[0].message.content, usage fields, object names).
    """
    payload = {
        "model": "mock-fast",
        "messages": [{"role": "user", "content": "Tell me a joke"}],
        "temperature": 0.7,
        "max_tokens": 50,
    }

    resp = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    # Required OpenAI fields
    assert "id" in data
    assert data["object"] == "chat.completion"
    assert "created" in data
    assert "model" in data
    assert "choices" in data
    assert len(data["choices"]) > 0
    assert "message" in data["choices"][0]
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert "content" in data["choices"][0]["message"]
    assert "usage" in data
    assert "prompt_tokens" in data["usage"]
    assert "completion_tokens" in data["usage"]
    assert "total_tokens" in data["usage"]
