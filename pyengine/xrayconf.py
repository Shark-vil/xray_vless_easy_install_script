"""config.json: the source of truth for inbounds, outbounds and routing.

It is read fresh on every call, so whatever was edited by hand shows up at
once. Changes made through xvei are written to a staging file next to it;
lib/apply.sh validates that with `xray -test` and only then swaps it in.
"""
from __future__ import annotations

import os

import json5lite
import util

XRAY_CONFIG_DEFAULT = "/usr/local/etc/xray/config.json"

# addresses that are not reachable from outside
LOCAL_LISTENS = ("127.0.0.1", "::1", "localhost")
# outbound protocols that are not a tunnel to somewhere else
NOT_PROXIES = ("freedom", "blackhole", "dns", "loopback")


def config_path() -> str:
    return os.environ.get("XVEI_XRAY_CONFIG", XRAY_CONFIG_DEFAULT)


def pending_path() -> str:
    """Staging file for a changed config (must end in .json for `xray -test`)."""
    return os.path.join(os.path.dirname(config_path()), ".xvei-config.new.json")


def load(*, pending: bool = False) -> dict:
    """The live config.json, or with pending=True the staged change if there
    is one. A missing or empty file is an empty config."""
    paths = [pending_path(), config_path()] if pending else [config_path()]
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if not text.strip():
            return {}
        try:
            cfg = json5lite.loads(text)
        except json5lite.Json5Error as e:
            util.die(f"{path}: {e}")
        if not isinstance(cfg, dict):
            util.die(f"{path}: top level is not an object")
        return cfg
    return {}


def save_pending(cfg: dict) -> None:
    """Stage a changed config; nothing is staged when it equals the live one."""
    if cfg == load():
        if os.path.exists(pending_path()):
            os.remove(pending_path())
        return
    util.write_json(pending_path(), cfg, mode=0o600)


def skeleton() -> dict:
    """A fresh config: direct first (the default route), then block."""
    import routing

    return {
        "log": {"loglevel": "warning", "dnsLog": False},
        "dns": {"servers": ["1.1.1.1", "8.8.8.8", "localhost"]},
        "inbounds": [],
        "outbounds": [
            {"protocol": "freedom", "tag": "direct", "settings": {}},
            {"protocol": "blackhole", "tag": "block", "settings": {}},
        ],
        "routing": {"domainStrategy": "IPIfNonMatch",
                    "rules": [dict(r) for r in routing.GUARD_RULES]
                    + [routing.exit_rule("direct")]},
    }


# ---- queries --------------------------------------------------------------

def inbounds(cfg: dict) -> list[dict]:
    return [x for x in cfg.get("inbounds") or [] if isinstance(x, dict)]


def outbounds(cfg: dict) -> list[dict]:
    return [x for x in cfg.get("outbounds") or [] if isinstance(x, dict)]


def rules(cfg: dict) -> list[dict]:
    """The routing rules list itself (created when missing), for changing it."""
    routing = cfg.setdefault("routing", {})
    if not isinstance(routing.get("rules"), list):
        routing["rules"] = []
    return routing["rules"]


def rules_view(cfg: dict) -> list[dict]:
    return [r for r in (cfg.get("routing") or {}).get("rules") or [] if isinstance(r, dict)]


def find_inbound(cfg: dict, tag: str) -> dict | None:
    return next((x for x in inbounds(cfg) if x.get("tag") == tag), None)


def find_outbound(cfg: dict, tag: str) -> dict | None:
    return next((x for x in outbounds(cfg) if x.get("tag") == tag), None)


def tags(cfg: dict) -> set[str]:
    return {x["tag"] for x in inbounds(cfg) + outbounds(cfg) if x.get("tag")}


def port_of(ib: dict) -> int | None:
    p = ib.get("port")
    if isinstance(p, int):
        return p
    if isinstance(p, str) and p.isdigit():
        return int(p)
    return None


def used_ports(cfg: dict) -> set[int]:
    return {p for p in (port_of(x) for x in inbounds(cfg)) if p is not None}


def is_public(ib: dict) -> bool:
    listen = str(ib.get("listen") or "0.0.0.0")
    return port_of(ib) is not None and listen not in LOCAL_LISTENS \
        and not listen.startswith(("@", "/"))


def terminator(cfg: dict) -> dict | None:
    """The TLS inbound on :443 whose fallbacks carry the WS / XHTTP / Trojan
    inbounds that have no port of their own."""
    for ib in inbounds(cfg):
        ss = ib.get("streamSettings") or {}
        if port_of(ib) == 443 and ss.get("security") == "tls" \
                and isinstance((ib.get("settings") or {}).get("fallbacks"), list):
            return ib
    return None


def rule_users(cfg: dict, *, outbound: str | None = None,
               inbound: str | None = None) -> list[int]:
    """Numbers (1-based) of the rules that send traffic to / take it from a tag."""
    out = []
    for i, r in enumerate(rules_view(cfg), 1):
        if outbound and r.get("outboundTag") == outbound:
            out.append(i)
        ib = r.get("inboundTag")
        if inbound and inbound in ([ib] if isinstance(ib, str) else ib or []):
            out.append(i)
    return out


def ensure_outbound(cfg: dict, tag: str) -> None:
    """Rules may only point at outbounds that exist; add "direct" / "block"
    when a config has none (after the others: the first one is the default)."""
    if find_outbound(cfg, tag):
        return
    proto = {"direct": "freedom", "block": "blackhole"}.get(tag)
    if not proto:
        util.die(f"no outbound tagged {tag!r}")
    cfg.setdefault("outbounds", []).append({"protocol": proto, "tag": tag, "settings": {}})


# ---- descriptions ---------------------------------------------------------

def inbound_detail(ib: dict) -> str:
    """What an inbound is, e.g. 'vless :443 tcp/tls'."""
    ss = ib.get("streamSettings") or {}
    net = f" {ss.get('network', 'tcp')}/{ss.get('security', 'none')}" if ss else ""
    where = ib.get("port") or ib.get("listen") or "?"
    return f"{ib.get('protocol', '?')} :{where}{net}"


def outbound_detail(ob: dict) -> str:
    """What an outbound is, e.g. 'socks 127.0.0.1:1080'."""
    out = ob.get("protocol", "?")
    settings = ob.get("settings") or {}
    srv = (settings.get("vnext") or settings.get("servers") or [None])[0]
    if isinstance(srv, dict):
        out += f" {srv.get('address', '?')}:{srv.get('port', '?')}"
    elif settings.get("address"):
        out += f" {settings['address']}:{settings.get('port', '?')}"
    ss = ob.get("streamSettings") or {}
    if ss:
        out += f" {ss.get('network', 'tcp')}/{ss.get('security', 'none')}"
    return out


def rule_parts(rule: dict) -> tuple[str, str]:
    """(matchers, target) of a routing rule, for display."""
    parts = []
    for key in ("inboundTag", "domain", "ip", "port", "sourcePort", "source",
                "network", "protocol", "user", "attrs"):
        val = rule.get(key)
        if val in (None, "", []):
            continue
        if isinstance(val, list):
            shown = ", ".join(map(str, val[:4])) + (f" (+{len(val) - 4})" if len(val) > 4 else "")
        else:
            shown = str(val)
        parts.append(f"{key} {shown}")
    target = rule.get("outboundTag") or (f"balancer {rule['balancerTag']}"
                                         if rule.get("balancerTag") else "?")
    return "; ".join(parts) or "everything", target


def describe_rule(rule: dict) -> str:
    what, target = rule_parts(rule)
    return f"{what} -> {target}"
