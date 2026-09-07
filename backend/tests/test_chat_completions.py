import pytest


@pytest.mark.asyncio
async def test_chat_completion_non_streaming(client, auth_headers):
    payload = {
        "model": "mock-fast",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello from pytest!"},
        ],
        "temperature": 0.7,
        "stream": False,
    }

    resp = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["object"] == "chat.completion"
    assert data["model"] == "mock-fast"
    assert len(data["choices"]) == 1
    choice = data["choices"][0]
    assert choice["message"]["role"] == "assistant"
    assert len(choice["message"]["content"]) > 0
    assert choice["finish_reason"] == "stop"

    # Token metering assertion
    assert "usage" in data
    assert data["usage"]["prompt_tokens"] > 0
    assert data["usage"]["completion_tokens"] > 0
    assert data["usage"]["total_tokens"] == (
        data["usage"]["prompt_tokens"] + data["usage"]["completion_tokens"]
    )


@pytest.mark.asyncio
async def test_chat_completion_alias_routing(client, auth_headers):
    # 'mock' is registered as an alias for 'mock-fast'
    payload = {
        "model": "mock",
        "messages": [{"role": "user", "content": "Testing alias routing"}],
        "stream": False,
    }
    resp = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "choices" in data


@pytest.mark.asyncio
async def test_chat_completion_auto_routing(client, auth_headers):
    # 'auto' routes to the highest-priority enabled model
    payload = {
        "model": "auto",
        "messages": [{"role": "user", "content": "Testing auto routing"}],
        "stream": False,
    }
    resp = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "choices" in data


@pytest.mark.asyncio
async def test_chat_completion_unknown_model(client, auth_headers):
    payload = {
        "model": "non-existent-70b",
        "messages": [{"role": "user", "content": "Hi"}],
    }
    resp = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"]["code"] == "model_not_found"
