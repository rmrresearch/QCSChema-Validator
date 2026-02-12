import sys
import subprocess
from pathlib import Path

import pytest

TEST_DIR = Path(__file__).resolve().parent
GOOD_FILES = sorted(TEST_DIR.glob("*good*"))
BAD_FILES = sorted(TEST_DIR.glob("*bad*"))

def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "qcschema_validator", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


@pytest.mark.parametrize('file', GOOD_FILES)
def test_cli_good_files_exit_zero(file):
    proc = run_cli([str(file)])
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

def test_cli_no_args_shows_help():
    proc = run_cli([])
    assert proc.returncode != 0
    assert "usage" in (proc.stderr + proc.stdout).lower()

from qcschema_validator.parsing import parse_config
from qcschema_validator.validate import validate_data_against_schemas

@pytest.mark.parametrize("file", GOOD_FILES)
def test_library_validate_good_files(file: Path):
    data = parse_config(file)
    result = validate_data_against_schemas(data)
    assert result.schema_name == data["schema_name"]
    assert 0.0 <= result.required_score <= 1.0
    assert 0.0 <= result.optional_score <= 1.0
    
