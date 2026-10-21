import re
from pathlib import Path

import pytest
import yaml

SKILL = Path(__file__).resolve().parent.parent / "template/workspace/.claude/skills/sync-context"
STACKS = ["workspace", "backend", "frontend", "mobile"]
MARKERS = [
    "<!-- project-context:start -->",
    "<!-- project-context:end -->",
    "<!-- claude-tools:start -->",
    "<!-- claude-tools:end -->",
]
SECTIONS = ["Stack", "Commands", "Architecture map", "Conventions", "Testing", "Definition of done", "Never"]
BACKEND = "dev test lint fmt check openapi up down migrate migration create-admin".split()
CLIENT = "dev test lint fmt check gen-api".split()
CONTRACT = set(BACKEND) | set(CLIENT) | {"bootstrap"}


def ref(kind: str, stack: str) -> str:
    return (SKILL / "references" / f"{kind}-skeleton-{stack}.md").read_text()


def test_skill_frontmatter():
    text = (SKILL / "SKILL.md").read_text()
    _, fm, body = text.split("---\n", 2)
    meta = yaml.safe_load(fm)
    assert meta["name"] == "sync-context"
    assert str(meta["description"]).strip()
    assert meta["disable-model-invocation"] is True
    assert "PROJECT.md" in body
    for m in MARKERS:
        assert m in body


@pytest.mark.parametrize("stack", STACKS)
def test_skeletons_have_exact_markers_once(stack):
    a = ref("agents", stack).splitlines()
    assert a.count(MARKERS[0]) == 1 and a.count(MARKERS[1]) == 1
    c = ref("claude", stack).splitlines()
    assert c[0] == "@AGENTS.md"
    assert c.count(MARKERS[2]) == 1 and c.count(MARKERS[3]) == 1


@pytest.mark.parametrize("stack", STACKS)
def test_skeletons_have_no_jinja(stack):
    for kind in ("agents", "claude"):
        t = ref(kind, stack)
        assert "{{" not in t and "{%" not in t


def headings(text: str) -> list[str]:
    return [h for h in re.findall(r"^## (.+)$", text, re.M) if h in SECTIONS]


@pytest.mark.parametrize("stack", ["backend", "frontend", "mobile"])
def test_agents_skeleton_sections_in_order_and_short(stack):
    t = ref("agents", stack)
    assert headings(t) == SECTIONS
    assert len(t.splitlines()) <= 150


def commands(text: str) -> set[str]:
    sec = re.search(r"^## Commands\n(.*?)(?=^## |\Z)", text, re.S | re.M).group(1)
    return set(re.findall(r"^- `make ([\w-]+)`", sec, re.M))


@pytest.mark.parametrize("stack", ["backend", "frontend", "mobile"])
def test_skeleton_commands_match_contract(stack):
    got = commands(ref("agents", stack))
    want = {"backend": BACKEND, "frontend": CLIENT, "mobile": CLIENT + ["bootstrap"]}[stack]
    assert got == set(want)
    assert got <= CONTRACT


def test_skill_commands_rule_limits_to_contract_targets():
    body = (SKILL / "SKILL.md").read_text()
    assert "exactly the targets" not in body
    assert "Never add file targets or helper targets" in body
