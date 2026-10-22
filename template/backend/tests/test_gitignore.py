from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND.parents[1]


def test_generated_backend_commits_its_lockfile():
    assert "uv.lock" not in (BACKEND / ".gitignore").read_text().splitlines()


def test_template_repo_ignores_its_own_lockfile():
    assert "template/**/uv.lock" in (REPO_ROOT / ".gitignore").read_text().splitlines()
