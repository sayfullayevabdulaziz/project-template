import os
import subprocess
from pathlib import Path

import pytest

from conftest import generate, make_template


def git(dest: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(dest), *args], capture_output=True, text=True, check=True).stdout.strip()


def assert_single_commit_repo(dest: Path):
    assert git(dest, "rev-list", "--count", "HEAD") == "1"
    assert git(dest, "status", "--porcelain") == ""
    assert git(dest, "log", "-1", "--format=%ae") == "ada@example.com"


@pytest.fixture
def no_flutter(monkeypatch):
    """PATH without any directory that provides flutter."""
    dirs = [d for d in os.environ["PATH"].split(os.pathsep) if not (Path(d) / "flutter").exists()]
    monkeypatch.setenv("PATH", os.pathsep.join(dirs))


@pytest.mark.parametrize("c", ["backend", "frontend", "mobile"])
def test_component_is_own_git_repo_with_one_commit(tmp_path, no_flutter, c):
    dest = tmp_path / "out"
    r = generate(make_template(tmp_path), dest, component=c)
    assert r.returncode == 0, r.stderr
    assert_single_commit_repo(dest)


def test_commit_works_without_global_git_identity(tmp_path):
    dest = tmp_path / "out"
    r = generate(make_template(tmp_path), dest, component="backend", no_git_identity=True)
    assert r.returncode == 0, r.stderr
    assert_single_commit_repo(dest)


def test_mobile_warns_without_flutter_and_still_succeeds(tmp_path, no_flutter):
    r = generate(make_template(tmp_path), tmp_path / "out", component="mobile")
    assert r.returncode == 0, r.stderr
    assert "make bootstrap" in r.stdout + r.stderr


def test_mobile_runs_make_bootstrap_when_flutter_on_path(tmp_path):
    stub = tmp_path / "bin"
    stub.mkdir()
    flutter = stub / "flutter"
    flutter.write_text("#!/bin/sh\nexit 0\n")
    flutter.chmod(0o755)
    tpl = make_template(tmp_path, overlay={"template/mobile/Makefile": "bootstrap:\n\t@echo ran > bootstrapped.txt\n"})
    dest = tmp_path / "out"
    r = generate(tpl, dest, component="mobile", path_prepend=[stub])
    assert r.returncode == 0, r.stderr
    assert (dest / "bootstrapped.txt").exists()
    assert "bootstrapped.txt" in git(dest, "ls-files").splitlines()


def test_other_components_unaffected_by_missing_flutter(tmp_path, no_flutter):
    r = generate(make_template(tmp_path), tmp_path / "out", component="backend")
    assert r.returncode == 0, r.stderr


def test_tasks_do_not_run_on_update(tmp_path):
    tpl = make_template(tmp_path, tag="v0.1.0")
    dest = tmp_path / "out"
    r = generate(tpl, dest, component="backend")
    assert r.returncode == 0, r.stderr
    (dest / ".git" / "marker").write_text("x")
    before = git(dest, "rev-list", "--count", "HEAD")

    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    (tpl / "template/backend/new.txt").write_text("new\n")
    subprocess.run(["git", "-C", str(tpl), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tpl), *ident, "commit", "-q", "-m", "add new"], check=True)
    subprocess.run(["git", "-C", str(tpl), *ident, "tag", "v0.1.1"], check=True)

    r = subprocess.run(
        ["copier", "update", "--trust", "--defaults", "--vcs-ref", "v0.1.1"],
        cwd=dest, capture_output=True, text=True,
        env=os.environ | {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"},
    )
    assert r.returncode == 0, r.stderr
    assert (dest / "new.txt").exists()
    assert git(dest, "rev-list", "--count", "HEAD") == before == "1"
    assert (dest / ".git" / "marker").exists()
    assert not (dest / "uv.lock").exists()
