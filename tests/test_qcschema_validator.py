import sys
import subprocess
import warnings
from pathlib import Path

import pytest
from qcschema_validator.parsing import parse_config
from qcschema_validator.validate import validate_data_against_schemas


TEST_DIR = Path(__file__).resolve().parent
GOOD_FILES = sorted(TEST_DIR.glob("*good*"))
BAD_FILES = sorted(TEST_DIR.glob("*bad*"))


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "qcschema_validator", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# validate mode (default)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("file", GOOD_FILES)
def test_validate_good_files_exit_zero(file):
    proc = run_cli([str(file)])
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


@pytest.mark.parametrize("file", GOOD_FILES)
def test_validate_explicit_flag_good_files_exit_zero(file):
    proc = run_cli(["--validate", str(file)])
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


@pytest.mark.parametrize("file", BAD_FILES)
def test_validate_bad_files_exit_nonzero(file):
    proc = run_cli([str(file)])
    assert proc.returncode != 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


@pytest.mark.parametrize("file", GOOD_FILES)
def test_validate_output_contains_pass(file):
    proc = run_cli([str(file)])
    assert "PASS" in proc.stdout


@pytest.mark.parametrize("file", BAD_FILES)
def test_validate_output_contains_fail(file):
    proc = run_cli([str(file)])
    assert "FAIL" in proc.stdout


# ---------------------------------------------------------------------------
# coverage mode
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("file", GOOD_FILES)
def test_coverage_good_files_exit_zero(file):
    proc = run_cli(["--coverage", str(file)])
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


@pytest.mark.parametrize("file", BAD_FILES)
def test_coverage_bad_files_exit_nonzero(file):
    proc = run_cli(["--coverage", str(file)])
    assert proc.returncode != 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


@pytest.mark.parametrize("file", GOOD_FILES)
def test_coverage_output_contains_percentages(file):
    proc = run_cli(["--coverage", str(file)])
    assert "Coverage of Required Values:" in proc.stdout
    assert "Coverage of Optional Values:" in proc.stdout


# ---------------------------------------------------------------------------
# mutual exclusion
# ---------------------------------------------------------------------------

def test_validate_and_coverage_are_mutually_exclusive():
    proc = run_cli(["--validate", "--coverage", "dummy.json"])
    assert proc.returncode != 0
    assert "error" in (proc.stderr + proc.stdout).lower()


# ---------------------------------------------------------------------------
# general
# ---------------------------------------------------------------------------

def test_cli_no_args_shows_help():
    proc = run_cli([])
    assert proc.returncode != 0
    assert "usage" in (proc.stderr + proc.stdout).lower()


@pytest.mark.parametrize("file", GOOD_FILES)
def test_library_validate_good_files(file: Path):
    data = parse_config(file)
    result = validate_data_against_schemas(data)
    assert result.schema_name == data["schema_name"]
    assert result.required_score == 1.0
    assert 0.0 <= result.optional_score <= 1.0


# ---------------------------------------------------------------------------
# nested schema (AtomicInput) coverage
# ---------------------------------------------------------------------------
# AtomicInput has two required fields (molecule, specification) and four
# optional ones (id, schema_name, schema_version, provenance). The tests
# below verify that coverage is computed at the correct depth: the tool
# validates each top-level field as a whole Pydantic model but does not
# recurse into sub-fields for coverage purposes.

_ATOMIC_GOOD = TEST_DIR / "known_good_atomic_input.json"
_ATOMIC_BAD  = TEST_DIR / "known_bad_atomic_input.json"


def test_nested_schema_required_fields_are_molecule_and_specification():
    data = parse_config(_ATOMIC_GOOD)
    result = validate_data_against_schemas(data)
    assert result.schema_name == "qcschema_atomic_input"
    assert set(result.required_cov.keys()) == {"molecule", "specification"}


def test_nested_schema_valid_nested_fields_show_true():
    data = parse_config(_ATOMIC_GOOD)
    result = validate_data_against_schemas(data)
    assert result.required_cov["molecule"] is True
    assert result.required_cov["specification"] is True
    assert result.required_score == 1.0


def test_nested_schema_schema_name_is_optional_not_required():
    # schema_name has a default value so Pydantic marks it as not required;
    # it should appear in optional_cov, not required_cov.
    data = parse_config(_ATOMIC_GOOD)
    result = validate_data_against_schemas(data)
    assert "schema_name" not in result.required_cov
    assert "schema_name" in result.optional_cov


def test_nested_schema_invalid_nested_field_shows_false():
    # The bad fixture omits `driver` from specification, which is required by
    # AtomicSpecification. TypeAdapter(AtomicSpecification).validate_python()
    # raises ValidationError, so matches() returns False for that field.
    data = parse_config(_ATOMIC_BAD)
    result = validate_data_against_schemas(data)
    assert result.required_cov["specification"] is False
    assert result.required_score < 1.0


# ---------------------------------------------------------------------------
# allowlist (subset) mechanism
# ---------------------------------------------------------------------------
# known_good.json (qcschema_molecule) contains `molecular_charge` but not
# `identifiers`. Tests use these two fields to exercise present/absent cases.

_MOLECULE_GOOD = TEST_DIR / "known_good.json"
_SUBSET_PRESENT = TEST_DIR / "subset_molecule.json"          # declares molecular_charge
_SUBSET_MISSING = TEST_DIR / "subset_molecule_missing.json"  # declares identifiers (absent)


def test_no_allowlist_leaves_behavior_unchanged():
    data = parse_config(_MOLECULE_GOOD)
    result = validate_data_against_schemas(data)
    assert result.allowlisted_cov == {}
    assert result.allowlisted_score == 1.0


def test_allowlist_declared_field_present_shows_true():
    data = parse_config(_MOLECULE_GOOD)
    result = validate_data_against_schemas(data, allowlist={"molecular_charge"})
    assert result.allowlisted_cov == {"molecular_charge": True}
    assert result.allowlisted_score == 1.0


def test_allowlist_declared_field_absent_shows_false():
    data = parse_config(_MOLECULE_GOOD)
    result = validate_data_against_schemas(data, allowlist={"identifiers"})
    assert result.allowlisted_cov == {"identifiers": False}
    assert result.allowlisted_score == 0.0


def test_allowlist_does_not_affect_optional_cov():
    data = parse_config(_MOLECULE_GOOD)
    result_without = validate_data_against_schemas(data)
    result_with = validate_data_against_schemas(data, allowlist={"molecular_charge"})
    # molecular_charge should move from optional_cov to allowlisted_cov
    assert "molecular_charge" in result_without.optional_cov
    assert "molecular_charge" not in result_with.optional_cov
    assert "molecular_charge" in result_with.allowlisted_cov


def test_allowlist_unknown_field_emits_warning():
    data = parse_config(_MOLECULE_GOOD)
    with pytest.warns(UserWarning, match="not_a_real_field"):
        validate_data_against_schemas(data, allowlist={"not_a_real_field"})


# CLI-level subset tests

def test_cli_subset_present_field_exits_zero():
    proc = run_cli([str(_MOLECULE_GOOD), "--subset", str(_SUBSET_PRESENT)])
    assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


def test_cli_subset_missing_field_exits_nonzero():
    proc = run_cli([str(_MOLECULE_GOOD), "--subset", str(_SUBSET_MISSING)])
    assert proc.returncode != 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"


def test_cli_subset_coverage_shows_declared_line():
    proc = run_cli(["--coverage", str(_MOLECULE_GOOD), "--subset", str(_SUBSET_PRESENT)])
    assert "Coverage of Declared Optional Values:" in proc.stdout
