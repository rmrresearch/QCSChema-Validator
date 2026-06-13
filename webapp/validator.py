"""QCSchema browser validator — runs inside Pyodide, no qcelemental required.

Entry points called from JavaScript:
    get_schema_name(text, ext)          -> str | None
    run(text, ext, schema_json_str)     -> dict (see _result())
"""

from __future__ import annotations

import json
import tomllib
from typing import Any


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _parse(text: str, ext: str) -> Any:
    ext = ext.lower().lstrip(".")
    if ext == "json":
        return json.loads(text)
    if ext in ("yaml", "yml"):
        import yaml
        return yaml.safe_load(text)
    if ext == "toml":
        return tomllib.loads(text)
    raise ValueError(f"Unsupported file type: .{ext}")


# ---------------------------------------------------------------------------
# Type checking (no jsonschema — pure stdlib)
# ---------------------------------------------------------------------------

def _field_ok(value: Any, field_schema: dict) -> bool:
    """Lightweight type check using the JSON Schema 'type' keyword.

    Falls back to "is the value not None?" for $ref / allOf / anyOf fields
    (the browser UI does not re-implement a full JSON Schema validator).
    """
    if not field_schema or value is None:
        return value is not None

    if "$ref" in field_schema or "allOf" in field_schema or "anyOf" in field_schema:
        return value is not None

    ftype = field_schema.get("type")
    if ftype == "string":
        return isinstance(value, str)
    if ftype == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if ftype == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if ftype == "boolean":
        return isinstance(value, bool)
    if ftype == "array":
        return isinstance(value, list)
    if ftype == "object":
        return isinstance(value, dict)
    if ftype == "null":
        return value is None

    return value is not None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_schema_name(text: str, ext: str) -> str | None:
    """Parse ``text`` and return the value of its schema_name field, or None."""
    try:
        data = _parse(text, ext)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data.get("schema_name")


def run(text: str, ext: str, schema_json_str: str) -> dict:
    """Validate ``text`` against the pre-built JSON Schema in ``schema_json_str``.

    Returns a dict:
        schema_name   str | None
        required_score  float 0–1
        optional_score  float 0–1
        required_cov  {field: bool}
        optional_cov  {field: bool}
        error         str | None  (non-None on parse/lookup failure only)
    """
    # Parse file
    try:
        data = _parse(text, ext)
    except Exception as exc:
        return _error(f"Could not parse file as {ext.upper()}: {exc}")

    if not isinstance(data, dict):
        return _error("File must contain a top-level key/value mapping (object).")

    schema_name = data.get("schema_name")
    if not schema_name:
        return _error("File is missing a 'schema_name' field.")

    schema = json.loads(schema_json_str)
    properties: dict = schema.get("properties", {})
    required_set: set[str] = set(schema.get("required", []))

    required_cov: dict[str, bool] = {}
    optional_cov: dict[str, bool] = {}

    for fname, fschema in properties.items():
        present = fname in data
        ok = present and _field_ok(data[fname], fschema)
        (required_cov if fname in required_set else optional_cov)[fname] = ok

    return {
        "schema_name": schema_name,
        "required_score": _score(required_cov),
        "optional_score": _score(optional_cov),
        "required_cov": required_cov,
        "optional_cov": optional_cov,
        "error": None,
    }


def _score(cov: dict) -> float:
    return sum(cov.values()) / len(cov) if cov else 1.0


def _error(msg: str) -> dict:
    return {
        "schema_name": None,
        "required_score": 0.0,
        "optional_score": 0.0,
        "required_cov": {},
        "optional_cov": {},
        "error": msg,
    }
