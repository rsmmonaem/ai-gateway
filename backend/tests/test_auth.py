import pytest
from app.core.security import (
    generate_api_key,
    get_password_hash,
    hash_api_key,
    verify_password,
)


def test_password_hashing():
    pwd = "super-secure-password-123"
    hashed = get_password_hash(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_api_key_generation():
    raw_key, key_hash, key_prefix = generate_api_key()
    assert raw_key.startswith("sk-local-")
    assert len(key_hash) == 64
    assert key_prefix.startswith("sk-local-")
    # Verify deterministic hashing
    assert hash_api_key(raw_key) == key_hash


@pytest.mark.asyncio
async def test_api_key_auth_success(client, auth_headers):
    resp = await client.get("/v1/models", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"


@pytest.mark.asyncio
async def test_missing_api_key(client):
    resp = await client.get("/v1/models")
    assert resp.status_code == 401
    assert "error" in resp.json()
    assert resp.json()["error"]["code"] == "missing_api_key"


@pytest.mark.asyncio
async def test_invalid_api_key(client):
    resp = await client.get(
        "/v1/models", headers={"Authorization": "Bearer sk-local-invalidkey999"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_api_key"


@pytest.mark.asyncio
async def test_revoked_api_key(client):
    resp = await client.get(
        "/v1/models", headers={"Authorization": "Bearer sk-local-revokedkey"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_api_key"
