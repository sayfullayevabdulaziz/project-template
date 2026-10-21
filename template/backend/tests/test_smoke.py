def test_import():
    import app

    assert app.__name__ == "app"
