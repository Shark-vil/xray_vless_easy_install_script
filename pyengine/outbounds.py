"""Xray outbound objects."""
from __future__ import annotations

WARP_SOCKS_PORT = 1080
TOR_SOCKS_PORT = 9050

TAG_DIRECT = "direct"
TAG_BLOCK = "block"
TAG_WARP = "warp_proxy"
TAG_TOR = "tor_proxy"


def _socks(tag: str, port: int) -> dict:
    return {
        "protocol": "socks",
        "tag": tag,
        "settings": {"servers": [{"address": "127.0.0.1", "port": port}]},
    }


def build(data: dict) -> list[dict]:
    out = [
        {"protocol": "freedom", "tag": TAG_DIRECT, "settings": {}},
        {"protocol": "blackhole", "tag": TAG_BLOCK, "settings": {}},
    ]
    routing = data["routing"]
    want_warp = (data["outbounds"]["warp"] or routing.get("tunnel") == "warp"
                 or routing.get("country_exit") == "warp")
    want_tor = (data["outbounds"]["tor"] or routing.get("tunnel") == "tor"
                or routing.get("country_exit") == "tor")
    if want_warp:
        out.append(_socks(TAG_WARP, WARP_SOCKS_PORT))
    if want_tor:
        out.append(_socks(TAG_TOR, TOR_SOCKS_PORT))
    return out
