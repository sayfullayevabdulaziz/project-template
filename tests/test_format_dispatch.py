import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPOS = ("backend", "frontend", "mobile")


@pytest.fixture
def root(ws, tmp_path) -> Path:
    dest = tmp_path / "root"
    shutil.copytree(ws, dest, symlinks=True)
    for repo in REPOS:
        stub(dest, repo)
    return dest


def stub(root: Path, repo: str, body: str = "") -> None:
    f = root / repo / ".claude/hooks/format.sh"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f'#!/bin/bash\ncat >> "{root}/{repo}.log"\n'
        f'echo "$(pwd -P)|$CLAUDE_PROJECT_DIR" >> "{root}/{repo}.env"\n{body}\n')
    f.chmod(0o755)


def run(root: Path, payload: str, env: dict | None = None):
    return subprocess.run(
        ["bash", str(root / ".claude/hooks/format-dispatch.sh")],
        input=payload, capture_output=True, text=True, env=env,
    )


def payload(path: str) -> str:
    return json.dumps({"tool_input": {"file_path": path}})


def logs(root: Path) -> dict[str, str]:
    return {r: (root / f"{r}.log").read_text() if (root / f"{r}.log").exists() else "" for r in REPOS}


def test_settings_json_valid_and_wired(ws):
    s = json.loads((ws / ".claude/settings.json").read_text())
    entry = s["hooks"]["PostToolUse"][0]
    assert entry["matcher"] == "Edit|Write"
    assert "format-dispatch.sh" in entry["hooks"][0]["command"]
    assert {"Bash(make:*)", "Bash(docker compose:*)"} <= set(s["permissions"]["allow"])
    assert not {"Bash(git branch:*)", "Bash(git -C:*)"} & set(s["permissions"]["allow"])


def test_dispatches_backend_file_with_same_stdin(root):
    p = payload(f"{root}/backend/src/app/x.py")
    r = run(root, p)
    assert r.returncode == 0
    assert logs(root) == {"backend": p, "frontend": "", "mobile": ""}


@pytest.mark.parametrize("repo", ["frontend", "mobile"])
def test_dispatches_frontend_and_mobile_by_prefix(root, repo):
    p = payload(f"{root}/{repo}/x.ts")
    assert run(root, p).returncode == 0
    assert logs(root) == {r: (p if r == repo else "") for r in REPOS}


def test_sibling_prefix_not_matched(root):
    assert run(root, payload(f"{root}/backend-old/x.py")).returncode == 0
    assert set(logs(root).values()) == {""}


@pytest.mark.parametrize("path", ["PROJECT.md", "/etc/hosts"])
def test_outside_repos_noop(root, path):
    p = path if path.startswith("/") else f"{root}/{path}"
    assert run(root, payload(p)).returncode == 0
    assert set(logs(root).values()) == {""}


def test_dotdot_escape_noop(root):
    assert run(root, payload(f"{root}/backend/../PROJECT.md")).returncode == 0
    assert set(logs(root).values()) == {""}


def test_missing_format_script_noop(root):
    (root / "backend/.claude/hooks/format.sh").unlink()
    r = run(root, payload(f"{root}/backend/x.py"))
    assert r.returncode == 0 and r.stderr == ""


@pytest.mark.parametrize("stdin", ["not json {", "", "[]", '{"tool_input":{"file_path":5}}'])
def test_garbage_stdin_and_empty_stdin_exit_zero(root, stdin):
    r = run(root, stdin)
    assert r.returncode == 0
    assert set(logs(root).values()) == {""}


def test_falls_back_to_python3_without_jq(root, tmp_path):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name in ("python3", "bash", "dirname", "cat"):
        src = Path(sys.executable).resolve() if name == "python3" else shutil.which(name)
        (bin_ / name).symlink_to(src)
    env = {"PATH": str(bin_)}
    assert shutil.which("jq", path=str(bin_)) is None
    p = payload(f"{root}/backend/src/x.py")
    assert run(root, p, env=env).returncode == 0
    assert logs(root)["backend"] == p
    assert run(root, payload(f"{root}/backend-old/x.py"), env=env).returncode == 0
    assert logs(root)["backend"] == p  # sibling prefix still not dispatched


def test_failing_repo_formatter_does_not_propagate(root):
    stub(root, "backend", "exit 7")
    assert run(root, payload(f"{root}/backend/x.py")).returncode == 0


def test_relative_file_path_resolved_against_root(root):
    p = payload("backend/src/x.py")
    assert run(root, p).returncode == 0
    assert logs(root)["backend"] == p


def test_script_is_executable_in_generated_tree(ws):
    assert os.access(ws / ".claude/hooks/format-dispatch.sh", os.X_OK)


def test_formatter_runs_in_its_repo_dir(root):
    assert run(root, payload(f"{root}/backend/x.py")).returncode == 0
    repo = str((root / "backend").resolve())
    assert (root / "backend.env").read_text().strip() == f"{repo}|{repo}"
