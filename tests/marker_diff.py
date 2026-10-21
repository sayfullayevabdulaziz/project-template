import re

_BLOCKS = re.compile(
    r"<!-- (?:project-context|claude-tools):start -->.*?<!-- (?:project-context|claude-tools):end -->\n?",
    re.S,
)
# shortcut: Commands section ends at the next level-2 heading; fine for the skeleton shapes.
_COMMANDS = re.compile(r"^## Commands\n.*?(?=^## |\Z)", re.S | re.M)


def strip_managed(text: str) -> str:
    return _COMMANDS.sub("", _BLOCKS.sub("", text))


def same_outside_managed(a: str, b: str) -> bool:
    return strip_managed(a) == strip_managed(b)
