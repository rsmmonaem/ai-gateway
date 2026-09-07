import pytest


@pytest.mark.asyncio
async def test_list_models(client, auth_headers):
    resp = await client.get("/v1/models", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    assert len(data["data"]) >= 1

    model_ids = [m["id"] for m in data["data"]]
    assert "mock-fast" in model_ids
    # Disabled models must never be returned in public models list
    assert "disabled-model" not in model_ids


@pytest.mark.asyncio
async def test_get_single_model(client, auth_headers):
    resp = await client.get("/v1/models/mock-fast", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "mock-fast"
    assert data["object"] == "model"
    assert data["context_length"] == 16384


@pytest.mark.asyncio
async def test_get_nonexistent_model(client, auth_headers):
    resp = await client.get("/v1/models/non-existent-model", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "model_not_found"
