def test_package_imports_and_has_version():
    import invisible_playwright_mcp
    assert isinstance(invisible_playwright_mcp.__version__, str)
    assert invisible_playwright_mcp.__version__
