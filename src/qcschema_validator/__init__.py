# qcschema_validator/__init__.py
from .parsing import parse_config, PARSERS
from .validate import validate_data_against_schemas, CoverageResult


__all__ = [
    "parse_config",
    "PARSERS",
    "validate_data_against_schemas",
    "CoverageResult"
]


# if len(sys.argv) == 1:
#     parser.print_help()
#     sys.exit(1)
