## **Logs narrate; IntentProof gives you proof.**

[![CI](https://github.com/IntentProof/intentproof-api/actions/workflows/ci.yml/badge.svg)](https://github.com/IntentProof/intentproof-api/actions/workflows/ci.yml)
<a href="https://github.com/IntentProof/intentproof-api/raw/main/conformance-certificate.json" target="_blank" rel="noopener noreferrer"><img src="https://img.shields.io/badge/conformance_certificate-view-0366d6" alt="Conformance Certificate" /></a>

**IntentProof** is **auditable execution records** for actions that must be defensible—**intent** tied to what actually ran.

**This service** ingests **`ExecutionEvent`** payloads over HTTPS, keeps them in an **append-only** store, and serves **tenant-scoped** correlation queries—so proof can be **reconciled** with reality downstream, not only observed.

Observability captures what happened. **IntentProof** tells you whether it matched what was **meant to happen**.

Every **`ExecutionEvent`** contains:

- **`intent`**: what this invocation was meant to prove
- **`action`**: the stable operation id for this step
- **`status`**: success or error
- **`inputs`** and **`output`**: what the runtime saw going in and coming out

## Why this matters

Modern systems—especially AI agents—do not only compute; they act:
issuing refunds, sending emails, updating databases.

When something goes wrong, logs tell you what ran.
They don't tell you:

- what was supposed to happen
- whether all steps completed
- whether systems ended up in a consistent state

**IntentProof** exists to bridge that gap.

It records intent alongside execution so systems can be verified, not just observed.

### Picture this:

It's 4:47 on a Friday. A customer insists the critical action never happened. Support sees scattered traces; engineering sees green checks; finance asks for **one** clean chain: what was **supposed** to occur, what **did** occur, and whether the outcome is **complete**.

Ordinary telemetry shows that *something ran*. It rarely ships an **auditable story** you can hand to someone who doesn't read your codebase. **IntentProof** exists for when the question stops being "what was logged?" and starts being **"prove it."**

## What this repository is

**Repository:** [IntentProof/intentproof-api](https://github.com/IntentProof/intentproof-api).

**`intentproof-api`** is the hosted ingestion plane for **`ExecutionEvent`** evidence: strict tenant boundaries, deterministic behavior, and quality gates you can trust in CI. It is built with **Python**, **FastAPI**, **Pydantic**, **SQLAlchemy**, and **Postgres**.

## Current status

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
- optional deploy-pipeline check that pinned **`intentproof-spec`** revision matches conformance artifacts (when CI/CD exists)
- expanded integration suite against long-lived Postgres

Shipped toward ops: **Alembic** migrations (Postgres), **Docker** image + **`docker-compose.yml`**, post-deploy **`scripts/smoke.sh`**, optional **SQS** transactional outbox (**`app/verification_queue.py`**) when **`INTENTPROOF_SQS_QUEUE_URL`** is set.

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
| Alembic migrations | Implemented now | Initial revision under **`alembic/versions/`**; run **`alembic upgrade head`** or use the Docker entrypoint |
| Docker / Compose | Implemented now | **`Dockerfile`**, **`docker-compose.yml`** (API + Postgres) |
| Post-append **SQS** (optional) | Implemented now | **`INTENTPROOF_SQS_QUEUE_URL`** → transactional **`proof_ingest_outbox`** + **`intentproof.proof.ingested`** envelope (`schema_version` / `message_id`); **`scripts/publish_outbox.py`** retries unpublished rows |
| Expanded API reference docs | Planned | Swagger/OpenAPI endpoints available, long-form reference pending |

## Requirements

- **Python** 3.12 or newer
- **Postgres** 15+ (recommended for local and production parity)

## Quick start

### Option A — Docker Compose (Postgres + API)

1. Install Docker.
2. Run:
   - `docker compose up --build`
3. Call the API with header **`X-API-Key: compose-local-key`** (see **`docker-compose.yml`**).
4. Open docs: `http://127.0.0.1:8000/docs`

Migrations run automatically via the container entrypoint (**`alembic upgrade head`**).

### Option B — Local Python (SQLite tests use auto-`create_all`; Postgres needs Alembic)

1. Create and activate a virtual environment.
2. Install dependencies:
   - `pip install -e ".[dev]"`
3. Copy environment file:
   - `cp .env.example .env`
4. **Postgres:** apply schema before first request:
   - `alembic upgrade head`
5. Start the API:
   - `uvicorn app.main:app --reload`
6. Open docs:
   - Swagger UI: `http://127.0.0.1:8000/docs`
   - OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

### Post-deploy smoke

With **`BASE_URL`** and an API key:

```bash
export BASE_URL="http://127.0.0.1:8000"
export API_KEY="your-key"
bash scripts/smoke.sh
```

Requires **`curl`** and **`jq`**.

## Configuration

- `INTENTPROOF_DATABASE_URL`: SQLAlchemy URL (**required** — set explicitly; use SQLite for local tests, Postgres in Docker via Compose, or RDS in production)
- `INTENTPROOF_API_KEYS`: JSON object mapping API key to tenant id (production deployments should use **hashed keys stored in Postgres**, not environment JSON)
- `INTENTPROOF_ENV`: environment name (`dev`, `staging`, `prod`, etc.)
- `INTENTPROOF_SQS_QUEUE_URL` (optional): Amazon SQS queue URL — after a successful append (non-duplicate), enqueue **`intentproof.proof.ingested`** for verification workers
- `INTENTPROOF_AWS_REGION` (optional): AWS region for the SQS client when it cannot be inferred from the environment

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
  - optionally notifies **Amazon SQS** for downstream verification (when `INTENTPROOF_SQS_QUEUE_URL` is set; failures are logged and do not fail the request)
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

Runnable **`curl`** and Python scripts live under **`examples/`** (see **`examples/README.md`**). Set **`INTENTPROOF_API_BASE`** and **`INTENTPROOF_API_KEY`** to match your deployment. The SDK example uses the real **`intentproof`** package — **`pip install -e ../intentproof-sdk-python`** when that repo sits next to **`intentproof-api`** (typical **`~/src`** layout), or install **`intentproof-sdk`** from PyPI.

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
- `examples/`: sample **`curl`** and Python callers (see **`examples/README.md`**); shared **`http_utils.py`** for URL validation in Python scripts
- `tests/test_api.py`: API behavior and coverage gates
- `tox.ini`: quality/test orchestration

## Security and operations notes

- API keys are an MVP mechanism; move to stronger auth before production.
- Tenant identity is derived from trusted auth context, not client payload.
- Event storage is append-only in application paths.
- Keep DB credentials and keys out of logs and source control.
- Run this service behind TLS and hardened ingress in non-local environments.

## Roadmap placeholders

These sections are intentionally reserved for upcoming docs:

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
