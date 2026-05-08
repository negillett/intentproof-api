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

For undisclosed security issues, use [Security advisories](https://github.com/IntentProof/intentproof-api/security/advisories).
