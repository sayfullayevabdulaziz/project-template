import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

COMMON_ANSWERS = {
    "project_name": "Acme Shop",
    "project_slug": "acme-shop",
    "project_description": "Demo",
    "org_domain": "com.example",
    "author_name": "Ada Dev",
    "author_email": "ada@example.com",
}

_GIT_ID = ["-c", "user.name=t", "-c", "user.email=t@t"]


def make_template(tmp_path: Path, overlay: dict[str, str] | None = None, tag: str | None = None) -> Path:
    """Copy copier.yml (if present) and template/ to tmp_path/tpl, apply overlay, commit, optionally tag."""
    tpl = tmp_path / "tpl"
    tpl.mkdir(parents=True)
    if (REPO / "copier.yml").exists():
        shutil.copy2(REPO / "copier.yml", tpl / "copier.yml")
    if (REPO / "template").exists():
        shutil.copytree(
            REPO / "template",
            tpl / "template",
            ignore=shutil.ignore_patterns(".venv", "node_modules", "__pycache__"),
        )
    for rel, text in (overlay or {}).items():
        f = tpl / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    git = ["git", "-C", str(tpl)]
    subprocess.run(git + ["init", "-q", "-b", "main"], check=True)
    subprocess.run(git + ["add", "-A"], check=True)
    subprocess.run(git + _GIT_ID + ["commit", "-q", "-m", "tpl"], check=True)
    if tag:
        subprocess.run(git + _GIT_ID + ["tag", tag], check=True)
    return tpl


def run_copier(
    args: list[str],
    cwd: Path,
    path_prepend: list[Path] | None = None,
    no_git_identity: bool = True,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if no_git_identity:
        env.update(HOME=str(cwd), GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    if path_prepend:
        env["PATH"] = os.pathsep.join([*map(str, path_prepend), env["PATH"]])
    return subprocess.run(["copier", *args], cwd=cwd, env=env, capture_output=True, text=True)


def generate(
    tpl: Path,
    dest: Path,
    component: str = "workspace",
    extra: dict[str, str] | None = None,
    **kw,
) -> subprocess.CompletedProcess:
    answers = COMMON_ANSWERS | {"component": component} | (extra or {})
    args = ["copy", "--trust", "--defaults", "--vcs-ref", "HEAD"]
    for k, v in answers.items():
        args += ["-d", f"{k}={v}"]
    return run_copier([*args, str(tpl), str(dest)], cwd=dest.parent, **kw)


@pytest.fixture(scope="session")
def ws(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("ws")
    tpl = make_template(base)
    dest = base / "out"
    r = generate(tpl, dest)
    assert r.returncode == 0, r.stderr
    return dest
