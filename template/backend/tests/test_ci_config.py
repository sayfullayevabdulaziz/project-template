from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text()


def test_ci_workflow() -> None:
    ci = read(".github/workflows/ci.yml")
    for needle in [
        "ruff check",
        "ruff format --check",
        "ty check",
        "pytest",
        "git diff --exit-code openapi",
        "oasdiff",
        "breaking",
        "public.json",
    ]:
        assert needle in ci, needle
    assert "mypy" not in ci


def test_dependabot() -> None:
    dependabot = read(".github/dependabot.yml")
    for ecosystem in ["uv", "github-actions", "docker"]:
        assert ecosystem in dependabot, ecosystem


def test_pre_commit() -> None:
    pre_commit = read(".pre-commit-config.yaml")
    assert "ruff" in pre_commit
    assert "ty" in pre_commit
