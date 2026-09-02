"""Routing rules: base guardrails + country template + exit mode + user edits."""
from __future__ import annotations

import outbounds as ob

# Country -> (domain matchers, ip matchers) kept DIRECT (never tunneled/proxied).
COUNTRY_DIRECT = {
    "russia": (["geosite:category-ru", "geosite:category-gov-ru"], ["geoip:ru"]),
    "iran": (["geosite:category-ir"], ["geoip:ir"]),
    "china": (["geosite:cn"], ["geoip:cn"]),
    "none": ([], []),
}

_DOMAIN_PREFIXES = ("geosite:", "domain:", "full:", "regexp:", "keyword:")


def _split_matchers(items: list[str]) -> tuple[list[str], list[str]]:
    domains, ips = [], []
    for it in items:
        it = it.strip()
        if not it:
            continue
        if it.startswith(_DOMAIN_PREFIXES):
            domains.append(it)
        elif it.startswith("geoip:") or "/" in it or _looks_ip(it):
            ips.append(it)
        else:
            domains.append("domain:" + it)
    return domains, ips


def _looks_ip(s: str) -> bool:
    import ipaddress

    try:
        ipaddress.ip_address(s.split("/")[0])
        return True
    except ValueError:
        return False


def _rule(tag: str, items: list[str], *, extra: dict | None = None) -> list[dict]:
    domains, ips = _split_matchers(items)
    rules: list[dict] = []
    if domains:
        r = {"type": "field", "outboundTag": tag, "domain": domains}
        if extra:
            r.update(extra)
        rules.append(r)
    if ips:
        r = {"type": "field", "outboundTag": tag, "ip": ips}
        if extra:
            r.update(extra)
        rules.append(r)
    return rules


def build(data: dict) -> dict:
    routing = data["routing"]
    rules: list[dict] = []

    # 1. hard guardrails
    rules.append({"type": "field", "outboundTag": ob.TAG_BLOCK, "protocol": ["bittorrent"]})
    rules.append({"type": "field", "outboundTag": ob.TAG_BLOCK,
                  "ip": ["geoip:private"], "network": "tcp,udp"})
    rules.append({"type": "field", "outboundTag": ob.TAG_BLOCK, "port": "135,137,138,139"})

    # 2. user edits (highest priority after guardrails)
    user = data.get("rules", {})
    rules += _rule(ob.TAG_BLOCK, user.get("block", []))
    rules += _rule(ob.TAG_DIRECT, user.get("direct", []))
    if data["outbounds"]["warp"]:
        rules += _rule(ob.TAG_WARP, user.get("warp", []))
    if data["outbounds"]["tor"]:
        rules += _rule(ob.TAG_TOR, user.get("tor", []))

    # 3. country template: in-country stays direct
    dom, ips = COUNTRY_DIRECT.get(routing.get("country") or "none", ([], []))
    if dom:
        rules.append({"type": "field", "outboundTag": ob.TAG_DIRECT, "domain": dom})
    if ips:
        rules.append({"type": "field", "outboundTag": ob.TAG_DIRECT, "ip": ips})

    # 4. exit mode: everything else
    if routing.get("mode") == "tunnel" and routing.get("tunnel") in ("warp", "tor"):
        tag = ob.TAG_WARP if routing["tunnel"] == "warp" else ob.TAG_TOR
        rules.append({"type": "field", "outboundTag": tag, "network": "tcp,udp"})
    else:
        rules.append({"type": "field", "outboundTag": ob.TAG_DIRECT, "network": "tcp,udp"})

    return {"domainStrategy": "IPIfNonMatch", "rules": rules}
