"""The Xray outbounds xvei adds itself: its WARP and TOR SOCKS5 endpoints."""
from __future__ import annotations

WARP_SOCKS_PORT = 1080
TOR_SOCKS_PORT = 9050

TAG_DIRECT = "direct"
TAG_BLOCK = "block"
TAG_WARP = "warp_proxy"
TAG_TOR = "tor_proxy"


def builtin(name: str) -> dict:
    """The outbound for xvei's WARP container / tor service."""
    tag, port = (TAG_WARP, WARP_SOCKS_PORT) if name == "warp" else (TAG_TOR, TOR_SOCKS_PORT)
    return {"protocol": "socks", "tag": tag,
            "settings": {"servers": [{"address": "127.0.0.1", "port": port}]}}
