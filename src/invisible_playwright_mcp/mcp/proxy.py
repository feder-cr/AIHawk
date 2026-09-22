"""Parse a proxy URL into the dict invisible_playwright expects.

The wrapper hands the dict to invisible_core.configure_proxy, which keys on
`server` (scheme://host:port) plus optional `username`/`password`.
"""
from __future__ import annotations

from urllib.parse import urlparse, unquote


def proxy_from_url(url: str | None) -> dict[str, str] | None:
    if not url or not url.strip():
        return None
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"proxy URL {url!r} is missing a scheme or host")
    if parsed.port is None:
        raise ValueError(
            f"proxy URL {url!r} has no port; use e.g. http://host:8080"
        )
    out: dict[str, str] = {
        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
    }
    if parsed.username:
        out["username"] = unquote(parsed.username)
    if parsed.password:
        out["password"] = unquote(parsed.password)
    return out
