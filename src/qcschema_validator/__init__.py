import argparse
import json

argparse_config = {
    "prog": "qcschema_validator",
    "description": "QCSchema Validation Tool",
}

parser = argparse.ArgumentParser(**argparse_config)
parser.add_argument("input_file", type=argparse.FileType("rb"))


args = parser.parse_args()
data = json.loads(args.input_file.read())
print(data)


def main() -> None:
    print("Hello from qcschema-validator!")
