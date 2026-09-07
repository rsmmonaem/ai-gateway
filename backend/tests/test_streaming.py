import json
import pytest


@pytest.mark.asyncio
async def test_chat_completion_streaming(client, auth_headers):
    payload = {
        "model": "mock-fast",
        "messages": [{"role": "user", "content": "Stream me a message"}],
        "stream": True,
    }

    async with client.stream(
        "POST", "/v1/chat/completions", json=payload, headers=auth_headers
    ) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        chunks = []
        saw_done = False

        async for line in response.aiter_lines():
            if not line or not line.strip():
                continue
            if line == "data: [DONE]":
                saw_done = True
                break
            if line.startswith("data: "):
                data_str = line[6:].strip()
                chunk_obj = json.loads(data_str)
                chunks.append(chunk_obj)
                assert chunk_obj["object"] == "chat.completion.chunk"
                assert len(chunk_obj["choices"]) > 0

        assert saw_done is True
        assert len(chunks) > 0
        # Combine streamed content deltas
        full_text = "".join(
            c["choices"][0]["delta"].get("content", "") for c in chunks
        )
        assert len(full_text) > 0
