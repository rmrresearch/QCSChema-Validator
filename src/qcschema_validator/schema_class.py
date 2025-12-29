import inspect
from pydantic import BaseModel
import qcelemental.models.v2 as qc_models

schemas = {}

# Grabs all the models from QCElemental
for name, obj in vars(qc_models).items():
    if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
        schemas[name] = obj



def print_class_data(cls: type, tab = ""):
    optional = []
    required = []
    for name, field in cls.model_fields.items():  # ty:ignore[unresolved-attribute]
        if field.is_required():
            required.append((name, field.annotation))
        else:
            optional.append((name, field.annotation))
        if isinstance(field.annotation, type) and issubclass(field.annotation, BaseModel):
            tab += "\t"
            print_class_data(field.annotation, tab)
    print(tab + "Required: ")
    for (name, field_type) in required:
        print(tab + f"\t{name} {field_type}")
    print(tab + "Optional: ")
    for (name, field_type) in optional:
        print(tab + f"\t{name} {field_type}")
