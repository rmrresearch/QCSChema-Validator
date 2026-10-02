from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Annotated, Any, get_origin

import numpy as np
from pydantic import ConfigDict, PydanticUserError, TypeAdapter, ValidationError

from .schemas import get_schemas


@dataclass(frozen=True)
class CoverageResult:
    schema_name: str
    required_cov: dict[str, bool]
    optional_cov: dict[str, bool]
    allowlisted_cov: dict[str, bool]
    required_vals: dict[str, Any]
    optional_vals: dict[str, Any]
    allowlisted_vals: dict[str, Any]

    @property
    def required_score(self) -> float:
        return (sum(self.required_cov.values()) / len(self.required_cov)) if self.required_cov else 1.0

    @property
    def optional_score(self) -> float:
        return (sum(self.optional_cov.values()) / len(self.optional_cov)) if self.optional_cov else 1.0

    @property
    def allowlisted_score(self) -> float:
        return (sum(self.allowlisted_cov.values()) / len(self.allowlisted_cov)) if self.allowlisted_cov else 1.0


def _type_adapter(annotation: Any) -> TypeAdapter:
    try:
        return TypeAdapter(annotation, config=ConfigDict(arbitrary_types_allowed=True))
    except PydanticUserError as e:
        # BaseModel, dataclass and TypedDict types carry their own config
        if e.code != "type-adapter-config-unused":
            raise
        return TypeAdapter(annotation)


def matches(value: Any, annotation: Any, metadata: Any = ()) -> bool:
    is_array = get_origin(annotation) == np.ndarray or annotation is np.ndarray
    if is_array and metadata:
        # qcelemental keeps the array caster in the field metadata, not the annotation
        annotation = Annotated[annotation, *metadata]
    elif is_array:
        value = np.asarray(value)
    ta = _type_adapter(annotation)
    try:
        out = ta.validate_python(value)
    except (ValidationError, ValueError, TypeError):
        return False
    if is_array:
        return isinstance(out, np.ndarray) and out.ndim >= 1
    return True

def _pick_schema(data: dict) -> Any | None:
    schema_name = data.get("schema_name")
    if schema_name is None:
        return None

    schemas = get_schemas()
    for model in schemas.values():
        if (
            "schema_name" in model.model_fields
            and model.model_fields["schema_name"].default == schema_name
        ):
            return model

    return None

def validate_data_against_schemas(
    data: dict, *, allowlist: set[str] | None = None
) -> CoverageResult:
    model = _pick_schema(data)
    if model is None:
        raise ValueError("Could not determine schema from data['schema_name'].")

    schema_name = data["schema_name"]
    known_fields = set(model.model_fields)

    if allowlist is not None:
        unknown = allowlist - known_fields
        for name in sorted(unknown):
            warnings.warn(
                f"Allowlisted field '{name}' is not a field of '{schema_name}' and will be ignored.",
                UserWarning,
                stacklevel=2,
            )

    required_cov: dict[str, bool] = {}
    optional_cov: dict[str, bool] = {}
    allowlisted_cov: dict[str, bool] = {}
    required_vals: dict[str, Any] = {}
    optional_vals: dict[str, Any] = {}
    allowlisted_vals: dict[str, Any] = {}

    for field_name, field in model.model_fields.items():
        present = field_name in data
        is_req = field.is_required()
        in_allowlist = (allowlist is not None) and (field_name in allowlist)

        if not present:
            if is_req:
                required_cov[field_name] = False
                required_vals[field_name] = None
            elif in_allowlist:
                allowlisted_cov[field_name] = False
                allowlisted_vals[field_name] = None
            else:
                optional_cov[field_name] = False
                optional_vals[field_name] = None
            continue

        ok = matches(data[field_name], field.annotation, field.metadata)
        if is_req:
            required_cov[field_name] = ok
            required_vals[field_name] = data[field_name]
        elif in_allowlist:
            allowlisted_cov[field_name] = ok
            allowlisted_vals[field_name] = data[field_name]
        else:
            optional_cov[field_name] = ok
            optional_vals[field_name] = data[field_name]

    return CoverageResult(
        schema_name=schema_name,
        required_cov=required_cov,
        optional_cov=optional_cov,
        allowlisted_cov=allowlisted_cov,
        required_vals=required_vals,
        optional_vals=optional_vals,
        allowlisted_vals=allowlisted_vals,
    )
