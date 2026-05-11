# Contributing

Repository: [IntentProof/intentproof-api](https://github.com/IntentProof/intentproof-api).

Cross-repository pins, `INTENTPROOF_*` environment variables, and script naming are documented in the [`intentproof-spec` CONTRIBUTING guide](https://github.com/IntentProof/intentproof-spec/blob/main/CONTRIBUTING.md#terminology-shared-with-sdk-repos).

Typical local checks:

```bash
pip install "tox>=4"
export INTENTPROOF_SPEC_ROOT=/path/to/intentproof-spec   # required for `tox -e static` (spec pin + codegen drift)
tox run -e static
tox run -e cov
```

Spec-generated model discipline:

- Request model code under `app/generated/` is generated from `intentproof-spec`.
- Regenerate: `python3 scripts/generate_spec_models.py`
- Verify no drift: `bash scripts/verify-generated-models.sh`

## Trusted CI (default branch)

Pull requests run **Spec Conformance** (`.github/workflows/spec-conformance.yml`) with schema/replay gates and an unsigned report artifact.

After merge, **Conformance Attestation** (`.github/workflows/conformance-attestation.yml`) runs on `main` and requires the same signing and spec-integrity secrets as `intentproof-spec` trusted workflows:

- `INTENTPROOF_CERTIFICATE_SIGNING_KEY_PEM`
- `INTENTPROOF_CERTIFICATE_PUBLIC_KEY_PEM`
- `INTENTPROOF_SPEC_INTEGRITY_PUBLIC_KEY_PEM`

Custody and rotation are documented in [`intentproof-spec` CONTRIBUTING](https://github.com/IntentProof/intentproof-spec/blob/main/CONTRIBUTING.md).

## Release images (AWS ECR)

Pushing container images is **not** part of the default PR CI. After **`intentproof-infra`** **`stack`** creates the ECR push IAM role, add repository secret **`AWS_ECR_PUSH_ROLE_ARN`** (role ARN from Terraform output **`github_actions_api_ecr_push_role_arn`**). Pushing a semver tag **`vX.Y.Z`** runs **`.github/workflows/docker-ecr-release.yml`** (see root **`README.md`** and **`intentproof-infra`** **`docs/DEPLOYMENT.md`**).

For undisclosed security issues, use [Security advisories](https://github.com/IntentProof/intentproof-api/security/advisories).
