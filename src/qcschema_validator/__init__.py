import argparse
import json
import numpy as np
from .schema_class import schemas
from typing import get_origin
from pydantic import TypeAdapter,ConfigDict

argparse_config = {
    "prog": "qcschema_validator",
    "description": "QCSchema Validation Tool",
}

parser = argparse.ArgumentParser(**argparse_config)
parser.add_argument("input_file", type=argparse.FileType("rb"))


args = parser.parse_args()
data = json.loads(args.input_file.read())


def matches(value, annotation):
    ta = TypeAdapter(annotation, config=ConfigDict(arbitrary_types_allowed=True))
    try:
        if get_origin(annotation) == np.ndarray or annotation is np.ndarray:
            ta.validate_python(np.asarray(value))
            return True
        else:
            ta.validate_python(value)
            return True
    except:
        return False

def main() -> None:
    for name, obj in schemas.items():
        if 'schema_name' in obj.model_fields.keys():
            if obj.model_fields['schema_name'].default == data['schema_name']:
                required_vals = {}
                optional_vals = {}
                for name, field in obj.model_fields.items():
                    if name not in data.keys():
                        if field.is_required():
                            required_vals[name]: False
                            continue
                        else:
                            optional_vals[name] = False
                            continue
                    if field.is_required():
                        required_vals[name] = matches(data[name], field.annotation)
                    else:
                        optional_vals[name] = matches(data[name], field.annotation)
                        

    print("Required Value Coverage:")
    for key, value in required_vals.items():
            print("\t", key + ": ", value)
    print("Optional Value Coverage:")
    for key, value in optional_vals.items():
            print("\t", key + ": ", value)
