import json

import pydantic

from http_config import HTTPConfig


class Config(pydantic.BaseModel):
    http: HTTPConfig


def main() -> None:
    main_model_schema = Config.model_json_schema()
    print(json.dumps(main_model_schema, indent=4))


if __name__ == "__main__":
    main()
