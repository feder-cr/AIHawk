def test_package_imports_and_has_version():
    import aihawk.mcp
    assert isinstance(aihawk.mcp.__version__, str)
    assert aihawk.mcp.__version__
