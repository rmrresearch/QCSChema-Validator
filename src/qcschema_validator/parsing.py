from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Union

import json
import yaml
import tomllib

PathLike = Union[str, Path]
ParserFn = Callable[[Path], Any]

def _open_rb(path: Path):
    """Open a file in binary mode with consisten filesystem errors."""
    try:
        return path.open("rb")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: '{path}'") from e
    except PermissionError as e:
        raise PermissionError(f"Insufficient permissions to read file: '{path}'") from e

def _p(p: PathLike) -> Any:
    return p if isinstance(p, Path) else Path(p)

def parse_json(path: PathLike):
    path = _p(path)
    with _open_rb(path) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse '{path.name}' as JSON\n") from None

def parse_yaml(path: PathLike):
    path = _p(path)
    with _open_rb(path) as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError:
            raise ValueError(f"Failed to parse '{path.name}' as YAML\n") from None

def parse_toml(path: PathLike):
    path = _p(path)
    with _open_rb(path) as f:
        try:
            return tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"{path} is not valid TOML: {e}") from None

PARSERS: Mapping[str, ParserFn] = {
    "json": parse_json,
    "yaml": parse_yaml,
    "yml": parse_yaml,
    "toml": parse_toml
}

def infer_filetype(path: str):
    ext = _p(path).suffix.lower().lstrip(".")
    if ext not in PARSERS:
        raise ValueError(f"Unsupported file extension: .{ext}")
    return ext

def parse_config(path: PathLike, *, fmt: str | None = None) -> Any:
    path = _p(path)
    fmt = (fmt or infer_filetype(path)).lower()
    try:
        return PARSERS[fmt](path)
    except KeyError as e:
        raise ValueError(f"Unsupported format '{fmt}'") from e
    
