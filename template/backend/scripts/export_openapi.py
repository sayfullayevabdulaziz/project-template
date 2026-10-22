"""Write (or --check) the per-surface OpenAPI specs under openapi/."""

import argparse
import json
import os
import sys
from pathlib import Path

# app.core.broker builds its broker from get_settings() at import time; set values explicitly
# (no connections are made) so the export never depends on the caller's environment.
_DATABASE_URL = "postgresql+asyncpg://u:p@localhost/db"
_REDIS_URL = "redis://localhost:6379/0"
os.environ.update(
    APP_ENV="test",
    APP_JWT_SECRET="x" * 32,
    APP_DATABASE_URL=_DATABASE_URL,
    APP_REDIS_URL=_REDIS_URL,
)

from pydantic import SecretStr  # noqa: E402

from app.api.surfaces import SURFACES, surface_openapi  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

DEFAULT_OUT = Path(__file__).resolve().parent.parent / "openapi"


def render() -> dict[str, str]:
    app = create_app(
        Settings(
            env="test",
            jwt_secret=SecretStr("x" * 32),
            database_url=_DATABASE_URL,
            redis_url=_REDIS_URL,
        )
    )
    return {
        f"{s.name}.json": json.dumps(surface_openapi(app, s), indent=2, sort_keys=True) + "\n"
        for s in SURFACES
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="exit 1 if files differ; write nothing"
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output directory")
    args = parser.parse_args()

    specs = render()
    if args.check:
        stale = [
            n
            for n, text in specs.items()
            if not (args.out / n).exists() or (args.out / n).read_text() != text
        ]
        for n in stale:
            print(f"differs: {args.out / n}")
        return 1 if stale else 0

    args.out.mkdir(parents=True, exist_ok=True)
    for n, text in specs.items():
        (args.out / n).write_text(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
