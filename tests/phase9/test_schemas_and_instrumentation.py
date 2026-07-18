from __future__ import annotations

import ast
import json
from pathlib import Path

import jsonschema


ROOT = Path(__file__).resolve().parents[2]


def test_phase9_schemas_are_valid() -> None:
    for name in ("phase9_generation_manifest", "phase9_participant_state", "generation_summary", "phase9_claim_gate"):
        schema = json.loads((ROOT / f"schemas/v04/{name}.schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)


def test_every_python_print_has_identifying_comment() -> None:
    for path in (ROOT / "scripts").glob("*phase9*.py"):
        lines = path.read_text(encoding="utf-8").splitlines()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                assert lines[node.lineno - 2].strip().startswith("# console.log:"), (path, node.lineno)


def test_every_javascript_console_log_has_identifying_comment() -> None:
    for path in (ROOT / "scripts").glob("*phase9*.mjs"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if "console.log(" in line and not line.strip().startswith("//"):
                assert lines[index - 1].strip().startswith("// console.log:"), (path, index + 1)

