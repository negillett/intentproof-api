#!/usr/bin/env python3
"""Generate API models from intentproof-spec schemas."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from importlib import metadata
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_spec_root() -> Path:
    env = os.environ.get("INTENTPROOF_SPEC_ROOT", "").strip()
    if env:
        candidate = Path(env)
        if (candidate / "spec.json").is_file():
            return candidate.resolve()

    sibling = repo_root().parent / "intentproof-spec"
    if (sibling / "spec.json").is_file():
        return sibling.resolve()

    local = repo_root() / "intentproof-spec"
    if (local / "spec.json").is_file():
        return local.resolve()

    print(
        "generate_spec_models: set INTENTPROOF_SPEC_ROOT to an intentproof-spec checkout",
        file=sys.stderr,
    )
    sys.exit(1)


def run_datamodel_codegen(schema_path: Path, output_path: Path) -> None:
    cmd = [
        "datamodel-codegen",
        "--input",
        str(schema_path),
        "--output",
        str(output_path),
        "--input-file-type",
        "jsonschema",
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--target-python-version",
        "3.12",
        "--disable-timestamp",
        "--snake-case-field",
        "--class-name",
        "IntentProofExecutionEventV1",
    ]
    print("+", " ".join(cmd), file=sys.stderr)
    subprocess.run(cmd, check=True)


def patch_json_value_for_codegen(schema: dict) -> None:
    schema.setdefault("$defs", {})["JsonValue"] = {
        "anyOf": [
            {"type": "null"},
            {"type": "boolean"},
            {"type": "number"},
            {"type": "string"},
            {"type": "array", "items": True},
            {"type": "object", "additionalProperties": True},
        ]
    }


def simplify_output_for_pydantic(schema: dict) -> None:
    if "properties" in schema and "output" in schema["properties"]:
        schema["properties"]["output"] = True


def patch_generated_model(output_path: Path) -> None:
    text = output_path.read_text(encoding="utf-8")
    if "populate_by_name" not in text:
        text = text.replace(
            "    model_config = ConfigDict(\n        extra='forbid',\n    )",
            (
                "    model_config = ConfigDict(\n"
                "        extra='forbid',\n"
                "        populate_by_name=True,\n"
                "    )"
            ),
        )
    output_path.write_text(text, encoding="utf-8")


def write_spec_fingerprint_json(spec_root: Path, out_dir: Path) -> None:
    """SHA256 aggregate over normative schema files listed in spec.json (intentproof-spec manifest contract)."""
    spec = json.loads((spec_root / "spec.json").read_text(encoding="utf-8"))
    schema_paths = sorted(spec["schemas"].values())
    files: dict[str, str] = {}
    lines: list[str] = []
    for rel in schema_paths:
        raw = (spec_root / rel).read_text(encoding="utf-8")
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        files[rel] = digest
        lines.append(f"{rel}:{digest}")
    payload = {
        "specVersion": spec["version"],
        "algorithm": "sha256",
        "generator": {
            "name": "datamodel-code-generator",
            "version": metadata.version("datamodel-code-generator"),
        },
        "files": files,
        "aggregate": hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest(),
    }
    (out_dir / "spec_fingerprint.json").write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def write_generated_init(generated_dir: Path) -> None:
    init_py = generated_dir / "__init__.py"
    init_py.write_text(
        '"""Models generated from intentproof-spec. Do not edit by hand."""\n\n'
        "from app.generated.execution_event import (\n"
        "    ExecutionError,\n"
        "    IntentProofExecutionEventV1,\n"
        "    Status,\n"
        ")\n\n"
        "__all__ = [\n"
        '    "ExecutionError",\n'
        '    "IntentProofExecutionEventV1",\n'
        '    "Status",\n'
        "]\n",
        encoding="utf-8",
    )


def main() -> None:
    root = repo_root()
    spec_root = resolve_spec_root()
    spec_manifest = json.loads((spec_root / "spec.json").read_text(encoding="utf-8"))
    execution_event_schema_rel = spec_manifest["schemas"]["execution_event"]
    generated_dir = root / "app" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    output_path = generated_dir / "execution_event.py"
    source_schema = json.loads((spec_root / execution_event_schema_rel).read_text(encoding="utf-8"))
    patch_json_value_for_codegen(source_schema)
    simplify_output_for_pydantic(source_schema)
    tmp_schema = generated_dir / ".codegen_execution_event.schema.json"
    tmp_schema.write_text(json.dumps(source_schema), encoding="utf-8")

    run_datamodel_codegen(tmp_schema, output_path)
    tmp_schema.unlink(missing_ok=True)
    patch_generated_model(output_path)
    write_generated_init(generated_dir)
    write_spec_fingerprint_json(spec_root, generated_dir)

    print(f"Generated {output_path.relative_to(root)} from {execution_event_schema_rel}")


if __name__ == "__main__":
    main()
