"""Routing rules: base guardrails + template + exit mode + user edits."""
from __future__ import annotations

import outbounds as ob

# Country -> (domain matchers, ip matchers) that identify "in-country" traffic.
# This traffic is NEVER sent direct from the server: a VPS reaching straight
# into that country's networks (banks, gov, ISPs...) burns/exposes the
# server's real IP to that country's monitoring, which is exactly what
# usually gets a hosting IP blacklisted. It always exits via WARP/TOR, or is
# blocked outright -- see `country_exit` in routing state.
COUNTRY_MATCHERS = {
    "russia": (["geosite:category-ru", "geosite:category-gov-ru"], ["geoip:ru"]),
    "iran": (["geosite:category-ir"], ["geoip:ir"]),
    "china": (["geosite:cn"], ["geoip:cn"]),
}

# Global, non-country-specific destinations for the "popular" template: send
# these direct (fast, no extra hop) and push everything else through a
# tunnel. Picked from tags present in both the upstream v2fly
# domain-list-community geosite.dat and Loyalsoldier's superset (what
# XTLS/Xray-install ships), so they exist on essentially any install.
POPULAR_DOMAINS = [
    "geosite:google", "geosite:youtube", "geosite:instagram", "geosite:facebook",
    "geosite:twitter", "geosite:telegram", "geosite:whatsapp", "geosite:netflix",
    "geosite:tiktok", "geosite:discord", "geosite:spotify", "geosite:github",
    "geosite:microsoft", "geosite:apple", "geosite:amazon", "geosite:openai",
]

_EXIT_TAGS = {"warp": ob.TAG_WARP, "tor": ob.TAG_TOR, "block": ob.TAG_BLOCK,
              "direct": ob.TAG_DIRECT}

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

    template = routing.get("template") or "none"

    # 3. template rules
    if template in COUNTRY_MATCHERS:
        # In-country traffic: WARP / TOR / block -- never direct.
        exit_name = routing.get("country_exit")
        if exit_name not in ("warp", "tor", "block"):
            exit_name = "block"
        tag = _EXIT_TAGS[exit_name]
        dom, ips = COUNTRY_MATCHERS[template]
        if dom:
            rules.append({"type": "field", "outboundTag": tag, "domain": dom})
        if ips:
            rules.append({"type": "field", "outboundTag": tag, "ip": ips})
    elif template == "popular":
        rules.append({"type": "field", "outboundTag": ob.TAG_DIRECT,
                      "domain": list(POPULAR_DOMAINS)})

    # 4. exit mode: everything else
    if template == "popular":
        # Everything outside the popular list goes through a tunnel.
        tunnel = routing.get("tunnel") if routing.get("tunnel") in ("warp", "tor") else "warp"
        rules.append({"type": "field", "outboundTag": _EXIT_TAGS[tunnel], "network": "tcp,udp"})
    elif routing.get("mode") == "tunnel" and routing.get("tunnel") in ("warp", "tor"):
        rules.append({"type": "field", "outboundTag": _EXIT_TAGS[routing["tunnel"]],
                      "network": "tcp,udp"})
    else:
        rules.append({"type": "field", "outboundTag": ob.TAG_DIRECT, "network": "tcp,udp"})

    return {"domainStrategy": "IPIfNonMatch", "rules": rules}
