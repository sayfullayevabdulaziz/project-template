import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    "dev",
    "test",
    "lint",
    "fmt",
    "check",
    "openapi",
    "up",
    "down",
    "migrate",
    "migration",
    "create-admin",
]
SERVICES = ["db", "redis", "otel-lgtm", "migrate", "api", "worker", "scheduler"]


def _make(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["make", *args],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_required_targets_exist() -> None:
    makefile = (ROOT / "Makefile").read_text()
    for target in TARGETS:
        assert re.search(rf"^{re.escape(target)}:", makefile, re.MULTILINE), target


def test_migration_requires_m() -> None:
    result = _make("-n", "migration")
    assert result.returncode != 0
    assert "m=" in result.stdout + result.stderr


def test_migration_with_m_runs_autogenerate() -> None:
    result = _make("-n", "migration", "m=add widgets")
    assert result.returncode == 0
    assert 'alembic revision --autogenerate -m "add widgets"' in result.stdout


def test_create_admin_uses_compose_run() -> None:
    result = _make("-n", "create-admin", "ARGS=--email a@b.co")
    assert "docker compose run --rm api create-admin --email a@b.co" in result.stdout


def test_compose_has_services() -> None:
    compose = (ROOT / "compose.yaml").read_text()
    for service in SERVICES:
        assert re.search(rf"^  {re.escape(service)}:", compose, re.MULTILINE), service


def test_dockerfile_non_root_and_healthcheck() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "USER app" in dockerfile
    assert "HEALTHCHECK" in dockerfile


def _service_block(name: str) -> str:
    compose = (ROOT / "compose.yaml").read_text()
    match = re.search(rf"^  {re.escape(name)}:\n((?:    .*\n|\n)*)", compose, re.MULTILINE)
    assert match, name
    return match.group(1)


def test_non_http_services_disable_inherited_healthcheck() -> None:
    # Line-based check: PyYAML is not a dependency.
    for service in ("worker", "scheduler", "migrate"):
        block = _service_block(service)
        assert re.search(r"^    healthcheck:\n      disable: true$", block, re.MULTILINE), service


def test_published_ports_bind_loopback() -> None:
    compose = (ROOT / "compose.yaml").read_text()
    ports = [
        item
        for block in re.findall(r"^    ports:\n((?:      - .*\n)+)", compose, re.MULTILINE)
        for item in re.findall(r'- "(.*)"', block)
    ]
    assert len(ports) == 6
    assert all(p.startswith("127.0.0.1:") for p in ports), ports
