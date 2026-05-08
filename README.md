# IntentProof API

Logs narrate; IntentProof gives you proof.

`intentproof-api` is the Stage 3 service for ingesting and querying execution evidence with strict tenant boundaries and deterministic behavior. It is built with Python, FastAPI, Pydantic, SQLAlchemy, and Postgres.

Repository: [IntentProof/intentproof-api](https://github.com/IntentProof/intentproof-api).

## Why this service exists

IntentProof answers four questions:

- what was supposed to happen
- what actually happened
- did those match
- can that be proven

This API is the first SaaS-layer step: accept valid `ExecutionEvent` payloads, store them append-only, and retrieve correlation-scoped event history for downstream verification and reconciliation.

## Current status (Stage 3 scaffold)

Implemented now:

- `POST /v1/events` ingestion endpoint
- API key authentication with server-side tenant derivation
- append-only persistence model with idempotent duplicate handling (hash-based)
- tenant-scoped correlation query: `GET /v1/events/by-correlation/{correlation_id}`
- deterministic JSON error envelope
- quality gates: `tox`, `ruff`, pre-commit, and 100% test coverage enforcement

Planned next:

- production auth mode (JWT or equivalent)
- cursor-based pagination for correlation queries
- OpenAPI hardening and endpoint versioning policy
- migration workflow (`alembic`) and production DB operations
- Stage 3 gate integration suite against real Postgres

## Implementation status legend

To keep this README unambiguous:

- **Implemented now**: present in the current codebase and tests.
- **Planned**: intended direction, not fully implemented yet.

Quick status map:

| Area | Status | Notes |
| --- | --- | --- |
| `POST /v1/events` ingest | Implemented now | Auth, validation, idempotent hash check, append-only write, `202` |
| `GET /v1/events/by-correlation/{correlation_id}` | Implemented now | Tenant-scoped reads, ordered results, `limit` parameter |
| Canonical error envelope | Implemented now | `unauthenticated`, `unauthorized_tenant`, `http_error` |
| API key -> tenant mapping | Implemented now | Derived server-side via `X-API-Key` |
| Spec-generated request model | Implemented now | `ExecutionEvent` request model generated from `intentproof-spec` |
| JWT/production auth mode | Planned | API keys are MVP-only |
| Cursor pagination | Planned | Current query uses `limit`, no cursor token yet |
| Alembic migrations | Planned | SQLAlchemy model exists; migration workflow not added yet |
| Expanded API reference docs | Planned | Swagger/OpenAPI endpoints available, long-form reference pending |

## Requirements

- Python 3.12+
- Postgres 15+ (recommended for local/prod parity)

## Quickstart

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -e ".[dev]"`
3. Copy environment file:
   - `cp .env.example .env`
4. Start the API:
   - `uvicorn app.main:app --reload`
5. Open docs:
   - Swagger UI: `http://127.0.0.1:8000/docs`
   - OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Configuration

- `INTENTPROOF_DATABASE_URL`: SQLAlchemy URL (defaults to local Postgres)
- `INTENTPROOF_API_KEYS`: JSON object mapping API key to tenant id
- `INTENTPROOF_ENV`: environment name (`dev`, `staging`, `prod`, etc.)

Example API key map:

```json
{"dev-local-key":"tenant-dev","ops-local-key":"tenant-ops"}
```

## API surface (MVP)

Status: **Implemented now**

### Health

- `GET /health`
- Purpose: liveness probe for local/dev orchestration

### Ingest execution events

- `POST /v1/events`
- Auth: `X-API-Key` header
- Behavior:
  - derives `tenant_id` from API key map (never trusted from request body)
  - validates request shape with Pydantic
  - computes deterministic event hash for idempotent retries
  - writes append-only event record
  - returns `202 Accepted`

### Query by correlation

- `GET /v1/events/by-correlation/{correlation_id}`
- Auth: `X-API-Key` header
- Behavior:
  - tenant-scoped reads only
  - stable ascending order by insertion id
  - bounded result size via `limit` query param

## Error model

Status: **Implemented now**

All failures return a canonical envelope:

```json
{
  "code": "unauthenticated",
  "message": "Missing API key.",
  "details": {},
  "correlation_id": null
}
```

Current codes include:

- `unauthenticated` for missing API key
- `unauthorized_tenant` for invalid API key / tenant access
- `http_error` fallback for framework-level HTTP exceptions

## Example requests

Status: **Implemented now** (examples reflect current request/response models and routes)

### Ingest event

```bash
curl -X POST "http://127.0.0.1:8000/v1/events" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-local-key" \
  -d '{
    "id": "evt-1",
    "correlationId": "corr-123",
    "intent": "Capture customer payment after checkout authorization",
    "action": "checkout.capture_payment",
    "status": "ok",
    "inputs": {"amount": 1000, "currency": "USD"},
    "output": {"captureId": "cap-1", "status": "succeeded"},
    "startedAt": "2026-05-08T12:00:00Z",
    "completedAt": "2026-05-08T12:00:00Z",
    "durationMs": 0,
    "attributes": {"service": "checkout-api", "env": "dev"}
  }'
```

### Query correlation

```bash
curl "http://127.0.0.1:8000/v1/events/by-correlation/corr-123?limit=100" \
  -H "X-API-Key: dev-local-key"
```

## Development workflow

### Quality gates

- `python3 -m tox -q`
  - `static`: Ruff formatting/lint checks
    - validates generated models are in sync with `intentproof-spec`
  - `cov`: pytest with 100% coverage gate

### Spec-generated models

Status: **Implemented now**

- Request model for `POST /v1/events` is generated from `intentproof-spec` schema:
  - `app/generated/execution_event.py`
- Generate/update models:
  - `python3 scripts/generate_spec_models.py`
- Verify drift against spec (also run by `tox -e static`):
  - `bash scripts/verify-generated-models.sh`

### Pre-commit hooks

- Install once:
  - `python3 -m pre_commit install`
- Run manually:
  - `python3 -m pre_commit run --all-files`
- Hooks configured:
  - `ruff-check --fix`
  - `ruff-format`

## Repository layout

- `app/main.py`: FastAPI app, routes, exception handling
- `app/auth.py`: API key -> tenant mapping dependency
- `app/models.py`: SQLAlchemy persistence models
- `app/schemas.py`: request/response and envelope schemas
- `app/db.py`: engine/session lifecycle
- `tests/test_api.py`: API behavior and coverage gates
- `tox.ini`: quality/test orchestration

## Security and operations notes

- API keys are an MVP mechanism; move to stronger auth before production.
- Tenant identity is derived from trusted auth context, not client payload.
- Event storage is append-only in application paths.
- Keep DB credentials and keys out of logs and source control.
- Run this service behind TLS and hardened ingress in non-local environments.

## Roadmap placeholders

These sections are intentionally reserved for upcoming Stage 3/4 docs:

- API Reference (expanded endpoint contracts)
- Auth and tenancy model (production mode)
- Data model and migrations
- Deployment guide
- SLOs, observability, and runbooks
- Verification and reconciliation integration

## Related repositories

- `intentproof-spec` (schemas, conformance, normative semantics)
- `intentproof-sdk-node`
- `intentproof-sdk-python`
- `intentproof-sdk-java`

## Project policy docs

- Contribution guide: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`
- Change history: `CHANGELOG.md`

## License

Apache-2.0 (see `LICENSE`).
