"""Load / save the single source of truth: xvei-state.json."""
from __future__ import annotations

import json
import os

import util

STATE_VERSION = 3
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
COUNTRY_TEMPLATES = ("russia", "iran", "china")
TEMPLATES = COUNTRY_TEMPLATES + ("popular", "none")


def state_path() -> str:
    return os.environ.get("XVEI_STATE", DEFAULT_STATE_PATH)


def blank_state() -> dict:
    return {
        "version": STATE_VERSION,
        "domain": None,
        "email": "",
        "server_ip": "",
        "cert": {"mode": "none", "fullchain": "", "privkey": ""},
        "routing": {"mode": "direct", "template": "none", "country_exit": None, "tunnel": None},
        "site": {"type": "auth", "proxy_url": ""},
        "outbounds": {"warp": False, "tor": False},
        # [{"tag", "name", "link", "outbound": <xray outbound without tag>}]
        "custom_outbounds": [],
        "inbounds": [],
        "rules": {b: [] for b in RULE_BUCKETS},
        # An Xray setup that existed before xvei: "base" is its config, kept
        # verbatim and merged with what xvei manages (see xrayconf.py).
        "adopted": False,
        "base": None,
        # sha256 of config.json as xvei last wrote it (or as it was adopted)
        "applied_sha256": "",
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

    routing = data.get("routing") or {}
    if "country" in routing and "template" not in routing:
        old_country = routing.pop("country")
        routing["template"] = old_country if old_country in TEMPLATES else "none"
        if routing["template"] in COUNTRY_TEMPLATES:
            # Pre-v3 states sent in-country traffic DIRECT from the server's own
            # IP, which burns/exposes it to that country's network. Fail safe:
            # block it until the admin explicitly picks a tunnel.
            routing["country_exit"] = "block"
            util.warn(
                f"migrated state: the '{old_country}' template used to route "
                "in-country traffic DIRECT from the server (exposes its IP) -- "
                f"now blocked by default. Run 'xvei template {old_country} "
                "--exit warp|tor' to send it through a tunnel instead.")
        data["routing"] = routing

    for key, val in base.items():
        data.setdefault(key, val)
    data["routing"].setdefault("template", "none")
    data["routing"].setdefault("country_exit", None)
    data["routing"].setdefault("tunnel", None)
    data["routing"].setdefault("mode", "direct")
    for b in RULE_BUCKETS:
        data["rules"].setdefault(b, [])
    data["outbounds"].setdefault("warp", False)
    data["outbounds"].setdefault("tor", False)
    data.setdefault("custom_outbounds", [])
    for c in data["custom_outbounds"]:
        data["rules"].setdefault(c["tag"], [])
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


def custom_outbound(data: dict, tag: str) -> dict | None:
    for c in data.get("custom_outbounds", []):
        if c["tag"] == tag:
            return c
    return None


def custom_tags(data: dict) -> list[str]:
    return [c["tag"] for c in data.get("custom_outbounds", [])]


def rule_buckets(data: dict) -> list[str]:
    """Built-in buckets plus one per custom outbound (named by its tag)."""
    return list(RULE_BUCKETS) + custom_tags(data)


def tunnel_names(data: dict) -> list[str]:
    """What may carry the template's tunnel / in-country exit traffic."""
    return ["warp", "tor"] + custom_tags(data)


def base_inbounds(data: dict) -> list[dict]:
    return list((data.get("base") or {}).get("inbounds") or []) if data.get("adopted") else []


def base_outbounds(data: dict) -> list[dict]:
    return list((data.get("base") or {}).get("outbounds") or []) if data.get("adopted") else []


def base_tags(data: dict) -> set[str]:
    """Inbound + outbound tags of the adopted config."""
    return {o.get("tag") for o in base_inbounds(data) + base_outbounds(data) if o.get("tag")}


def base_ports(data: dict) -> set[int]:
    out: set[int] = set()
    for ib in base_inbounds(data):
        p = ib.get("port")
        if isinstance(p, int) or (isinstance(p, str) and p.isdigit()):
            out.add(int(p))
    return out


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
    r = data["routing"]
    if data["outbounds"]["warp"] or r.get("tunnel") == "warp" or r.get("country_exit") == "warp":
        out.append("warp")
    if data["outbounds"]["tor"] or r.get("tunnel") == "tor" or r.get("country_exit") == "tor":
        out.append("tor")
    # dedupe, keep order
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def public_ports(data: dict) -> list[str]:
    """Ports clients (and Let's Encrypt) must reach, as 'PORT/proto'."""
    out: list[str] = []
    if "cert" in needs(data):
        out.append("80/tcp")  # http-01 challenge for issue + renewal
    for ib in data["inbounds"]:
        t, port = ib["type"], ib.get("port", 443)
        if t in ("vless-tls", "vless-xhttp-reality") or (
                t == "vless-xhttp-tls" and ib.get("standalone")):
            out.append(f"{port}/tcp")
        elif t == "shadowsocks":
            out += [f"{port}/tcp", f"{port}/udp"]
        elif t == "hysteria2":
            out.append(f"{port}/udp")
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]
