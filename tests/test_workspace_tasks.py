import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml

from conftest import COMMON_ANSWERS, REPO, generate, make_template, run_copier

NESTED = ["backend", "frontend", "mobile"]


def git(dest: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(dest), *args], capture_output=True, text=True, check=True).stdout.strip()


def answers(dest: Path) -> dict:
    return yaml.safe_load((dest / ".copier-answers.yml").read_text())


def tree_hashes(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.relative_to(root).parts
    }


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    base = tmp_path_factory.mktemp("wst")
    dest = base / "out"
    r = generate(make_template(base), dest)
    assert r.returncode == 0, r.stderr
    return dest


def test_workspace_generation_yields_four_git_repos(generated):
    for d in [generated, *(generated / c for c in NESTED)]:
        assert (d / ".git").exists(), d
        assert git(d, "rev-list", "--count", "HEAD") == "1", d
        a = answers(d)
        if d != generated:
            assert a["component"] == d.name
        for k, v in COMMON_ANSWERS.items():
            assert a[k] == v
    tracked = git(generated, "ls-files").splitlines()
    assert tracked
    assert not [t for t in tracked if t.split("/")[0] in NESTED]


def test_nested_answers_match_outer_answers_and_no_prompts(tmp_path):
    dest = tmp_path / "out"
    tpl = make_template(tmp_path)
    args = ["copy", "--trust", "--defaults", "--vcs-ref", "HEAD"]
    for k, v in (COMMON_ANSWERS | {"component": "workspace"}).items():
        args += ["-d", f"{k}={v}"]
    r = subprocess.run(
        ["copier", *args, str(tpl), str(dest)], cwd=tmp_path, capture_output=True, text=True, stdin=subprocess.DEVNULL
    )
    assert r.returncode == 0, r.stderr


def test_nested_src_path_is_absolute_and_commit_matches(generated):
    outer = answers(generated)
    assert Path(outer["_src_path"]).is_absolute()
    for c in NESTED:
        a = answers(generated / c)
        assert a["_src_path"] == outer["_src_path"]
        assert a["_commit"] == outer["_commit"]


def test_relative_src_path_fails_fast(tmp_path):
    tpl = make_template(tmp_path)
    args = ["copy", "--trust", "--defaults", "--vcs-ref", "HEAD"]
    for k, v in (COMMON_ANSWERS | {"component": "workspace"}).items():
        args += ["-d", f"{k}={v}"]
    r = run_copier([*args, tpl.name, "dest"], cwd=tpl.parent)
    assert r.returncode != 0
    assert "absolute" in r.stderr


def test_awkward_names_survive(tmp_path):
    dest = tmp_path / "my dir" / "app one"
    dest.parent.mkdir()
    name = "Zoë O'Neil"
    extra = {"project_name": "O'Brien's Shop", "project_slug": "obriens-shop", "author_name": name}
    r = generate(make_template(tmp_path), dest, extra=extra)
    assert r.returncode == 0, r.stderr
    for d in [dest, *(dest / c for c in NESTED)]:
        assert answers(d)["author_name"] == name
        assert answers(d)["project_name"] == "O'Brien's Shop"
    assert git(dest / "backend", "log", "-1", "--format=%an") == name


def test_message_after_update_mentions_relocks():
    msg = yaml.safe_load((REPO / "copier.yml").read_text())["_message_after_update"]
    for cmd in ("uv lock", "pnpm install", "flutter pub get"):
        assert cmd in msg


def test_workspace_update_does_not_touch_nested_repos(tmp_path):
    tpl = make_template(tmp_path, tag="v0.1.0")
    dest = tmp_path / "out"
    r = generate(tpl, dest)
    assert r.returncode == 0, r.stderr
    head = git(dest / "backend", "rev-parse", "HEAD")
    hashes = tree_hashes(dest / "backend")

    (tpl / "template/workspace/NOTES.md").write_text("notes\n")
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "-C", str(tpl), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tpl), *ident, "commit", "-q", "-m", "notes"], check=True)
    subprocess.run(["git", "-C", str(tpl), *ident, "tag", "v0.1.1"], check=True)

    r = run_copier(["update", "--trust", "--defaults"], cwd=dest)
    assert r.returncode == 0, r.stderr
    assert (dest / "NOTES.md").exists()
    assert git(dest / "backend", "rev-parse", "HEAD") == head
    assert tree_hashes(dest / "backend") == hashes
    assert git(dest, "rev-list", "--count", "HEAD") == "1"


def test_custom_package_name_reaches_nested_repos(tmp_path):
    dest = tmp_path / "out"
    r = generate(make_template(tmp_path), dest, extra={"package_name": "custom_pkg"})
    assert r.returncode == 0, r.stderr
    for d in [dest, dest / "mobile", dest / "backend"]:
        assert answers(d)["package_name"] == "custom_pkg"
