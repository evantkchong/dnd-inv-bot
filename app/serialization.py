from pydantic import BaseModel

def persist(model: BaseModel) -> None:
    json_str = model.model_dump_json(indent=4)
    with open(model._filepath, "w") as f:
        f.write(json_str)

def load(model: BaseModel) -> BaseModel:
    filepath = model._filepath
    with open(filepath) as f:
        json_str = f.read()
    if json_str != "":
        loaded_model = model.model_validate_json(json_str, strict=False)
        loaded_model._filepath = filepath
        return loaded_model
    return model
