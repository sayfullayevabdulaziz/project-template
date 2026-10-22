import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "export_openapi.py"
SPECS = ["admin.json", "public.json"]


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=ROOT, check=False
    )


def test_export_is_deterministic(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    assert run("--out", str(a)).returncode == 0
    assert run("--out", str(b)).returncode == 0
    for name in SPECS:
        assert (a / name).read_bytes() == (b / name).read_bytes()


def test_committed_specs_are_up_to_date() -> None:
    result = run("--check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_check_fails_and_writes_nothing_when_stale(tmp_path: Path) -> None:
    (tmp_path / "admin.json").write_text("{}\n")
    result = run("--check", "--out", str(tmp_path))
    assert result.returncode == 1
    assert "admin.json" in result.stdout
    assert "public.json" in result.stdout  # missing counts as differing
    assert (tmp_path / "admin.json").read_text() == "{}\n"
    assert not (tmp_path / "public.json").exists()


def test_specs_are_valid_openapi_3() -> None:
    for name in SPECS:
        spec = json.loads((ROOT / "openapi" / name).read_text())
        assert spec["openapi"].startswith("3.")
        for item in spec["paths"].values():
            for op in item.values():
                assert re.match(r"^(auth|users|items)-", op["operationId"])


def test_spec_server_independent() -> None:
    for name in SPECS:
        spec = json.loads((ROOT / "openapi" / name).read_text())
        assert "servers" not in spec
