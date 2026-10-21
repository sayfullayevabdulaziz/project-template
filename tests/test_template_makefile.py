import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from conftest import REPO

needs_copier = pytest.mark.skipif(shutil.which("copier") is None, reason="copier not installed")
_GIT_ID = ["-c", "user.name=t", "-c", "user.email=t@t"]


def committed_clone(tmp_path: Path) -> Path:
    """Copy the template files (no .git) into a fresh committed repo, so nested copies can pin HEAD."""
    clone = tmp_path / "clone"
    shutil.copytree(
        REPO,
        clone,
        ignore=shutil.ignore_patterns(".git", ".venv", ".superpowers", "__pycache__", ".pytest_cache", "node_modules"),
    )
    git = ["git", "-C", str(clone)]
    subprocess.run(git + ["init", "-q", "-b", "main"], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + _GIT_ID + ["commit", "-q", "-m", "tpl"], check=True)
    return clone


def make(clone: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["make", "-C", str(clone), *args], capture_output=True, text=True)


@needs_copier
def test_make_test_template_refuses_dirty_tree(tmp_path):
    clone = committed_clone(tmp_path)
    (clone / "untracked.txt").write_text("x")
    r = make(clone, f"OUT={tmp_path / 'out'}", "test-template")
    assert r.returncode != 0
    assert "commit all changes" in r.stdout + r.stderr
    assert not (tmp_path / "out").exists()


@needs_copier
def test_make_test_template_passes_on_committed_tree(tmp_path):
    clone = committed_clone(tmp_path)
    out = tmp_path / "out"
    r = make(clone, f"OUT={out}", "test-template")
    assert r.returncode == 0, r.stdout + r.stderr
    assert str(out) in r.stdout
    for c in ("backend", "frontend", "mobile"):
        assert (out / "app" / c / ".git").is_dir()


def test_ci_yaml_shape():
    ci = REPO / ".github/workflows/ci.yml"
    text = ci.read_text()
    job = yaml.safe_load(text)["jobs"]["test-template"]
    assert job["runs-on"] == "ubuntu-latest"
    steps = job["steps"]
    checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["fetch-depth"] == 0
    assert any(s.get("run", "").startswith("make test-template") for s in steps)
    assert "flutter-version-file" in text
    for s in steps:
        if "uses" in s:  # pinned to an exact tag or SHA, never a floating major
            assert re.search(r"@(v\d+\.\d+\.\d+|[0-9a-f]{40})\b", s["uses"]), s["uses"]
    makefile = (REPO / "Makefile").read_text()
    assert "$(CURDIR)" in makefile
    copy_line = next(ln for ln in makefile.splitlines() if "copier copy" in ln)
    assert "--vcs-ref HEAD" in copy_line


def test_readme_has_required_sections():
    text = (REPO / "README.md").read_text()
    headings = re.findall(r"^#+\s+(.*)$", text, re.M)
    for h in ("Generate", "Update", "Develop", "Release"):
        assert any(h in x for x in headings), h
    assert "git tag" in text
    assert "copier update --trust" in text
    assert "committed" in text


def test_min_copier_version_is_tested_floor():
    assert yaml.safe_load((REPO / "copier.yml").read_text())["_min_copier_version"] == "9.19.0"
