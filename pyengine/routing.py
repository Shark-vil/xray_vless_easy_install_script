"""Routing rules in config.json: guardrails, templates, exit, matchers.

Nothing here is kept outside config.json. A template's rules are recognised
by what they match - a country's domain rule followed by its IP rule, both to
the same outbound, or the exact "popular" list to direct; a rule edited by
hand is no longer the template's, it is an ordinary rule. The exit is the
last rule when it catches everything.
"""
from __future__ import annotations

import xrayconf as xc

# Country -> (domain matchers, ip matchers) that identify "in-country" traffic.
# This traffic is NEVER sent direct from the server: a VPS reaching straight
# into that country's networks (banks, gov, ISPs...) burns/exposes the
# server's real IP to that country's monitoring, which is exactly what
# usually gets a hosting IP blacklisted. It always exits via WARP/TOR, or is
# blocked outright.
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

# a fresh config starts with these
GUARD_RULES = [
    {"type": "field", "outboundTag": "block", "protocol": ["bittorrent"]},
    {"type": "field", "outboundTag": "block", "ip": ["geoip:private"], "network": "tcp,udp"},
    {"type": "field", "outboundTag": "block", "port": "135,137,138,139"},
]


def exit_rule(tag: str) -> dict:
    return {"type": "field", "outboundTag": tag, "network": "tcp,udp"}


def template_rules(template: str, tag: str | None = None) -> list[dict]:
    """The rules of a template; `tag` is where in-country traffic goes."""
    if template in COUNTRY_MATCHERS:
        dom, ips = COUNTRY_MATCHERS[template]
        return [{"type": "field", "outboundTag": tag or "block", "domain": list(dom)},
                {"type": "field", "outboundTag": tag or "block", "ip": list(ips)}]
    if template == "popular":
        return [{"type": "field", "outboundTag": "direct", "domain": list(POPULAR_DOMAINS)}]
    return []


def _matchers(rule: dict) -> dict:
    return {k: v for k, v in rule.items() if k not in ("type", "outboundTag")}


def template_marks(rules: list[dict]) -> dict[int, str]:
    """{index: template name} of the rules that make up a template."""
    marks: dict[int, str] = {}
    popular = _matchers(template_rules("popular")[0])
    for i, r in enumerate(rules):
        if r.get("outboundTag") == "direct" and _matchers(r) == popular:
            marks[i] = "popular"
            continue
        if i + 1 >= len(rules) or r.get("outboundTag") != rules[i + 1].get("outboundTag"):
            continue
        for name in COUNTRY_MATCHERS:
            dom, ips = template_rules(name)
            if _matchers(r) == _matchers(dom) and _matchers(rules[i + 1]) == _matchers(ips):
                marks[i] = marks[i + 1] = name
    return marks


def is_exit(rule: dict) -> bool:
    """A rule that catches all traffic: only network tcp,udp and a target."""
    m = _matchers(rule)
    return set(m) == {"network"} and str(m["network"]).replace(" ", "") in (
        "tcp,udp", "udp,tcp") and bool(rule.get("outboundTag"))


def detect(cfg: dict) -> dict:
    """{"template": name, "country_exit": tag or None, "exit": tag or None}."""
    rules = xc.rules_view(cfg)
    out = {"template": "none", "country_exit": None, "exit": None}
    for i, name in template_marks(rules).items():
        out["template"] = name
        if name in COUNTRY_MATCHERS:
            out["country_exit"] = rules[i].get("outboundTag")
    if rules and is_exit(rules[-1]):
        out["exit"] = rules[-1]["outboundTag"]
    return out


def apply_template(cfg: dict, template: str, *, country_exit: str | None = None,
                   exit: str | None = "keep") -> bool:
    """Replace the template's rules (they go right before the exit) and set the
    exit: "keep" leaves it, None removes it, a tag catches everything there."""
    rules = xc.rules(cfg)
    before = [dict(r) for r in rules]
    tail = rules[-1] if rules and is_exit(rules[-1]) else None
    marks = template_marks(rules)
    body = [r for i, r in enumerate(rules[:-1] if tail else rules) if i not in marks]
    body += template_rules(template, country_exit)
    if exit != "keep":
        tail = exit_rule(exit) if exit else None
    rules[:] = body + ([tail] if tail else [])
    return rules != before


# ---- matchers: "send these domains / IPs to that outbound" ------------------

_DOMAIN_PREFIXES = ("geosite:", "domain:", "full:", "regexp:", "keyword:")


def _looks_ip(s: str) -> bool:
    import ipaddress

    try:
        ipaddress.ip_address(s.split("/")[0])
        return True
    except ValueError:
        return False


def split_matcher(item: str) -> tuple[str, str]:
    """("domain" | "ip", normalised matcher)."""
    item = item.strip()
    if item.startswith(_DOMAIN_PREFIXES):
        return "domain", item
    if item.startswith("geoip:") or "/" in item or _looks_ip(item):
        return "ip", item
    return "domain", "domain:" + item


def _simple(rule: dict, tag: str, kind: str) -> bool:
    """A rule that only sends one kind of matcher to `tag`."""
    return rule.get("outboundTag") == tag and set(_matchers(rule)) == {kind} \
        and isinstance(rule.get(kind), list)


def _first_free_slot(rules: list[dict]) -> int:
    i = 0
    while i < len(rules) and any(rules[i] == g for g in GUARD_RULES):
        i += 1
    return i


def add_matcher(cfg: dict, tag: str, item: str) -> bool:
    """Add to the first plain rule that sends such matchers to `tag`, or to a
    new one at the top (after the guardrails): checked before the rest."""
    kind, value = split_matcher(item)
    rules = xc.rules(cfg)
    marks = template_marks(rules)
    rule = next((r for i, r in enumerate(rules) if _simple(r, tag, kind) and i not in marks), None)
    if rule is None:
        rules.insert(_first_free_slot(rules), {"type": "field", "outboundTag": tag, kind: [value]})
        return True
    if value in rule[kind]:
        return False
    rule[kind].append(value)
    return True


def remove_matcher(cfg: dict, tag: str, item: str) -> bool:
    kind, value = split_matcher(item)
    rules = xc.rules(cfg)
    marks = template_marks(rules)
    for r in [r for i, r in enumerate(rules) if i not in marks]:
        if _simple(r, tag, kind) and value in r[kind]:
            r[kind].remove(value)
            if not r[kind]:
                rules.remove(r)
            return True
    return False


def matchers_for(cfg: dict, tag: str) -> list[str]:
    """Everything plain rules send to `tag` (template rules not counted)."""
    out: list[str] = []
    rules = xc.rules_view(cfg)
    marks = template_marks(rules)
    for i, r in enumerate(rules):
        if i in marks:
            continue
        for kind in ("domain", "ip"):
            if _simple(r, tag, kind):
                out += [m for m in r[kind] if m not in out]
    return out
