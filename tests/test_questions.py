from pathlib import Path

import pytest
import yaml

from conftest import COMMON_ANSWERS, REPO, generate, make_template, run_copier


def answers(dest: Path) -> dict:
    return yaml.safe_load((dest / ".copier-answers.yml").read_text())


def test_workspace_answers_file_records_component_and_shared_answers(tmp_path):
    dest = tmp_path / "out"
    r = generate(make_template(tmp_path), dest)
    assert r.returncode == 0, r.stderr
    a = answers(dest)
    assert a["component"] == "workspace"
    for k, v in COMMON_ANSWERS.items():
        assert a[k] == v
    assert a["package_name"] == "acme_shop"
    assert Path(a["_src_path"]).is_absolute()


@pytest.mark.parametrize("c", ["backend", "frontend", "mobile"])
def test_each_component_answers_file_has_its_component(tmp_path, c):
    dest = tmp_path / "out"
    r = generate(make_template(tmp_path), dest, component=c)
    assert r.returncode == 0, r.stderr
    assert answers(dest)["component"] == c


def test_slug_derived_from_name_when_not_given(tmp_path):
    tpl = make_template(tmp_path)
    dest = tmp_path / "out"
    r = run_copier(
        ["copy", "--trust", "--defaults", "--vcs-ref", "HEAD", "-d", "project_name=Café 2024!", str(tpl), str(dest)],
        cwd=tmp_path,
    )
    assert r.returncode == 0, r.stderr
    a = answers(dest)
    assert a["project_slug"] == "caf-2024"
    assert a["package_name"] == "caf_2024"


def test_invalid_slug_rejected(tmp_path):
    r = generate(make_template(tmp_path), tmp_path / "out", extra={"project_slug": "Bad_Slug"})
    assert r.returncode != 0
    assert "project_slug" in r.stderr


def test_invalid_org_domain_rejected(tmp_path):
    r = generate(make_template(tmp_path), tmp_path / "out", extra={"org_domain": "nodots"})
    assert r.returncode != 0
    assert "org_domain" in r.stderr


EXCLUDED = {
    "backend": [".venv/x", "uv.lock", "dist/a"],
    "frontend": ["node_modules/y", "pnpm-lock.yaml"],
    "mobile": ["pubspec.lock", ".dart_tool/z"],
}


def test_exclude_drops_dev_artifacts(tmp_path):
    overlay = {f"template/{c}/{p}": "x" for c, ps in EXCLUDED.items() for p in ps}
    overlay["template/backend/keep.txt"] = "keep"
    tpl = make_template(tmp_path, overlay)
    for c, ps in EXCLUDED.items():
        dest = tmp_path / f"out-{c}"
        r = generate(tpl, dest, component=c)
        assert r.returncode == 0, r.stderr
        for p in ps:
            assert not (dest / p).exists(), f"{c}/{p}"
    assert (tmp_path / "out-backend" / "keep.txt").exists()


def test_component_question_gating(tmp_path):
    extra_q = '\nbackend_only:\n  type: str\n  default: ""\n  when: "{{ component == \'backend\' }}"\n'
    text = (REPO / "copier.yml").read_text() + extra_q
    tpl = make_template(tmp_path, {"copier.yml": text})
    fe = tmp_path / "fe"
    assert generate(tpl, fe, component="frontend").returncode == 0
    assert "backend_only" not in answers(fe)
    be = tmp_path / "be"
    r = generate(tpl, be, component="backend", extra={"backend_only": "x"})
    assert r.returncode == 0, r.stderr
    assert answers(be)["backend_only"] == "x"


def test_author_identity_defaults_are_non_empty(tmp_path):
    tpl = make_template(tmp_path)
    dest = tmp_path / "out"
    r = run_copier(["copy", "--trust", "--defaults", "--vcs-ref", "HEAD", str(tpl), str(dest)], cwd=tmp_path)
    assert r.returncode == 0, r.stderr
    a = answers(dest)
    assert a["author_name"] == "Your Name"
    assert a["author_email"] == "you@example.com"
