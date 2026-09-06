import pytest
from invisible_playwright_mcp.proxy import proxy_from_url


def test_none_and_empty_return_none():
    assert proxy_from_url(None) is None
    assert proxy_from_url("") is None
    assert proxy_from_url("   ") is None


def test_http_with_credentials():
    d = proxy_from_url("http://user:pass@host.example:8080")
    assert d == {"server": "http://host.example:8080", "username": "user", "password": "pass"}


def test_http_without_credentials_has_no_auth_keys():
    d = proxy_from_url("http://host.example:8080")
    assert d == {"server": "http://host.example:8080"}


def test_socks5_scheme_preserved():
    d = proxy_from_url("socks5://user:pass@host.example:1080")
    assert d["server"] == "socks5://host.example:1080"
    assert d["username"] == "user"
    assert d["password"] == "pass"


def test_missing_port_raises():
    with pytest.raises(ValueError):
        proxy_from_url("http://host.example")
