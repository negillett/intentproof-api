# Changelog

Repository: [IntentProof API (`intentproof-api`)](https://github.com/IntentProof/intentproof-api).

All notable changes to this repository are documented here. Releases follow SemVer for the API package/version metadata declared in `pyproject.toml`.

## Unreleased

- **CI — ECR releases:** **`docker-ecr-release.yml`** builds **linux/amd64** and pushes to **`intentproof-api`** in ECR on semver tags **`vX.Y.Z`** (OIDC via repository secret **`AWS_ECR_PUSH_ROLE_ARN`** from **`intentproof-infra`** **`github_actions_api_ecr_push_role_arn`**).
- **Security / contract:** API key lookup uses **`secrets.compare_digest`** over same-length keys with sorted iteration (no dict short-circuit); **`INTENTPROOF_DATABASE_URL`** is required (**no embedded default credentials**).
- **`POST /v1/events`:** Response includes **`outbox_publish_ok`** when the transactional outbox path runs (**`null`**/`omitted` when SQS/outbox disabled, **`false`** when publish failed after ingest commit).
- **Conformance CI:** Align **`conformance-attestation.yml`** / **`spec-conformance.yml`** with SDK repos — checkout **`intentproof-spec`** at **`[tool.intentproof].spec-commit`**, **`paths-ignore`** on conformance JSON pushes (cert-bot loop guard), and fix cert-bot publish so **new** root **`conformance-certificate.json`** / **`conformance-report.json`** are committed (**`git diff --quiet` skipped untracked files**). README badge continues to target **`raw/main/conformance-certificate.json`** once **`intentproof-cert-bot`** lands the CI-generated files.

## 0.2.0 — 2026-05-09

- **Examples and integrator docs:** Add runnable **`examples/`** (`curl` and Python) with shared **`http_utils`** URL validation (**http**/**https**, optional path prefix, rejects query/fragment and URL userinfo); Ruff **`format`/`check`** includes **`examples/`** in **`tox -e static`**; trim README and point to **`examples/README.md`**.
- **Deploy and optional queue:** Alembic migrations, **`Dockerfile`** + Compose, **`scripts/smoke.sh`**; optional transactional **SQS** outbox (**`proof_ingest_outbox`**, **`app/verification_queue.py`**, **`scripts/publish_outbox.py`**), **`boto3`** for publishers.
- **Conformance and spec pins:** **`[tool.intentproof]`**, **`app/generated/spec_fingerprint.json`**, **`scripts/check-spec-pin.sh`**; conformance workflows and root **`conformance-report.json`** / **`conformance-certificate.json`** with README badge; consumer pin checker aligned with **`intentproof-spec`**.
- **Public-repo boundaries:** Remove **`docs/AWS_DEPLOYMENT.md`** / **`docs/DEPLOY.md`** from this repository (AWS/deploy narrative lives in maintainer umbrella docs only).

## 0.1.0 — 2026-05-08

- Bootstrap the API service scaffold with FastAPI, Pydantic, SQLAlchemy, and Postgres-first config.
- Add ingestion endpoint (`POST /v1/events`) with deterministic auth error handling and tenant derivation from API key auth context.
- Add append-only execution event persistence with idempotent duplicate handling (`tenant_id` + event hash uniqueness).
- Add correlation query endpoint (`GET /v1/events/by-correlation/{correlation_id}`) with tenant-scoped reads.
- Add quality gates: `tox` (`static`, `cov`, `py312`) with Ruff checks and 100% coverage enforcement.
- Add pre-commit hooks for Ruff autofix and formatting.
- Generate ingest request model from `intentproof-spec` and enforce drift checks in `tox -e static`.
- Add baseline GitHub CI workflow for PR/push checks on `main`.
