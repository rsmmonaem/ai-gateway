import pytest
from app.router.classifier import request_classifier
from app.schemas.openai import ChatCompletionRequest, ChatMessage
from app.services.web_search import web_search_service


def test_classifier_code_detection():
    req = ChatCompletionRequest(
        model="universal",
        messages=[
            ChatMessage(role="user", content="Write a Python script using def search_binary(arr, target): return -1")
        ]
    )
    target = request_classifier.classify_request(req)
    assert target == "coding"


def test_classifier_reasoning_detection():
    req = ChatCompletionRequest(
        model="universal",
        messages=[
            ChatMessage(role="user", content="Provide a step-by-step mathematical proof of the Pythagorean theorem and derive calculus equations.")
        ]
    )
    target = request_classifier.classify_request(req)
    assert target == "reasoning"


def test_classifier_vision_detection():
    req = ChatCompletionRequest(
        model="universal",
        messages=[
            ChatMessage(role="user", content=[
                {"type": "text", "text": "Describe image"},
                {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}}
            ])
        ]
    )
    target = request_classifier.classify_request(req)
    assert target == "vision"


def test_classifier_web_search_detection():
    req = ChatCompletionRequest(
        model="universal",
        messages=[
            ChatMessage(role="user", content="What is the latest release version of Laravel in 2026?")
        ]
    )
    target = request_classifier.classify_request(req)
    assert target == "web_search"


def test_classifier_fast_default():
    req = ChatCompletionRequest(
        model="universal",
        messages=[ChatMessage(role="user", content="What is the capital of France?")]
    )
    target = request_classifier.classify_request(req)
    assert target == "fast"


def test_web_search_formatting():
    sample_results = [
        {"title": "Laravel 11 Released", "snippet": "Laravel 11 features thin skeleton...", "url": "https://laravel.com"}
    ]
    formatted = web_search_service.format_search_context(sample_results)
    assert "--- LIVE WEB SEARCH RESULTS ---" in formatted
    assert "Laravel 11 Released" in formatted


@pytest.mark.asyncio
async def test_universal_model_api_endpoint(client, auth_headers):
    payload = {
        "model": "universal",
        "messages": [{"role": "user", "content": "How do I define a function in Python?"}],
        "stream": False,
    }
    resp = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "choices" in data
    assert len(data["choices"]) > 0


@pytest.mark.asyncio
async def test_aliases_api_endpoint(client, auth_headers):
    for alias in ["fast", "coding", "reasoning", "universal"]:
        payload = {
            "model": alias,
            "messages": [{"role": "user", "content": "Test alias endpoint"}],
            "stream": False,
        }
        resp = await client.post("/v1/chat/completions", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data
