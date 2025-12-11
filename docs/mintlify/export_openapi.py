"""Export FastAPI OpenAPI schema for Mintlify reference."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi

try:
    from sardis_api.main import create_app
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Cannot import sardis_api. Ensure packages are installed (pip install -e packages/sardis-api)."
    ) from exc


def export(schema_path: Path) -> None:
    app = create_app()
    schema = get_openapi(
        title="Sardis API",
        version="1.0.0",
        description="Payment execution layer for AP2/TAP agents",
        routes=app.routes,
    )
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(json.dumps(schema, indent=2))
    print(f"OpenAPI schema exported to {schema_path}")


def main() -> None:
    root = Path(__file__).resolve().parent
    output = root / "reference" / "openapi.json"
    export(output)


if __name__ == "__main__":
    main()


