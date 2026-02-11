import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import get_origin

import numpy as np
import yaml
from pydantic import ConfigDict, TypeAdapter, ValidationError

from .schema_class import schemas

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

argparse_config = {
    "prog": "qcschema_validator",
    "description": "QCSchema Validation Tool",
}

def parse_json(file_path: str):
    path = Path(file_path)
    try:
        with path.open('rb') as f:
            return json.load(f)

    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: '{path}'") from e

    except PermissionError as e:
        raise PermissionError(f"Insufficient permissions to read file: '{path}'") from e

    except json.JSONDecodeError:
        raise ValueError(f"Failed to parse '{path.name}' as JSON\n") from None

def parse_yaml(file_path: str):
    path = Path(file_path)
    try:
        with path.open('rb') as f:
            return yaml.safe_load(f)

    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: '{path}'") from e

    except PermissionError as e:
        raise PermissionError(f"Insufficient permissions to read file: '{path}'") from e

    except yaml.YAMLError:
        raise ValueError(f"Failed to parse '{path.name}' as YAML\n") from None

def parse_toml(file_path: str):
    path = Path(file_path)
    try:
        with path.open('rb') as f:
            return tomllib.load(f)

    except FileNotFoundError as e:
        raise FileNotFoundError(f"File not found: '{path}'") from e

    except PermissionError as e:
        raise PermissionError(f"Insufficient permissions to read file: '{path}'") from e

    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"{path} is not valid TOML: {e}") from None

PARSERS = {
    "json": parse_json,
    "yaml": parse_yaml,
    "toml": parse_toml
}

def infer_filetype(file_path: str):
    ext = Path(file_path).suffix.lower().lstrip(".")
    if ext not in PARSERS.keys():
        raise argparse.ArgumentTypeError("Yeah no way I'm parsing that file")
    return ext

parser = argparse.ArgumentParser(**argparse_config)
parser.add_argument(
                    "input_file",
                    metavar="[FILE]",
                    type=str,
                    help="File to be validated"
                )
parser.add_argument(
                    "--format",
                    "-f",
                    type=str,
                    choices=PARSERS.keys(),
                    help="Input file format"
                )
parser.add_argument(
                    "--output-file",
                    "-o",
                    type=str,
                    choices=PARSERS.keys(),
                    help="Input file format"
                )
parser.add_argument(
                    "--out-format",
                    type=str,
                    choices=PARSERS.keys(),
                    help="Input file format"
                )
parser.add_argument(
                    "--verbose",
                    "-v",
                    action="store_true",
                    help="Print full schema coverage score"
                )

if len(sys.argv) == 1:
    parser.print_help()
    sys.exit(1)

args = parser.parse_args()
if args.format is None:
    ext = infer_filetype(args.input_file)
    parser_func = PARSERS[ext]
else:
    parser_func = PARSERS[args.format]

data = parser_func(args.input_file)

def matches(value, annotation) -> bool:
    ta = TypeAdapter(annotation, config=ConfigDict(arbitrary_types_allowed=True))
    try:
        if get_origin(annotation) == np.ndarray or annotation is np.ndarray:
            ta.validate_python(np.asarray(value))
        else:
            ta.validate_python(value)
        return True
    except ValidationError:
        return False

def main() -> None:
    for name, obj in schemas.items():
        if 'schema_name' in obj.model_fields.keys():
            if obj.model_fields['schema_name'].default == data['schema_name']:
                schema_being_validated = data['schema_name']
                required_cov = {}
                optional_cov = {}
                required_vals = {}
                optional_vals = {}
                for name, field in obj.model_fields.items():
                    if name not in data.keys():
                        if field.is_required():
                            required_cov[name] =  False
                            required_vals[name] =  None
                            continue
                        else:
                            optional_cov[name] = False
                            optional_vals[name] = None
                            continue
                    if field.is_required():
                        required_cov[name] = matches(data[name], field.annotation)
                        required_vals[name] = data[name]
                    else:
                        optional_cov[name] = matches(data[name], field.annotation)
                        optional_vals[name] = data[name]
                        
    print(f"Schema under scrutiny: {schema_being_validated}")
    if args.verbose:
        print("Required Value Coverage:")
        for key, value in required_cov.items():
            color = GREEN
            if not value:
                color = RED
            print(f"\t{key}: {color}{value}{RESET}")
            print(f"\t\tData: {required_vals[key]}", )
    print(f"Coverage of Required Values: {sum(required_cov.values()) / len(required_cov.values()):.0%}")
    if args.verbose:
        print("Optional Value Coverage:")
        for key, value in optional_cov.items():
            color = GREEN
            if not value:
                color = RED
            print(f"\t{key}: {color}{value}{RESET}")
            print(f"\t\tData: {optional_vals[key]}", )
    print(f"Coverage of Optional Values: {sum(optional_cov.values()) / len(optional_cov.values()):.0%}")
