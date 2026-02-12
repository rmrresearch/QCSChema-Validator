from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, get_origin

import numpy as np
from pydantic import ConfigDict, TypeAdapter, ValidationError

from .schemas import get_schemas


@dataclass(frozen=True)
class CoverageResult:
    schema_name: str
    required_cov: Dict[str, bool]
    optional_cov: Dict[str, bool]
    required_vals: Dict[str, Any]
    optional_vals: Dict[str, Any]

    @property
    def required_score(self) -> float:
        return (sum(self.required_cov.values()) / len(self.required_cov)) if self.required_cov else 1.0

    @property
    def optional_score(self) -> float:
        return (sum(self.optional_cov.values()) / len(self.optional_cov)) if self.optional_cov else 1.0


def matches(value: Any, annotation: Any) -> bool:
    ta = TypeAdapter(annotation, config=ConfigDict(arbitrary_types_allowed=True))
    try:
        if get_origin(annotation) == np.ndarray or annotation is np.ndarray:
            ta.validate_python(np.asarray(value))
        else:
            ta.validate_python(value)
        return True

    except ValidationError:
        return False

def _pick_schema(data: dict) -> Optional[Any]:
    schema_name = data.get("schema_name")
    if schema_name is None:
        return None

    schemas = get_schemas()
    for _name, model in schemas.items():
        if "schema_name" in model.model_fields:
            if model.model_fields["schema_name"].default == schema_name:
                return model

    return None

def validate_data_against_schemas(data: dict) -> CoverageResult:
    model = _pick_schema(data)
    if model is None:
        raise ValueError("Could not determine schema from data['schema_name'].")

    schema_name = data["schema_name"]
    required_cov: Dict[str, bool] = {}
    optional_cov: Dict[str, bool] = {}
    required_vals: Dict[str, Any] = {}
    optional_vals: Dict[str, Any] = {}

    for field_name, field in model.model_fields.items():
        present = field_name in data
        is_req = field.is_required()

        if not present:
            if is_req:
                required_cov[field_name] = False
                required_vals[field_name] = None
            else:
                optional_cov[field_name] = False
                optional_vals[field_name] = None
            continue

        ok = matches(data[field_name], field.annotation)
        if is_req:
            required_cov[field_name] = ok
            required_vals[field_name] = data[field_name]
        else:
            optional_cov[field_name] = ok
            optional_vals[field_name] = data[field_name]

    return CoverageResult(
        schema_name=schema_name,
        required_cov=required_cov,
        optional_cov=optional_cov,
        required_vals=required_vals,
        optional_vals=optional_vals
    )
