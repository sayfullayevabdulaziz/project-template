import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

SURFACES = [("frontend", "admin.json"), ("mobile", "public.json")]


@pytest.fixture(params=["tree", "a b"])
def tree(ws, tmp_path, request) -> Path:
    """Fresh copy of the generated workspace, also under a dir with a space."""
    dest = tmp_path / request.param / "ws"
    shutil.copytree(ws, dest)
    for repo in ("backend", "frontend", "mobile"):  # empty nested components: start from none
        shutil.rmtree(dest / repo)
    return dest


def make(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["make", *args], cwd=cwd, capture_output=True, text=True)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@pytest.mark.parametrize("target", ["up", "down", "sync-api", "check", "check-specs"])
def test_make_dry_run_targets_exist(tree, target):
    r = make(tree, "-n", target)
    assert r.returncode == 0, r.stderr


def test_check_specs_passes_when_equal_or_absent(tree):
    assert make(tree, "check-specs").returncode == 0
    write(tree / "backend/openapi/admin.json", "{}")
    write(tree / "frontend/openapi.json", "{}")
    assert make(tree, "check-specs").returncode == 0


@pytest.mark.parametrize("client,spec", SURFACES)
def test_check_specs_fails_when_client_spec_stale(tree, client, spec):
    write(tree / "backend/openapi" / spec, '{"a": 1}')
    write(tree / client / "openapi.json", '{"a": 2}')
    r = make(tree, "check-specs")
    assert r.returncode != 0  # recipe exits 1; make reports 2
    out = r.stdout + r.stderr
    assert "stale client" in out and client in out


def test_check_runs_repo_checks_and_skips_missing(tree):
    write(tree / "backend/Makefile", "check:\n\t@echo BACKEND_CHECK\n")
    r = make(tree, "check")
    assert r.returncode == 0, r.stderr
    assert "BACKEND_CHECK" in r.stdout


def test_check_fails_when_repo_check_fails(tree):
    write(tree / "backend/Makefile", "check:\n\t@exit 1\n")
    assert make(tree, "check").returncode != 0


def test_sync_api_copies_and_calls_gen_api(tree):
    write(
        tree / "backend/Makefile",
        "openapi:\n\t@mkdir -p openapi\n"
        "\t@echo '{\"s\": \"admin\"}' > openapi/admin.json\n"
        "\t@echo '{\"s\": \"public\"}' > openapi/public.json\n",
    )
    write(tree / "frontend/Makefile", "gen-api:\n\t@echo GEN_FRONTEND\n")
    write(tree / "mobile/Makefile", "gen-api:\n\t@echo GEN_MOBILE\n")
    r = make(tree, "sync-api")
    assert r.returncode == 0, r.stderr
    assert "GEN_FRONTEND" in r.stdout and "GEN_MOBILE" in r.stdout
    for client, spec in SURFACES:
        assert (tree / client / "openapi.json").read_text() == (tree / "backend/openapi" / spec).read_text()


def test_sync_api_skips_absent_client(tree):
    write(tree / "backend/Makefile", "openapi:\n\t@echo '{}' > /dev/null\n")
    write(tree / "backend/openapi/admin.json", "{}")
    write(tree / "backend/openapi/public.json", "{}")
    r = make(tree, "sync-api")
    assert r.returncode == 0, r.stderr
    assert "skip" in (r.stdout + r.stderr).lower()


def load_compose(ws: Path) -> dict:
    return yaml.safe_load((ws / "compose.yaml").read_text())


def test_compose_shape(ws):
    c = load_compose(ws)
    assert "backend/compose.yaml" in str(c["include"])
    admin = c["services"]["admin"]
    assert admin["image"] == "node:24"
    assert admin["working_dir"] == "/app"
    assert "5173:5173" in admin["ports"]
    assert "./frontend:/app" in admin["volumes"]
    assert "/app/node_modules" in admin["volumes"]
    assert "pnpm dev --host" in str(admin["command"])
    assert "API_PROXY_TARGET" in admin["environment"]
    assert "api" in admin["depends_on"]


def test_compose_config_validates_when_docker_and_backend_compose_present(ws, tmp_path):
    if not shutil.which("docker"):
        pytest.skip("docker not installed")
    if not (ws / "backend/compose.yaml").exists():
        pytest.skip("backend/compose.yaml not generated yet (plan 02)")
    r = subprocess.run(["docker", "compose", "config", "-q"], cwd=ws, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("args", [["-n", "check"], ["check"], ["sync-api"]])
def test_targets_skip_repos_without_makefile(ws, tmp_path, args):
    # Unchanged generated tree: repo dirs exist but hold only .git (no Makefile).
    dest = tmp_path / "ws"
    shutil.copytree(ws, dest)
    assert (dest / "backend").is_dir() and not (dest / "backend/Makefile").exists()
    r = make(dest, *args)
    assert r.returncode == 0, r.stderr
    assert r.stdout.lower().count("skip") >= 2
