import os
import subprocess
import sys
from pathlib import Path

import pytest

SRC = str(Path(__file__).parent.parent / "src")


@pytest.mark.parametrize("module", ["app.api.admin", "app.api.public", "app.api.surfaces"])
def test_surface_modules_import_first_in_fresh_interpreter(module: str):
    env = {**os.environ, "PYTHONPATH": SRC}
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", f"import {module}"], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
