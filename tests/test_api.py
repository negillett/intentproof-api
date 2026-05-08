import asyncio

import pytest
from app.config import reset_settings_cache
from app.db import reset_engine_cache
from app.main import app, http_exception_handler
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request


def sample_event():
    return {
        "id": "evt-1",
        "correlationId": "corr-1",
        "intent": "Capture customer payment after checkout authorization",
        "action": "checkout.capture_payment",
        "status": "ok",
        "inputs": {"amount": 1000, "currency": "USD"},
        "output": {"captureId": "cap-1", "status": "succeeded"},
        "startedAt": "2026-05-08T12:00:00Z",
        "completedAt": "2026-05-08T12:00:00Z",
        "durationMs": 0,
        "attributes": {"service": "checkout-api", "env": "test"},
    }


@pytest.fixture
def test_env(monkeypatch, tmp_path):
    db_path = tmp_path / "intentproof_api_test.db"
    monkeypatch.setenv("INTENTPROOF_DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    monkeypatch.setenv("INTENTPROOF_API_KEYS", '{"test-key":"tenant-test"}')
    reset_settings_cache()
    reset_engine_cache()
    yield
    reset_engine_cache()


@pytest.fixture
def client(test_env):
    with TestClient(app) as test_client:
        yield test_client


def test_health(test_env):
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ingest_requires_api_key(test_env):
    with TestClient(app) as client:
        response = client.post("/v1/events", json=sample_event())
    assert response.status_code == 401
    assert response.json()["code"] == "unauthenticated"


def test_ingest_and_duplicate(client):
    headers = {"X-API-Key": "test-key"}
    first = client.post("/v1/events", json=sample_event(), headers=headers)
    assert first.status_code == 202
    assert first.json()["duplicate"] is False

    second = client.post("/v1/events", json=sample_event(), headers=headers)
    assert second.status_code == 202
    assert second.json()["duplicate"] is True


def test_ingest_invalid_key_rejected(client):
    headers = {"X-API-Key": "not-valid"}
    response = client.post("/v1/events", json=sample_event(), headers=headers)
    assert response.status_code == 403
    assert response.json()["code"] == "unauthorized_tenant"


def test_query_by_correlation(client):
    headers = {"X-API-Key": "test-key"}
    client.post("/v1/events", json=sample_event(), headers=headers)
    response = client.get("/v1/events/by-correlation/corr-1", headers=headers)
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-test"


def test_http_exception_handler_fallback_envelope():
    request = Request(
        scope={
            "type": "http",
            "headers": [(b"x-correlation-id", b"corr-fallback")],
            "method": "GET",
            "path": "/test",
        }
    )
    response = asyncio.run(
        http_exception_handler(request, HTTPException(status_code=400, detail="bad-input"))
    )
    assert response.status_code == 400
    assert b'"code":"http_error"' in response.body
    assert b'"correlation_id":"corr-fallback"' in response.body
