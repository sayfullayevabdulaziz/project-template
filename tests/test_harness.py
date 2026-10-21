import subprocess

from conftest import make_template


def test_make_template_is_a_git_repo_with_tag(tmp_path):
    tpl = make_template(tmp_path, overlay={"template/x/f.txt": "hi"}, tag="v0.1.0")
    out = subprocess.run(
        ["git", "-C", str(tpl), "describe", "--tags"], capture_output=True, text=True, check=True
    ).stdout.strip()
    assert out == "v0.1.0"
    assert (tpl / "template/x/f.txt").read_text() == "hi"
