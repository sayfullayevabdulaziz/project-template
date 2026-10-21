from marker_diff import same_outside_managed, strip_managed

DOC = """# T

<!-- project-context:start -->
ctx
<!-- project-context:end -->

## Commands

- `make dev`

## Stack

x
<!-- claude-tools:start -->
tools
<!-- claude-tools:end -->
tail
"""


def test_strip_managed_removes_blocks_and_commands():
    out = strip_managed(DOC)
    for gone in ("ctx", "tools", "make dev", "## Commands", "project-context", "claude-tools"):
        assert gone not in out
    for kept in ("# T", "## Stack", "tail"):
        assert kept in out


def test_same_outside_managed_detects_outside_edit():
    assert not same_outside_managed(DOC, DOC.replace("tail", "changed"))
    assert not same_outside_managed(DOC, DOC.replace("## Stack", "## Stacks"))


def test_marker_edit_inside_is_ignored():
    edited = DOC.replace("\nctx\n", "\nnew ctx\n").replace("\ntools\n", "\nnew tools\n").replace("make dev", "make run")
    assert same_outside_managed(DOC, edited)
