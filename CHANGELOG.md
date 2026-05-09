# Changelog

Repository: [IntentProof API (`intentproof-api`)](https://github.com/IntentProof/intentproof-api).

All notable changes to this repository are documented here. Releases follow SemVer for the API package/version metadata declared in `pyproject.toml`.

## Unreleased

- Declare `[tool.intentproof]` pyproject pins, emit `app/generated/spec_fingerprint.json` from codegen (same aggregate fingerprint contract as other IntentProof consumer repos), and enforce pins in `tox -e static` via `scripts/check-spec-pin.sh`.
- Surface root-level `conformance-report.json` and `conformance-certificate.json` artifacts and expose a README certificate badge for operator review, aligning API trust signals with SDK repositories.
- Publish refreshed root `conformance-report.json` and `conformance-certificate.json` from trusted `Conformance Attestation` runs using the cert-bot token flow, matching SDK repository artifact refresh behavior.

## 0.1.0 — 2026-05-08

- Bootstrap the API service scaffold with FastAPI, Pydantic, SQLAlchemy, and Postgres-first config.
- Add ingestion endpoint (`POST /v1/events`) with deterministic auth error handling and tenant derivation from API key auth context.
- Add append-only execution event persistence with idempotent duplicate handling (`tenant_id` + event hash uniqueness).
- Add correlation query endpoint (`GET /v1/events/by-correlation/{correlation_id}`) with tenant-scoped reads.
- Add quality gates: `tox` (`static`, `cov`, `py312`) with Ruff checks and 100% coverage enforcement.
- Add pre-commit hooks for Ruff autofix and formatting.
- Generate ingest request model from `intentproof-spec` and enforce drift checks in `tox -e static`.
- Add baseline GitHub CI workflow for PR/push checks on `main`.
