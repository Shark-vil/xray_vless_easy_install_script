"""xvei-state.json: what xvei knows that config.json cannot hold.

config.json is the source of truth for everything Xray runs (see
xrayconf.py). This file only keeps the domain, e-mail, server IP and
certificate, the camouflage site, which inbounds and services xvei created
itself (so it never tears down someone else's nginx, WARP or Hysteria2), and
the parameters of Hysteria2 and Turnable, which run from their own configs.
"""
from __future__ import annotations

import json
import os

import util
import xrayconf as xc

STATE_VERSION = 4
DEFAULT_STATE_PATH = "/usr/local/etc/xray/xvei-state.json"

INBOUND_TYPES = (
    "vless-tls",
    "vless-ws",
    "vless-xhttp-reality",
    "vless-xhttp-tls",
    "trojan-tcp",
    "trojan-ws",
    "vmess-ws",
    "shadowsocks",
    "hysteria2",
    "turnable",
)

# inbounds that live behind the :443 TLS inbound's fallbacks (no port of their own)
FALLBACK_TYPES = ("vless-ws", "trojan-tcp", "trojan-ws", "vmess-ws")
# inbounds that need the domain's TLS certificate
TLS_TYPES = ("vless-tls", "vless-xhttp-tls") + FALLBACK_TYPES

COUNTRY_TEMPLATES = ("russia", "iran", "china")
TEMPLATES = COUNTRY_TEMPLATES + ("popular", "none")

WARP_TAG = "warp_proxy"
TOR_TAG = "tor_proxy"


def state_path() -> str:
    return os.environ.get("XVEI_STATE", DEFAULT_STATE_PATH)


def blank_state() -> dict:
    return {
        "version": STATE_VERSION,
        "domain": None,
        "email": "",
        "server_ip": "",
        "cert": {"mode": "none", "fullchain": "", "privkey": ""},
        "site": {"type": "auth", "proxy_url": ""},
        # xvei did not install Xray (it was there already): `remove --all`
        # keeps it, and the first write saves the original config
        "adopted": False,
        # what xvei created: {inbound tag: type}, and whether it runs WARP / TOR
        "owned": {"inbounds": {}, "warp": False, "tor": False},
        # {"tag", "port", "socks_port", "password", "up_mbps", "down_mbps"}
        "hysteria2": None,
        # {"tag", "port", "call_id", "local_port", "turnable_uuid", "peers",
        #  "priv_key", "pub_key"}
        "turnable": None,
        # display names from the share links outbounds were added from
        "outbound_names": {},
        # how many backups of config.json + state to keep (0: automatic off)
        "backups_keep": 20,
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


def _from_v3(old: dict) -> dict:
    """Up to v3 the state described the whole Xray config and config.json was
    generated from it. That config is already on disk; keep what it cannot
    hold."""
    new = blank_state()
    for key in ("domain", "email", "server_ip", "cert", "site", "adopted"):
        if key in old:
            new[key] = old[key]
    ibs = [ib for ib in old.get("inbounds") or [] if ib.get("tag") and ib.get("type")]
    new["owned"]["inbounds"] = {ib["tag"]: ib["type"] for ib in ibs}
    r, outs = old.get("routing") or {}, old.get("outbounds") or {}
    for name in ("warp", "tor"):
        new["owned"][name] = bool(outs.get(name) or name in (r.get("tunnel"),
                                                              r.get("country_exit")))
    for ib in ibs:
        if ib["type"] == "hysteria2":
            new["hysteria2"] = {k: ib.get(k) for k in (
                "tag", "port", "socks_port", "password", "up_mbps", "down_mbps")}
        elif ib["type"] == "turnable":
            new["turnable"] = {k: ib.get(k) for k in (
                "tag", "port", "call_id", "local_port", "turnable_uuid", "peers",
                "priv_key", "pub_key")}
    new["outbound_names"] = {c["tag"]: c["name"] for c in old.get("custom_outbounds") or []
                             if c.get("tag") and c.get("name")}
    return new


def _migrate(data: dict) -> dict:
    if data.get("version", 0) < 4:
        data = _from_v3(data)
    base = blank_state()
    for key, val in base.items():
        data.setdefault(key, val)
    for key, val in base["owned"].items():
        data["owned"].setdefault(key, val)
    data["site"].setdefault("type", "auth")
    data["site"].setdefault("proxy_url", "")
    return data


# ---- what xvei owns ---------------------------------------------------------

def owned_type(data: dict, tag: str) -> str | None:
    return data["owned"]["inbounds"].get(tag)


def owned_present(data: dict, cfg: dict) -> dict[str, str]:
    """xvei's inbounds that are still in config.json: {tag: type}."""
    return {t: ty for t, ty in data["owned"]["inbounds"].items() if xc.find_inbound(cfg, t)}


def service(data: dict, cfg: dict, name: str) -> dict | None:
    """The Hysteria2 / Turnable record, if its Xray inbound is still there."""
    rec = data.get(name)
    return rec if rec and xc.find_inbound(cfg, rec.get("tag", "")) else None


def builtin_tag(name: str) -> str:
    return WARP_TAG if name == "warp" else TOR_TAG


def builtin_on(data: dict, cfg: dict, name: str) -> bool:
    """xvei's own WARP / TOR: on while its outbound is in config.json."""
    return bool(data["owned"].get(name)) and xc.find_outbound(cfg, builtin_tag(name)) is not None


def builtin_free(data: dict, cfg: dict, name: str) -> bool:
    """May xvei offer its own WARP / TOR? Not when the config already has an
    outbound with that tag that xvei did not add (its own WARP / TOR)."""
    return bool(data["owned"].get(name)) or xc.find_outbound(cfg, builtin_tag(name)) is None


# ---- what has to run --------------------------------------------------------

def needs(data: dict, cfg: dict) -> list[str]:
    """External resources lib/apply.sh has to provision for this config."""
    out: list[str] = []
    # an xvei inbound that terminates TLS itself; one that only rides the
    # fallbacks of someone else's TLS inbound uses that one's cert and site
    if any(((xc.find_inbound(cfg, t).get("streamSettings") or {}).get("security") == "tls")
           for t in owned_present(data, cfg)):
        out.append("cert")
    if service(data, cfg, "turnable"):
        out.append("turnable")
    if service(data, cfg, "hysteria2"):
        out.append("hysteria2")
        if data["domain"]:
            out.append("cert")
    for name in ("warp", "tor"):
        if builtin_on(data, cfg, name):
            out.append(name)
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def public_ports(data: dict, cfg: dict) -> list[str]:
    """Ports clients (and Let's Encrypt) must reach, as 'PORT/proto'."""
    out: list[str] = []
    if "cert" in needs(data, cfg):
        out.append("80/tcp")  # http-01 challenge for issue + renewal
    for ib in xc.inbounds(cfg):
        if not xc.is_public(ib):
            continue
        port = xc.port_of(ib)
        out.append(f"{port}/tcp")
        settings = ib.get("settings") or {}
        if ib.get("protocol") == "shadowsocks" or (
                ib.get("protocol") == "socks" and settings.get("udp")):
            out.append(f"{port}/udp")
    for name in ("hysteria2", "turnable"):
        rec = service(data, cfg, name)
        if rec and rec.get("port"):
            out.append(f"{rec['port']}/udp")
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]
