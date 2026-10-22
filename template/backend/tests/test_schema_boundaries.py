import ast
import re
from collections import defaultdict
from pathlib import Path

APP = Path(__file__).parent.parent / "src" / "app"
SURFACE_FILE = re.compile(r"(?:api|schemas)_(\w+)")
SURFACE_SCHEMAS = re.compile(r"app\.\w+\.schemas_(\w+)")
SHARED_SCHEMAS = re.compile(r"app\.\w+\.schemas")


def imports(path: Path) -> list[tuple[str, str]]:
    """(module, name) per `from module import name`; `import module` gives (module, "")."""
    out: list[tuple[str, str]] = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            out += [(node.module, a.name) for a in node.names]
        elif isinstance(node, ast.Import):
            out += [(a.name, "") for a in node.names]
    return out


def surface_of(path: Path) -> str | None:
    m = SURFACE_FILE.fullmatch(path.stem)
    return m[1] if m else None


def test_surface_schemas_imported_only_by_same_surface():
    bad = []
    for path in APP.rglob("*.py"):
        for module, name in imports(path):
            # covers `from app.x.schemas_admin import X` and `from app.x import schemas_admin`
            for target in (module, f"{module}.{name}"):
                m = SURFACE_SCHEMAS.fullmatch(target)
                if m and m[1] != surface_of(path):
                    bad.append(f"{path.relative_to(APP)} imports {target}")
    assert not bad


def test_shared_schema_classes_serve_two_surfaces():
    # A class in <module>/schemas.py that only one surface uses belongs in schemas_<surface>.py.
    users: defaultdict[str, set[str]] = defaultdict(set)
    for path in APP.rglob("*.py"):
        if surface := surface_of(path):
            for module, name in imports(path):
                if SHARED_SCHEMAS.fullmatch(module):
                    users[f"{module}.{name}"].add(surface)
    bad = []
    for path in APP.glob("*/schemas.py"):
        classes = [n.name for n in ast.parse(path.read_text()).body if isinstance(n, ast.ClassDef)]
        for cls in classes:
            qualname = f"app.{path.parent.name}.schemas.{cls}"
            if len(users[qualname]) < 2:
                bad.append(f"{qualname} used by {sorted(users[qualname])}")
    assert not bad
