"""Write the OpenAPI document that the web client types are generated from."""

import json
import sys
from pathlib import Path

from app.config import Settings
from app.main import create_app


def render() -> str:
    app = create_app(Settings(database_url="sqlite://", auto_migrate=False))
    return json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    target = Path(__file__).resolve().parent.parent / "openapi.json"
    target.write_text(render())
    print(f"wrote {target}", file=sys.stderr)
