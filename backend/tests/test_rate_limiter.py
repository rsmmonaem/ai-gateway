import pytest


@pytest.mark.asyncio
async def test_rate_limiting_enforcement(client):
    headers = {"Authorization": "Bearer sk-local-lowlimit"}
    payload = {
        "model": "mock-fast",
        "messages": [{"role": "user", "content": "ping"}],
    }

    # Our low-limit key in conftest.py has rate_limit_rpm = 3
    responses = []
    for _ in range(5):
        resp = await client.post("/v1/chat/completions", json=payload, headers=headers)
        responses.append(resp.status_code)

    # First 3 should succeed (200), subsequent requests should be 429
    assert 200 in responses
    assert 429 in responses
    last_resp = await client.post("/v1/chat/completions", json=payload, headers=headers)
    assert last_resp.status_code == 429
    assert "Retry-After" in last_resp.headers
    assert last_resp.json()["error"]["code"] == "rate_limit_exceeded"
