# QCSchema-Validator

> **Status**: under active development — not yet production-ready.

A command-line tool that validates quantum chemistry (QC) data files against
the [QCSchema](https://github.com/MolSSI/QCElemental) standard and reports
how much of the standard a given file implements.

## Contents

- [Installation](#installation)
- [Usage](#usage)
  - [Validate mode](#validate-mode-default)
  - [Coverage mode](#coverage-mode)
  - [Subset validation](#subset-validation)
- [Web interface](#web-interface)
- [Using in your CI pipeline](#using-in-your-ci-pipeline)
- [CLI reference](#cli-reference)

## Installation

```bash
pip install git+https://github.com/rmrresearch/QCSChema-Validator.git
```

**Status**: PyPI deployment is coming when QCSchema V2 is released.

## Usage

```
qcschema-validator FILE [--validate | --coverage] 
                        [--format {json,toml,yaml,yml}] 
                        [--verbose]
```

The tool runs in one of two modes selected by a flag. `--validate` is the
default. The file format is inferred from the extension; use `--format` to
override it.

### Validate mode (default)

Check whether a file is compliant with QCSchema. The tool exits **0** if all
required fields are present and correctly typed, **1** otherwise.

```bash
qcschema-validator molecule.json
# or equivalently:
qcschema-validator --validate molecule.json
```

Example output for a compliant file:

```
PASS: molecule.json (qcschema_molecule)
```

Example output for a non-compliant file:

```
FAIL: molecule.json (qcschema_molecule)
```

Add `--verbose` to see which required fields failed when the file does not
pass:

```bash
qcschema-validator --validate --verbose molecule.json
```

**Failure modes and their symptoms:**

| Problem | Symptom |
|---|---|
| File is not valid SDF (e.g., malformed JSON) | Non-zero exit code, error message printed |
| File has no recognized `schema_name` field | Non-zero exit code, error message printed |
| A required field is missing or has the wrong type | Exit code 1, `FAIL` printed |

YAML and TOML files are also supported:

```bash
qcschema-validator molecule.yaml
qcschema-validator molecule.toml
```

To validate a file whose extension does not match its actual format:

```bash
qcschema-validator molecule.txt --format json
```

### Coverage mode

Report what fraction of the QCSchema standard a file implements. The tool
exits **0** if required coverage is 100%, **1** otherwise.

```bash
qcschema-validator --coverage molecule.json
```

Example output:

```
Schema: qcschema_molecule
Coverage of Required Values: 100%
Coverage of Optional Values: 85%
```

Add `--verbose` to see a per-field breakdown for both required and optional
fields. Fields that fail their type check are printed in red; passing fields
in green.

```bash
qcschema-validator --coverage --verbose molecule.json
```

Example output:

```
Schema: qcschema_molecule
Required fields:
        schema_name: True
                Data: qcschema_molecule
        schema_version: True
                Data: 3
        symbols: True
                Data: ['He', 'He']
        geometry: True
                Data: [0.0, 0.0, 0.0, 0.0, 0.0, 5.0]
Coverage of Required Values: 100%
Optional fields:
        molecular_charge: True
                Data: 0.0
        fix_com: False
                Data: not_a_bool
        ...
Coverage of Optional Values: 85%
```

Required coverage measures the fraction of mandatory fields that are present
and correctly typed. Optional coverage measures the same for optional fields
the file chose to provide.

### Subset validation

A QC package may intentionally support only a subset of QCSchema's optional
fields. Use a subset file to declare which optional fields your package claims
to implement — declared fields are then held to the same standard as required
fields.

Create a JSON, YAML, or TOML file mapping schema names to lists of field names:

```json
{
  "qcschema_molecule": ["molecular_charge", "molecular_multiplicity", "fragments"]
}
```

Pass it with `--subset`:

```bash
qcschema-validator --validate molecule.json --subset subset.json
qcschema-validator --coverage molecule.json --subset subset.json --verbose
```

In coverage mode, a third line appears for declared fields:

```
Schema: qcschema_molecule
Coverage of Required Values: 100%
Coverage of Declared Optional Values: 67%
Coverage of Optional Values: 80%
```

The tool exits 1 if any declared optional field is missing or has the wrong
type, in addition to the usual required-field check. Undeclared optional
fields are never penalized. A warning is printed for any declared field name
that does not exist in the schema.

## Web interface

A browser-based validator is available at the repository's GitHub Pages URL.
Upload any `.json`, `.yaml`, `.yml`, or `.toml` file and choose between
validate and coverage modes — validation runs locally in your browser via
[Pyodide](https://pyodide.org) and no data leaves your machine.

## Using in your CI pipeline

Add QCSchema validation to any GitHub Actions workflow with a single step:

```yaml
jobs:
  qcschema:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: rmrresearch/QCSChema-Validator/.github/actions/validate@main
        with:
          file: output/result.json
```

The action installs the tool, runs the validator, and fails the job if
validation does not pass. Results are written to the workflow's step summary
so they are visible in the Actions UI without inspecting raw logs.

All CLI options are available as action inputs:

```yaml
- uses: rmrresearch/QCSChema-Validator/.github/actions/validate@main
  with:
    file: output/result.json
    mode: coverage          # 'validate' (default) or 'coverage'
    subset: subset.json     # optional: path to a subset file
    verbose: 'true'         # optional: show per-field detail
    format: json            # optional: force file format
    python-version: '3.12'  # optional: Python version (default 3.12)
```

Pin to a specific release tag instead of `@main` for reproducible builds:

```yaml
uses: rmrresearch/QCSChema-Validator/.github/actions/validate@v1.0.0
```

## CLI reference

| Flag | Short | Description |
|---|---|---|
| `--validate` | | (default) Exit 0 if all required and declared optional fields pass, 1 otherwise |
| `--coverage` | | Print coverage percentages; exit 0 if required and declared optional coverage is 100% |
| `--subset FILE` | | Subset file declaring which optional fields must be present |
| `--format FORMAT` | `-f` | Force input format (`json`, `yaml`, `yml`, `toml`) |
| `--verbose` | `-v` | Print per-field pass/fail detail |
| `--output-file FILE` | `-o` | Write the report to a file instead of stdout |
| `--out-format FORMAT` | | Format for the output file |
