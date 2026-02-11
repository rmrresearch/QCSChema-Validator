import pytest
from pathlib import Path
import subprocess

exe = "qcschema-validator"

def run_validator(filename: str):
    args = [exe, filename]
    data = subprocess.run(
        args=args,
        # executable=exe,
        # stdout=subprocess.PIPE,
        # stderr=subprocess.PIPE,
        capture_output=True,
        text=True
    )
    return data.stdout

test_files = list(Path(__file__).resolve().parent.glob("known_*"))

@pytest.mark.parametrize('file', test_files)
def test_qcschema_validator(file):
    filename = str(file.resolve())
    print(filename)
    result = run_validator(filename)
    print(result)
    # assert result == 0
