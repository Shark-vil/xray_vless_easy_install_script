"""Load / save the single source of truth: xvei-state.json."""
from __future__ import annotations

import json
import os

import util

STATE_VERSION = 2
DEFAULT_STATE_PATH = "/usr/local/etc/xray/xvei-state.json"

INBOUND_TYPES = (
    "vless-tls",
    "vless-ws",
    "vless-xhttp-reality",
    "vless-xhttp-tls",
    "shadowsocks",
    "hysteria2",
)

RULE_BUCKETS = ("block", "warp", "tor", "direct")
COUNTRIES = ("russia", "iran", "china", "none")


def state_path() -> str:
    return os.environ.get("XVEI_STATE", DEFAULT_STATE_PATH)


def blank_state() -> dict:
    return {
        "version": STATE_VERSION,
        "domain": None,
        "email": "",
        "server_ip": "",
        "cert": {"mode": "none", "fullchain": "", "privkey": ""},
        "routing": {"mode": "direct", "country": "none", "tunnel": None},
        "site": {"type": "auth", "proxy_url": ""},
        "outbounds": {"warp": False, "tor": False},
        "inbounds": [],
        "rules": {b: [] for b in RULE_BUCKETS},
    }


def load(path: str | None = None) -> dict:
    path = path or state_path()
    if not os.path.exists(path):
        return blank_state()
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return _migrate(data)


def save(data: dict, path: str | None = None) -> None:
    path = path or state_path()
    data["version"] = STATE_VERSION
    util.write_json(path, data, mode=0o600)


def _migrate(data: dict) -> dict:
    base = blank_state()
    for key, val in base.items():
        data.setdefault(key, val)
    for b in RULE_BUCKETS:
        data["rules"].setdefault(b, [])
    data["outbounds"].setdefault("warp", False)
    data["outbounds"].setdefault("tor", False)
    data.setdefault("site", {"type": "auth", "proxy_url": ""})
    data["site"].setdefault("type", "auth")
    data["site"].setdefault("proxy_url", "")
    return data


# ---- queries -------------------------------------------------------------

def inbound_by_tag(data: dict, tag: str) -> dict | None:
    for ib in data["inbounds"]:
        if ib.get("tag") == tag:
            return ib
    return None


def has_type(data: dict, itype: str) -> bool:
    return any(ib.get("type") == itype for ib in data["inbounds"])


def get_type(data: dict, itype: str) -> dict | None:
    for ib in data["inbounds"]:
        if ib.get("type") == itype:
            return ib
    return None


def proxied_inbound_tags(data: dict) -> list[str]:
    return [ib["tag"] for ib in data["inbounds"]]


def needs(data: dict) -> list[str]:
    """External resources the current state requires bash to provision."""
    out: list[str] = []
    tls_users = {"vless-tls", "vless-ws", "vless-xhttp-tls"}
    if any(ib["type"] in tls_users for ib in data["inbounds"]):
        out.append("cert")
    if has_type(data, "hysteria2"):
        out.append("hysteria2")
        if data["domain"]:
            out.append("cert")
    if data["outbounds"]["warp"] or data["routing"].get("tunnel") == "warp":
        out.append("warp")
    if data["outbounds"]["tor"] or data["routing"].get("tunnel") == "tor":
        out.append("tor")
    # dedupe, keep order
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]
