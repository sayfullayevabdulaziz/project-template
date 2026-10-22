import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENTS = (ROOT / "AGENTS.md.jinja").read_text()
CLAUDE = (ROOT / "CLAUDE.md.jinja").read_text()
README = (ROOT / "README.md.jinja").read_text()
MAKEFILE = (ROOT / "Makefile").read_text()
SECTIONS = [
    "Stack",
    "Commands",
    "Architecture",
    "Conventions",
    "Testing",
    "Definition of done",
    "Never",
]


def _markers_ordered(text: str, name: str) -> None:
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    lines = text.splitlines()
    assert lines.count(start) == 1
    assert lines.count(end) == 1
    assert lines.index(start) < lines.index(end)


def test_markers_present_once_and_ordered():
    _markers_ordered(AGENTS, "project-context")
    _markers_ordered(CLAUDE, "claude-tools")
    assert "claude-tools" not in AGENTS
    assert "project-context" not in CLAUDE


def test_agents_line_count_between_100_and_150():
    assert 100 <= len(AGENTS.splitlines()) <= 150


def test_agents_section_order():
    headings = re.findall(r"^## (.+)$", AGENTS, re.M)
    assert headings == SECTIONS
    first_heading = AGENTS.index("\n## ")
    assert AGENTS.index("<!-- project-context:end -->") < first_heading


def test_claude_imports_agents():
    first = next(line for line in CLAUDE.splitlines() if line.strip())
    assert first == "@AGENTS.md"


def test_every_make_target_in_commands_exists():
    declared = set(re.search(r"^\.PHONY: (.+)$", MAKEFILE, re.M).group(1).split())  # ty: ignore[unresolved-attribute]
    used = set(re.findall(r"`make ([a-z-]+)", AGENTS + README))
    assert used, "no make targets documented"
    # sync-api is a workspace-root target documented on purpose; it is not in this Makefile.
    assert used - {"sync-api"} <= declared, used - {"sync-api"} - declared
    assert "workspace root" in AGENTS
    assert declared <= set(re.findall(r"`make ([a-z-]+)", AGENTS)), "AGENTS omits a target"


def test_never_list_has_five_items():
    section = AGENTS.split("## Never", 1)[1]
    assert len(re.findall(r"^- ", section, re.M)) == 5


def test_no_other_jinja_syntax():
    for text in (AGENTS, CLAUDE, README):
        assert "{%" not in text
        assert "{#" not in text
        assert re.findall(r"\{\{.*?\}\}", text) in ([], ["{{ project_name }}"])
    assert AGENTS.splitlines()[0] == "# {{ project_name }}"


def test_settings_allowlist_is_documented_as_not_a_sandbox():
    text = AGENTS + CLAUDE
    assert "NOT a sandbox" in text
    assert "convenience" in text
    for cmd in ("docker compose config", "uv run python", "make"):
        assert cmd in text
    assert "Read tool" in text


def test_context7_pin_audit_recorded():
    assert "@upstash/context7-mcp@4.4.4" in CLAUDE
    assert "2026-10-21" in CLAUDE
    assert "Dependabot" in CLAUDE
    assert ".mcp.json" in CLAUDE


def test_claude_tools_lists_everything():
    block = CLAUDE.split("<!-- claude-tools:start -->")[1].split("<!-- claude-tools:end -->")[0]
    for name in ("new-feature-module", "db-migration", "background-task"):
        assert name in block
    for name in ("backend-reviewer", "context7"):
        assert name in block


def test_readme_covers_env_keys_and_make_targets():
    keys = re.findall(r"^([A-Z_]+)=", (ROOT / ".env.example").read_text(), re.M)
    assert "FORWARDED_ALLOW_IPS" in keys
    for key in keys:
        assert f"`{key}`" in README, key
    for target in re.search(r"^\.PHONY: (.+)$", MAKEFILE, re.M).group(1).split():  # ty: ignore[unresolved-attribute]
        assert f"`make {target}" in README, target


def test_readme_deploy_and_urls():
    for needle in (
        "cp .env.example .env",
        "APP_JWT_SECRET",
        "/api/admin/docs",
        "/api/v1/docs",
        "localhost:3000",
        "SameSite=Strict",
        "APP_COOKIE_SECURE=true",
        "FORWARDED_ALLOW_IPS",
    ):
        assert needle in README, needle


def test_quickstart_create_admin_passes_email():
    quickstart = README.split("## Quickstart")[1].split("## Commands")[0]
    line = next(x for x in quickstart.splitlines() if x.startswith("make create-admin"))
    assert 'ARGS="--email' in line
    assert 'ARGS="--email' in next(x for x in AGENTS.splitlines() if "`make create-admin" in x)


def test_readme_documents_otlp_http_and_no_logs_claim():
    assert "OTLP HTTP endpoint" in README
    assert "OTLP gRPC" not in README
    assert "Grafana (traces, metrics)" in README


def test_readme_deploy_section_requires_prod_env():
    deploy = README.split("## Deploy", 1)[1]
    assert "APP_ENV=prod" in deploy
