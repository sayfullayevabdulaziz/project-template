import re
import subprocess
from pathlib import Path

from conftest import generate, make_template, run_copier

START, END = "<!-- project-context:start -->", "<!-- project-context:end -->"
TOOLS_START, TOOLS_END = "<!-- claude-tools:start -->", "<!-- claude-tools:end -->"
SECTIONS = [
    "Purpose",
    "Users and roles",
    "Clients and the surface each uses",
    "Glossary",
    "Core entities and rules",
    "Integrations",
    "Environments",
    "Cross-repo conventions",
]
NESTED = {"backend", "frontend", "mobile", ".git"}
JINJA_ALLOWLIST: set[str] = set()


def lines(ws: Path, name: str) -> list[str]:
    return (ws / name).read_text().splitlines()


def test_agents_has_exact_context_markers_once(ws):
    ls = lines(ws, "AGENTS.md")
    assert ls.count(START) == 1 and ls.count(END) == 1
    assert ls.index(START) < ls.index(END)


def test_claude_md_imports_agents_and_has_tool_markers(ws):
    ls = lines(ws, "CLAUDE.md")
    assert next(l for l in ls if l.strip()) == "@AGENTS.md"
    assert ls.count(TOOLS_START) == 1 and ls.count(TOOLS_END) == 1
    assert ls.index(TOOLS_START) < ls.index(TOOLS_END)


def test_agents_mentions_project_name_and_rules(ws):
    text = (ws / "AGENTS.md").read_text()
    for needle in ("Acme Shop", "make sync-api", "/api/admin", "/api/v1", "openapi/"):
        assert needle in text


def test_agents_length_within_target(ws):
    assert len(lines(ws, "AGENTS.md")) <= 60


def test_project_md_sections_in_order(ws):
    text = (ws / "PROJECT.md").read_text()
    headings = [l[3:].strip() for l in text.splitlines() if l.startswith("## ")]
    assert headings == SECTIONS
    for body in re.split(r"^## .*\n", text, flags=re.M)[1:]:
        assert body.lstrip().startswith("<!--")
    for needle in ("UTC", "integer minor units", "UUIDv7"):
        assert needle in text


def test_no_unrendered_jinja_in_workspace(ws):
    for p in ws.rglob("*"):
        rel = p.relative_to(ws)
        if not p.is_file() or rel.parts[0] in NESTED or str(rel) in JINJA_ALLOWLIST:
            continue
        try:
            text = p.read_text()
        except UnicodeDecodeError:
            continue
        assert "{{" not in text and "{%" not in text, rel


def test_update_preserves_filled_project_context_block(tmp_path):
    tpl = make_template(tmp_path, tag="v0.1.0")
    dest = tmp_path / "out"
    r = generate(tpl, dest)
    assert r.returncode == 0, r.stderr
    ident = ["-c", "user.name=t", "-c", "user.email=t@t"]

    agents = dest / "AGENTS.md"
    filled = "Acme Shop sells widgets to retail customers."
    text = agents.read_text()
    assert "_Not generated yet." in text
    agents.write_text(re.sub(r"_Not generated yet\.[^\n]*", filled, text))
    subprocess.run(["git", "-C", str(dest), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(dest), *ident, "commit", "-q", "-m", "fill context"], check=True)

    src = tpl / "template/workspace/AGENTS.md.jinja"
    new_rule = "Session rule UPDATED-IN-V0.1.1."
    s = src.read_text()
    assert "Session rule" in s
    src.write_text(re.sub(r"^.*Session rule.*$", new_rule, s, count=1, flags=re.M))
    subprocess.run(["git", "-C", str(tpl), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(tpl), *ident, "commit", "-q", "-m", "rule"], check=True)
    subprocess.run(["git", "-C", str(tpl), *ident, "tag", "v0.1.1"], check=True)

    r = run_copier(["update", "--trust", "--defaults"], cwd=dest)
    assert r.returncode == 0, r.stderr
    out = agents.read_text()
    assert filled in out
    assert new_rule in out
    assert "<<<<<<<" not in out
