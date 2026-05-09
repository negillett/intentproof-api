import asyncio

import pytest
from app.config import reset_settings_cache
from app.db import reset_engine_cache
from app.main import app, http_exception_handler
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request


def sample_event(
    event_id: str = "evt-1",
    correlation_id: str = "corr-1",
    action: str = "checkout.capture_payment",
):
    return {
        "id": event_id,
        "correlationId": correlation_id,
        "intent": "Capture customer payment after checkout authorization",
        "action": action,
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
    monkeypatch.setenv(
        "INTENTPROOF_API_KEYS",
        '{"test-key":"tenant-test","test-key-b":"tenant-b"}',
    )
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
    assert len(response.json()["items"]) == 1


def test_query_by_correlation_is_tenant_isolated(client):
    headers_a = {"X-API-Key": "test-key"}
    headers_b = {"X-API-Key": "test-key-b"}

    # Same correlation_id across tenants must not leak across query boundaries.
    client.post(
        "/v1/events",
        json=sample_event(event_id="evt-a-1", correlation_id="shared-corr"),
        headers=headers_a,
    )
    client.post(
        "/v1/events",
        json=sample_event(event_id="evt-b-1", correlation_id="shared-corr"),
        headers=headers_b,
    )

    response_a = client.get("/v1/events/by-correlation/shared-corr", headers=headers_a)
    response_b = client.get("/v1/events/by-correlation/shared-corr", headers=headers_b)

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a.json()["tenant_id"] == "tenant-test"
    assert response_b.json()["tenant_id"] == "tenant-b"
    assert [item["tenant_id"] for item in response_a.json()["items"]] == ["tenant-test"]
    assert [item["tenant_id"] for item in response_b.json()["items"]] == ["tenant-b"]


def test_idempotency_is_scoped_per_tenant(client):
    headers_a = {"X-API-Key": "test-key"}
    headers_b = {"X-API-Key": "test-key-b"}
    event = sample_event(event_id="evt-shared", correlation_id="corr-shared")

    first_a = client.post("/v1/events", json=event, headers=headers_a)
    second_a = client.post("/v1/events", json=event, headers=headers_a)
    first_b = client.post("/v1/events", json=event, headers=headers_b)
    second_b = client.post("/v1/events", json=event, headers=headers_b)

    assert first_a.status_code == 202
    assert first_b.status_code == 202
    assert first_a.json()["duplicate"] is False
    assert second_a.json()["duplicate"] is True
    assert first_b.json()["duplicate"] is False
    assert second_b.json()["duplicate"] is True


def test_query_limit_and_order_are_tenant_scoped(client):
    headers_a = {"X-API-Key": "test-key"}
    headers_b = {"X-API-Key": "test-key-b"}

    for i in range(3):
        client.post(
            "/v1/events",
            json=sample_event(
                event_id=f"evt-a-{i}",
                correlation_id="corr-limit",
                action=f"checkout.step_{i}",
            ),
            headers=headers_a,
        )

    for i in range(2):
        client.post(
            "/v1/events",
            json=sample_event(
                event_id=f"evt-b-{i}",
                correlation_id="corr-limit",
                action=f"tenant-b.step_{i}",
            ),
            headers=headers_b,
        )

    response_a = client.get("/v1/events/by-correlation/corr-limit?limit=2", headers=headers_a)
    response_b = client.get("/v1/events/by-correlation/corr-limit?limit=10", headers=headers_b)

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a.json()["tenant_id"] == "tenant-test"
    assert response_b.json()["tenant_id"] == "tenant-b"

    items_a = response_a.json()["items"]
    items_b = response_b.json()["items"]
    assert len(items_a) == 2
    assert len(items_b) == 2
    assert [item["event_type"] for item in items_a] == ["checkout.step_0", "checkout.step_1"]
    assert [item["event_type"] for item in items_b] == ["tenant-b.step_0", "tenant-b.step_1"]
    assert all(item["tenant_id"] == "tenant-test" for item in items_a)
    assert all(item["tenant_id"] == "tenant-b" for item in items_b)


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


def test_openapi_contract_includes_core_endpoints_and_schemas(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200

    openapi = response.json()
    paths = openapi["paths"]
    components = openapi["components"]["schemas"]

    assert "/v1/events" in paths
    assert "/v1/events/by-correlation/{correlation_id}" in paths
    assert "IngestEventResponse" in components
    assert "CorrelationQueryResponse" in components
    assert "IntentProofExecutionEventV1" in components
