# Contributing

Repository: [IntentProof/intentproof-api](https://github.com/IntentProof/intentproof-api).

Cross-repository pins, `INTENTPROOF_*` environment variables, and script naming are documented in the [`intentproof-spec` CONTRIBUTING guide](https://github.com/IntentProof/intentproof-spec/blob/main/CONTRIBUTING.md#terminology-shared-with-sdk-repos).

Typical local checks:

```bash
pip install "tox>=4"
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

For undisclosed security issues, use [Security advisories](https://github.com/IntentProof/intentproof-api/security/advisories).
