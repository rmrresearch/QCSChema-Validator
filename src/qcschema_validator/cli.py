from __future__ import annotations

import argparse
from typing import Sequence

from .parsing import PARSERS, parse_config
from .validate import validate_data_against_schemas

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

def build_parser() -> argparse.ArgumentParser:
    argparse_config = {
        "prog": "qcschema_validator",
        "description": "QCSchema Validation Tool",
    }
    p = argparse.ArgumentParser(**argparse_config)
    p.add_argument("input_file", metavar="[FILE]", type=str, help="File to be validated")
    p.add_argument("--format", "-f", type=str, choices=sorted(PARSERS.keys()), help="Input file format")
    p.add_argument("--output-file", "-o", type=str, help="Write report to this file (optional)")
    p.add_argument("--out-format", type=str, choices=sorted(PARSERS.keys()), help="Output format (if writing a report)")
    p.add_argument("--verbose", "-v", action="store_true", help="Print full schema coverage score")
    return p

def _print_verbose(title: str, cov: dict, vals: dict) -> None:
    print(title)
    for key, ok in cov.items():
        color = GREEN if ok else RED
        print(f"\t{key}: {color}{ok}{RESET}")
        print(f"\t\tData: {vals[key]}")

def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    data = parse_config(args.input_file, fmt=args.format)

    result = validate_data_against_schemas(data)

    print(f"Schema under scrutiny: {result.schema_name}")

    if args.verbose:
        _print_verbose("Required Value Coverage:", result.required_cov, result.required_vals)
    print(f"Coverage of Required Values: {result.required_score:.0%}")

    if args.verbose:
        _print_verbose("Optional Value Coverage:", result.optional_cov, result.optional_vals)
    print(f"Coverage of Optional Values: {result.optional_score:.0%}")

    return 0
