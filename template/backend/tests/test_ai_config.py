import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / ".claude"
SKILLS = ["new-feature-module", "db-migration", "background-task"]


def frontmatter(path: Path) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", path.read_text(), re.DOTALL)
    assert match, f"{path} has no frontmatter"
    return dict(line.split(": ", 1) for line in match.group(1).splitlines())


@pytest.fixture(scope="module")
def settings() -> dict:
    return json.loads((CLAUDE / "settings.json").read_text())


def test_settings_permissions(settings: dict) -> None:
    deny = settings["permissions"]["deny"]
    assert "Read(./.env)" in deny
    assert "Read(./.env.*.local)" in deny
    assert not any(".env.example" in rule for rule in deny)
    for rule in ["Bash(uv run *)", "Bash(make *)", "Bash(docker compose *)"]:
        assert rule in settings["permissions"]["allow"]


def test_settings_format_hook(settings: dict) -> None:
    (group,) = settings["hooks"]["PostToolUse"]
    assert group["matcher"] == "Edit|Write"
    (hook,) = group["hooks"]
    assert hook["type"] == "command"
    assert hook["command"] == '"$CLAUDE_PROJECT_DIR"/.claude/hooks/format.sh'


def test_format_hook_is_executable() -> None:
    assert os.access(CLAUDE / "hooks" / "format.sh", os.X_OK)


@pytest.mark.parametrize("name", SKILLS)
def test_skill_frontmatter(name: str) -> None:
    fm = frontmatter(CLAUDE / "skills" / name / "SKILL.md")
    assert fm["name"] == name
    assert fm["description"]


def test_agent_frontmatter() -> None:
    fm = frontmatter(CLAUDE / "agents" / "backend-reviewer.md")
    assert fm["name"] == "backend-reviewer"
    assert fm["description"]
    assert fm["tools"] == "Read, Grep, Glob, Bash"


def test_mcp_context7() -> None:
    server = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["context7"]
    assert server["command"] == "npx"
    assert re.fullmatch(r"@upstash/context7-mcp@\d+\.\d+\.\d+", server["args"][-1])
