from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Type, get_args, get_origin, Union, Annotated

from pydantic import BaseModel
import qcelemental.models.v2 as qc_models

SchemaType = Type[BaseModel]

def collect_schemas(module=qc_models) -> Dict[str, SchemaType]:
    """
    Collect all Pydantic models from a module.
    """
    out: Dict[str, SchemaType] = {}
    for name, obj in vars(module).items():
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
            out[name] = obj
    return out

_schemas: Dict[str, SchemaType] | None = None

def get_schemas() -> Dict[str, SchemaType]:
    global _schemas
    if _schemas is None:
        _schemas = collect_schemas()
    return _schemas

@dataclass(frozen=True)
class FieldInfo:
    name: str
    annotation: Any
    required: bool

@dataclass(frozen=True)
class ClassInfo:
    cls: SchemaType
    required: Tuple[FieldInfo, ...]
    optional: Tuple[FieldInfo, ...]
    children: Tuple[ClassInfo, ...]
    

def _is_pydantic_model_type(tp: Any) -> bool:
    return isinstance(tp, type) and issubclass(tp, BaseModel) and tp is not BaseModel

def iter_pydantic_model_types(annotation: Any) -> set[SchemaType]:
    """
    Find BaseModel subclasses inside typing constructs.
    """
    found: set[SchemaType] = set()

    def walk(tp: Any) -> None:
        if _is_pydantic_model_type(tp):
            found.add(tp)
            return

        origin = get_origin(tp)

        if origin is Annotated:
            args = get_args(tp)
            if args:
                walk(args[0])
            return

        if origin is Union:
            for a in get_args(tp):
                walk(a)
            return

        args = get_args(tp)
        if args:
            for a in args:
                walk(a)

    walk(annotation)
    return found

def describe_model(
    cls: SchemaType,
    *,
    seen: Optional[Set[SchemaType]] = None,
) -> ClassInfo:
    """
    Recursively describe a BaseModel's fields and nested model types.
    """
    seen = set() if seen is None else seen
    if cls in seen:
        return ClassInfo(cls=cls, required=(), optional=(), children=())
    seen.add(cls)

    required: List[FieldInfo] = []
    optional: List[FieldInfo] = []
    child_types: set[SchemaType] = set()

    for name, field in cls.model_fields.items():
        info = FieldInfo(name=name, annotation=field.annotation, required=field.is_required())
        (required if info.required else optional).append(info)

        child_types |= iter_pydantic_model_types(field.annotation)

    children = [
        describe_model(t, seen=seen)
        for t in sorted(child_types, key=lambda c: c.__name__)
    ]

    return ClassInfo(
        cls=cls,
        required=tuple(required),
        optional=tuple(optional),
        children=tuple(children)
    )

def print_class_info(info: ClassInfo, *, tab: str = "") -> None:
    """
    Presentation function (printing only). 
    """
    for child in info.children:
        print_class_info(child, tab=tab + "\t")

    print(f"{tab}{info.cls.__name__}")
    print(f"{tab}Required:")
    for f in info.required:
        print(f"{tab}\t{f.name} {f.annotation}")

    print(f"{tab}Optional:")
    for f in info.optional:
        print(f"{tab}\t{f.name} {f.annotation}")
