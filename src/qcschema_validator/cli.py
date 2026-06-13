from __future__ import annotations

import argparse
from typing import Sequence

from .parsing import PARSERS, parse_config
from .validate import CoverageResult, validate_data_against_schemas

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="qcschema-validator",
        description="QCSchema Validation Tool",
    )
    p.add_argument("input_file", metavar="FILE", type=str, help="File to validate")
    p.add_argument("--format", "-f", type=str, choices=sorted(PARSERS.keys()), help="Input file format (inferred from extension if omitted)")
    p.add_argument("--output-file", "-o", type=str, help="Write report to this file (optional)")
    p.add_argument("--out-format", type=str, choices=sorted(PARSERS.keys()), help="Output format (if writing a report)")
    p.add_argument("--verbose", "-v", action="store_true", help="Print per-field pass/fail detail")
    p.add_argument(
        "--subset", metavar="FILE",
        help="Subset file (JSON/YAML/TOML) declaring which optional fields must be present. "
             "Format: {\"<schema_name>\": [\"field1\", \"field2\", ...]}",
    )

    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--validate",
        dest="mode", action="store_const", const="validate",
        help="(default) Exit 0 if all required fields are present and correctly typed, 1 otherwise",
    )
    mode.add_argument(
        "--coverage",
        dest="mode", action="store_const", const="coverage",
        help="Print required and optional coverage percentages; exit 0 if required coverage is 100%%",
    )
    p.set_defaults(mode="validate")
    return p


def _print_fields(title: str, cov: dict, vals: dict) -> None:
    print(title)
    for key, ok in cov.items():
        color = GREEN if ok else RED
        print(f"\t{key}: {color}{ok}{RESET}")
        print(f"\t\tData: {vals[key]}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    data = parse_config(args.input_file, fmt=args.format)

    allowlist = None
    if args.subset:
        subset_data = parse_config(args.subset)
        declared = subset_data.get(data.get("schema_name", ""), [])
        allowlist = set(declared)

    result = validate_data_against_schemas(data, allowlist=allowlist)
    passed = result.required_score == 1.0 and result.allowlisted_score == 1.0

    if args.mode == "validate":
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {args.input_file} ({result.schema_name})")
        if args.verbose and not passed:
            _print_fields("Required fields:", result.required_cov, result.required_vals)
            if result.allowlisted_cov:
                _print_fields("Declared optional fields:", result.allowlisted_cov, result.allowlisted_vals)
    else:  # coverage
        print(f"Schema: {result.schema_name}")
        if args.verbose:
            _print_fields("Required fields:", result.required_cov, result.required_vals)
        print(f"Coverage of Required Values: {result.required_score:.0%}")
        if result.allowlisted_cov:
            if args.verbose:
                _print_fields("Declared optional fields:", result.allowlisted_cov, result.allowlisted_vals)
            print(f"Coverage of Declared Optional Values: {result.allowlisted_score:.0%}")
        if args.verbose:
            _print_fields("Optional fields:", result.optional_cov, result.optional_vals)
        print(f"Coverage of Optional Values: {result.optional_score:.0%}")

    return 0 if passed else 1
