import pytest
from pathlib import Path
import subprocess
import difflib

exe = "qcschema-validator"

def run_validator(filename: str):
    args = [filename]
    data = subprocess.run(
        args=args,
        executable=exe,
        # stdout=subprocess.PIPE,
        # stderr=subprocess.PIPE,
        capture_output=True,
        text=True
    )
    return data.stdout

good_xml = run_validator("known_good.xml")
good_json = run_validator("known_good.json")

diff = difflib.unified_diff(
    good_xml.splitlines(),
    good_json.splitlines(),
    fromfile="old.txt",
    tofile="new.txt",
    lineterm=""
)
print("\n".join(diff))

test_files = list(Path("./").glob("known_*"))

@pytest.mark.parametrize('file', test_files)
def test_qcschema_validator(file):
    filename = str(file.resolve())
    result = run_validator(filename)
    assert result == 0
