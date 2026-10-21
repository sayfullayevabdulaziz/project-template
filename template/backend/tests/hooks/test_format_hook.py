import json
import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "format.sh"
TMP = ROOT / "tests" / "_tmp"
UGLY = "x   =   {'a':1,\n  'b':2}\n"


@pytest.fixture
def tmp_inside_repo() -> Iterator[Path]:
    TMP.mkdir(exist_ok=True)
    try:
        yield TMP
    finally:
        shutil.rmtree(TMP, ignore_errors=True)


def run_hook(stdin: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)}
    return subprocess.run(  # noqa: S603
        [str(HOOK)], input=stdin, text=True, capture_output=True, cwd=ROOT, env=env, timeout=120
    )


def payload(path: Path) -> str:
    return json.dumps({"tool_input": {"file_path": str(path)}})


def test_formats_python_file_inside_repo(tmp_inside_repo: Path) -> None:
    f = tmp_inside_repo / "ugly.py"
    f.write_text(UGLY)
    assert run_hook(payload(f)).returncode == 0
    assert f.read_text() == 'x = {"a": 1, "b": 2}\n'


def test_ignores_non_python(tmp_inside_repo: Path) -> None:
    f = tmp_inside_repo / "note.md"
    f.write_text(UGLY)
    assert run_hook(payload(f)).returncode == 0
    assert f.read_text() == UGLY


def test_ignores_file_outside_repo(tmp_path: Path) -> None:
    f = tmp_path / "ugly.py"
    f.write_text(UGLY)
    assert run_hook(payload(f)).returncode == 0
    assert f.read_text() == UGLY


@pytest.mark.parametrize("stdin", ["not json", "", "{}", '{"tool_input": {"file_path": 5}}'])
def test_exit_zero_on_garbage_stdin(stdin: str) -> None:
    assert run_hook(stdin).returncode == 0


def test_exit_zero_when_file_missing(tmp_inside_repo: Path) -> None:
    assert run_hook(payload(tmp_inside_repo / "missing.py")).returncode == 0
