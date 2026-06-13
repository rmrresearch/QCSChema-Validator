#!/usr/bin/env python3
"""Build step: export Pydantic model JSON schemas to static JSON files.

Run once in a Python environment where qcelemental is installed:
    python webapp/build_schemas.py

Writes to webapp/schemas/ which is bundled into the GitHub Pages deployment.
The schemas/ directory is git-ignored; it is regenerated on every CI push.

For models that cannot generate a full JSON schema (e.g., Molecule uses custom
NumPy array types with a Pydantic metadata bug in qcelemental's next2025 branch),
a fallback schema is derived directly from model.model_fields.  The fallback
correctly identifies required vs optional fields; individual field type schemas
may be less specific than the full Pydantic-generated version.
"""

from __future__ import annotations

import json
import sys
import typing
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from qcschema_validator.schemas import collect_schemas

OUTPUT_DIR = Path(__file__).resolve().parent / "schemas"


# ---------------------------------------------------------------------------
# Schema name extraction
# ---------------------------------------------------------------------------

def _schema_name_default(model) -> str | None:
    field = model.model_fields.get("schema_name")
    if field is None:
        return None
    default = field.default
    if default is None:
        return None
    if hasattr(default, "__class__") and default.__class__.__name__ == "PydanticUndefinedType":
        return None
    return str(default)


# ---------------------------------------------------------------------------
# Fallback: build schema from model.model_fields when model_json_schema fails
# ---------------------------------------------------------------------------

def _type_to_json(annotation: typing.Any) -> dict:
    """Map a Python type annotation to a minimal JSON Schema fragment."""
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    if origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        return _type_to_json(non_none[0]) if non_none else {}

    # Annotated[X, ...] — unwrap
    try:
        from typing import Annotated
        if origin is Annotated:
            return _type_to_json(args[0]) if args else {}
    except ImportError:
        pass

    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    if origin in (list, tuple):
        return {"type": "array"}
    if origin is dict:
        return {"type": "object"}

    # Bare numpy arrays / any class with ndarray in the name
    name = getattr(annotation, "__name__", "") or ""
    if "ndarray" in name.lower() or "array" in name.lower():
        return {"type": "array"}

    # Pydantic BaseModel subclass → object
    try:
        from pydantic import BaseModel
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            return {"type": "object"}
    except ImportError:
        pass

    return {}


def _fallback_schema(model, schema_name: str) -> dict:
    """Minimal JSON Schema derived from model.model_fields (no type resolution errors)."""
    required: list[str] = []
    properties: dict[str, dict] = {}

    for fname, field in model.model_fields.items():
        if field.is_required():
            required.append(fname)
        properties[fname] = _type_to_json(field.annotation)

    return {
        "title": model.__name__,
        "type": "object",
        "properties": properties,
        "required": required,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    schemas = collect_schemas()
    manifest: dict[str, str] = {}

    for class_name, model in sorted(schemas.items()):
        schema_name = _schema_name_default(model)
        if not schema_name:
            continue

        try:
            json_schema = model.model_json_schema()
            source = "pydantic"
        except Exception:
            json_schema = _fallback_schema(model, schema_name)
            source = "fallback"

        filename = f"{schema_name}.json"
        (OUTPUT_DIR / filename).write_text(json.dumps(json_schema, indent=2))
        manifest[schema_name] = filename
        tag = "" if source == "pydantic" else " [fallback schema]"
        print(f"  {class_name!s:40s} → schemas/{filename}{tag}")

    (OUTPUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"\nWrote manifest.json ({len(manifest)} schemas).")


if __name__ == "__main__":
    main()
