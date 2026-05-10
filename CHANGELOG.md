# Changelog

Repository: [IntentProof API (`intentproof-api`)](https://github.com/IntentProof/intentproof-api).

All notable changes to this repository are documented here. Releases follow SemVer for the API package/version metadata declared in `pyproject.toml`.

## Unreleased

- **Examples and developer docs:** runnable **`examples/`** (**`curl`** with **`curl -f`**, **`http_utils.require_http_base`** for **`INTENTPROOF_API_BASE`** (**http**/**https**, optional path prefix, no query/fragment or URL userinfo), URL-encoded correlation ids, validated **`limit`** (**1–500**); Python **`HttpExporter`** + stdlib **`urllib`** with **`URLError`** handling and non-zero exits on failure; optional **`INTENTPROOF_SDK_PYTHON_ROOT`**; security notes and **`tox -e static`** Ruff coverage for **`examples/`**). Top-level README points to **`examples/README.md`**.
- **Public-repo hygiene:** remove **`docs/AWS_DEPLOYMENT.md`** / **`docs/DEPLOY.md`** — AWS/deploy narrative is maintainer/umbrella-only, not shipped in this repo.
- **Transactional ingest and ops:** Alembic + Docker Compose + **`scripts/smoke.sh`**; optional **SQS** outbox (**`proof_ingest_outbox`**, **`app/verification_queue.py`**, **`scripts/publish_outbox.py`**), **`boto3`**; SQLite tests use **`create_all`** only on SQLite URLs.
- **Spec pins and conformance:** **`[tool.intentproof]`**, **`app/generated/spec_fingerprint.json`**, **`scripts/check-spec-pin.sh`**; root **`conformance-report.json`** / **`conformance-certificate.json`**, README badge, cert-bot refresh on **`main`**.

## 0.1.0 — 2026-05-08

- Bootstrap the API service scaffold with FastAPI, Pydantic, SQLAlchemy, and Postgres-first config.
- Add ingestion endpoint (`POST /v1/events`) with deterministic auth error handling and tenant derivation from API key auth context.
- Add append-only execution event persistence with idempotent duplicate handling (`tenant_id` + event hash uniqueness).
- Add correlation query endpoint (`GET /v1/events/by-correlation/{correlation_id}`) with tenant-scoped reads.
- Add quality gates: `tox` (`static`, `cov`, `py312`) with Ruff checks and 100% coverage enforcement.
- Add pre-commit hooks for Ruff autofix and formatting.
- Generate ingest request model from `intentproof-spec` and enforce drift checks in `tox -e static`.
- Add baseline GitHub CI workflow for PR/push checks on `main`.
