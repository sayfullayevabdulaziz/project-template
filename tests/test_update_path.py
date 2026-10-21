import subprocess

import pytest
from conftest import _GIT_ID, generate, make_template, run_copier

COMPONENTS = ["workspace", "backend", "frontend", "mobile"]
PROBE = "CHANGELOG-probe.txt"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


def release_v011(tpl, component):
    """Add a trivial per-component change to the template and tag it v0.1.1."""
    (tpl / "template" / component / PROBE).write_text("probe\n")
    git(tpl, "add", "-A")
    git(tpl, *_GIT_ID, "commit", "-q", "-m", "probe")
    git(tpl, *_GIT_ID, "tag", "v0.1.1")


def update(dest):
    return run_copier(["update", "--trust", "--defaults", "--vcs-ref", "v0.1.1"], cwd=dest)


@pytest.mark.parametrize("component", COMPONENTS)
def test_v010_to_v011_update_applies_cleanly_in_each_component(tmp_path, component):
    tpl = make_template(tmp_path, tag="v0.1.0")
    dest = tmp_path / "out"
    r = generate(tpl, dest, component=component)
    assert r.returncode == 0, r.stderr
    before = git(dest, "rev-list", "--count", "HEAD")
    release_v011(tpl, component)

    r = update(dest)
    assert r.returncode == 0, r.stderr
    assert (dest / PROBE).exists()
    assert not [p for p in dest.rglob("*") if ".git" not in p.parts and p.is_file() and "<<<<<<<" in p.read_text(errors="ignore")]
    assert git(dest, "rev-list", "--count", "HEAD") == before
    # " M .copier-answers.yml" is allowed: update rewrites _commit there.
    untracked = {l[3:] for l in git(dest, "status", "--porcelain").splitlines() if l.startswith("??")}
    assert untracked == {PROBE}


def test_update_never_reprompts(tmp_path):
    tpl = make_template(tmp_path, tag="v0.1.0")
    dest = tmp_path / "out"
    assert generate(tpl, dest).returncode == 0
    release_v011(tpl, "workspace")

    r = subprocess.run(
        ["copier", "update", "--trust", "--defaults", "--vcs-ref", "v0.1.1"],
        cwd=dest, stdin=subprocess.DEVNULL, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr


def test_update_keeps_user_edits_outside_template_changes(tmp_path):
    tpl = make_template(tmp_path, tag="v0.1.0")
    dest = tmp_path / "out"
    assert generate(tpl, dest).returncode == 0
    agents = dest / "AGENTS.md"
    lines = agents.read_text().splitlines()
    lines[0] = lines[0] + " (user edit)"
    agents.write_text("\n".join(lines) + "\n")
    git(dest, "add", "-A")
    git(dest, *_GIT_ID, "commit", "-q", "-m", "user edit")
    release_v011(tpl, "workspace")

    r = update(dest)
    assert r.returncode == 0, r.stderr
    assert agents.read_text().splitlines()[0] == lines[0]
    assert (dest / PROBE).exists()
