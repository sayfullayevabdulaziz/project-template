from importlib.metadata import entry_points


def test_create_admin_console_script_is_installed() -> None:
    scripts = {ep.name: ep.value for ep in entry_points(group="console_scripts")}
    assert scripts.get("create-admin") == "app.cli:main"
