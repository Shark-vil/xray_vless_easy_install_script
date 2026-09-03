"""State-mutating operations. Each returns True when the state changed."""
from __future__ import annotations

import inbounds as ibmod
import reality
import sites
import state as st
import util


def _used_ports(data: dict) -> set[int]:
    ports: set[int] = set()
    for ib in data["inbounds"]:
        for key in ("port", "socks_port"):
            if isinstance(ib.get(key), int):
                ports.add(ib[key])
    return ports


def _ensure_domain(data: dict) -> None:
    if data.get("domain"):
        return
    dom = util.prompt("Your real domain (A record -> this server)")
    if not dom:
        util.die("this inbound type needs a domain")
    data["domain"] = dom
    if not data.get("email"):
        data["email"] = util.prompt("Email for Let's Encrypt", f"admin@{dom}")
    data["cert"]["mode"] = "letsencrypt"
    data["cert"]["fullchain"] = f"/etc/letsencrypt/live/{dom}/fullchain.pem"
    data["cert"]["privkey"] = f"/etc/letsencrypt/live/{dom}/privkey.pem"


def _new_inbound(data: dict, itype: str, opts: dict) -> dict:
    tag = opts.get("tag") or ibmod.default_tag(itype)
    if st.inbound_by_tag(data, tag):
        util.die(f"inbound tag {tag!r} already exists")
    if itype in ("vless-tls", "vless-ws", "vless-xhttp-tls"):
        _ensure_domain(data)
    ib: dict = {"type": itype, "tag": tag, "uuid": util.new_uuid(),
                "email": data.get("email") or "user@xvei"}

    if itype == "vless-tls":
        ib["port"] = 443
        # a standalone xhttp-tls was owning :443; fold it into the fallback
        x = st.get_type(data, "vless-xhttp-tls")
        if x and x.get("standalone"):
            x.pop("standalone", None)
            x.pop("port", None)
    elif itype == "vless-ws":
        if not st.has_type(data, "vless-tls"):
            util.die("vless-ws needs vless-tls first (it rides its :443 fallback)")
        ib["ws_path"] = util.token(12)
    elif itype == "vless-xhttp-reality":
        used = _used_ports(data)
        default_port = "443" if 443 not in used else "8443"
        port = int(opts.get("port") or util.prompt("REALITY listen port", default_port))
        if port in used:
            util.die(f"port {port} already used by another inbound")
        dest_in = opts.get("dest") or util.prompt(
            "Masquerade site (SNI to borrow)", reality.DEFAULT_DESTS[0])
        dest, name = reality.normalize_dest(dest_in)
        priv, pub = reality.gen_keypair()
        ib.update(port=port, dest=dest, server_names=[name],
                  private_key=priv, public_key=pub,
                  short_ids=[reality.gen_short_id()], xhttp_path=util.token(12))
    elif itype == "vless-xhttp-tls":
        ib["xhttp_path"] = util.token(12)
        if not st.has_type(data, "vless-tls"):
            ib["standalone"] = True
            ib["port"] = 443
    elif itype == "shadowsocks":
        used = _used_ports(data)
        port = int(opts.get("port") or util.prompt("Shadowsocks port", "5465"))
        if port in used:
            util.die(f"port {port} already used")
        method = opts.get("method") or util.choose(
            "Encryption method",
            [(m, m) for m in ibmod.SS_METHODS], ibmod.SS_METHODS[0])
        ib.update(port=port, method=method, password=util.rand_password(16))
    elif itype == "hysteria2":
        used = _used_ports(data)
        port = int(opts.get("port") or util.prompt("Hysteria2 UDP port", "443"))
        socks_port = 10808
        while socks_port in used:
            socks_port += 1
        ib.update(port=port, socks_port=socks_port,
                  password=util.rand_password(16),
                  up_mbps=int(opts.get("up_mbps") or 0),
                  down_mbps=int(opts.get("down_mbps") or 0))
    else:
        util.die(f"unknown inbound type {itype!r}")
    return ib


def add_inbound(data: dict, itype: str, **opts) -> bool:
    if itype not in st.INBOUND_TYPES:
        util.die(f"unknown inbound type {itype!r}; one of {', '.join(st.INBOUND_TYPES)}")
    if st.has_type(data, itype):
        util.warn(f"{itype} already configured; remove it first to recreate")
        return False
    ib = _new_inbound(data, itype, opts)
    data["inbounds"].append(ib)
    util.ok(f"added inbound {ib['tag']} ({itype})")
    return True


def remove_inbound(data: dict, tag: str) -> bool:
    ib = st.inbound_by_tag(data, tag)
    if not ib:
        util.die(f"no inbound tagged {tag!r}")
    if ib["type"] == "vless-tls":
        deps = [x["tag"] for x in data["inbounds"]
                if x["type"] in ("vless-ws",) or
                (x["type"] == "vless-xhttp-tls" and not x.get("standalone"))]
        if deps:
            util.die(f"remove {', '.join(deps)} first (they ride vless-tls)")
    data["inbounds"] = [x for x in data["inbounds"] if x["tag"] != tag]
    util.ok(f"removed inbound {tag}")
    return True


def set_outbound(data: dict, name: str, on: bool) -> bool:
    if name not in ("warp", "tor"):
        util.die("outbound must be 'warp' or 'tor'")
    if data["outbounds"][name] == on:
        return False
    if not on:
        r = data["routing"]
        if r.get("tunnel") == name:
            util.die(f"{name} is the active tunnel; switch the template first "
                     f"(template {r.get('template', 'none')} --direct)")
        if r.get("country_exit") == name:
            util.die(f"{name} is the exit for in-country traffic; switch the "
                     f"template first (template {r.get('template')} --exit "
                     "block|warp|tor)")
    data["outbounds"][name] = on
    if not on:
        data["rules"][name] = []
    util.ok(f"{'enabled' if on else 'disabled'} {name} outbound")
    return True


def rule_op(data: dict, op: str, bucket: str, matches: list[str]) -> bool:
    if bucket not in st.RULE_BUCKETS:
        util.die(f"bucket must be one of {', '.join(st.RULE_BUCKETS)}")
    if bucket in ("warp", "tor") and not data["outbounds"][bucket]:
        util.die(f"enable the {bucket} outbound first (add-outbound {bucket})")
    cur = data["rules"].setdefault(bucket, [])
    if op == "list":
        for m in cur:
            print(m)
        return False
    if not matches:
        util.die("no matchers given")
    changed = False
    if op == "add":
        for m in matches:
            if m not in cur:
                cur.append(m)
                changed = True
    elif op == "remove":
        for m in matches:
            if m in cur:
                cur.remove(m)
                changed = True
    else:
        util.die("op must be add | remove | list")
    if changed:
        util.ok(f"{op} {bucket}: {', '.join(matches)}")
    return changed


def set_template(data: dict, template: str, *, country_exit: str | None = None,
                  mode: str | None = None, tunnel: str | None = None) -> bool:
    if template not in st.TEMPLATES:
        util.die(f"template must be one of {', '.join(st.TEMPLATES)}")

    r = data["routing"]
    before = dict(r)

    if template in st.COUNTRY_TEMPLATES:
        if country_exit not in ("warp", "tor", "block"):
            util.die("country templates need --exit warp|tor|block "
                      "(in-country traffic is never sent direct from the server "
                      "-- that would expose its real IP)")
        if country_exit in ("warp", "tor"):
            data["outbounds"][country_exit] = True
        mode = mode or r.get("mode") or "direct"
        if mode not in ("direct", "tunnel"):
            util.die("mode must be 'direct' or 'tunnel'")
        if mode == "tunnel":
            if tunnel not in ("warp", "tor"):
                util.die("tunnel mode needs --tunnel warp|tor")
            data["outbounds"][tunnel] = True
        r["template"] = template
        r["country_exit"] = country_exit
        r["mode"] = mode
        r["tunnel"] = tunnel if mode == "tunnel" else None

    elif template == "popular":
        if tunnel not in ("warp", "tor"):
            util.die("the 'popular' template needs --tunnel warp|tor "
                      "(everything outside the popular list goes through it)")
        data["outbounds"][tunnel] = True
        r["template"] = "popular"
        r["country_exit"] = None
        r["mode"] = "tunnel"
        r["tunnel"] = tunnel

    else:  # none
        mode = mode or "direct"
        if mode not in ("direct", "tunnel"):
            util.die("mode must be 'direct' or 'tunnel'")
        if mode == "tunnel":
            if tunnel not in ("warp", "tor"):
                util.die("tunnel mode needs --tunnel warp|tor")
            data["outbounds"][tunnel] = True
        r["template"] = "none"
        r["country_exit"] = None
        r["mode"] = mode
        r["tunnel"] = tunnel if mode == "tunnel" else None

    changed = r != before
    if changed:
        detail = f"exit={r['mode']}" + (f" via {r['tunnel']}" if r["tunnel"] else "")
        if r.get("country_exit"):
            detail = f"in-country -> {r['country_exit']}, rest {detail}"
        util.ok(f"template: {template}, {detail}")
    return changed


def set_site(data: dict, kind: str, proxy_url: str | None = None) -> bool:
    valid = {"auth", "blank", "404", "proxy"} | set(sites.STATIC_PRESETS)
    if kind not in valid:
        util.die(f"site must be one of: {', '.join(sorted(valid))}")
    site = data.setdefault("site", {"type": "auth", "proxy_url": ""})
    before = dict(site)
    site["type"] = kind
    if kind == "proxy":
        raw = proxy_url or util.prompt(
            "Upstream to proxy (preset name or URL)", "example")
        url = sites.resolve_proxy_url(raw)
        if not url or "://" not in url:
            util.die("invalid upstream URL")
        site["proxy_url"] = url
    else:
        site["proxy_url"] = ""
    changed = site != before
    if changed:
        tail = f" -> {site['proxy_url']}" if kind == "proxy" else ""
        util.ok(f"camouflage site: {kind}{tail}")
        if "cert" not in st.needs(data):
            util.warn("no TLS/fallback inbound present — the site only takes "
                      "effect once you add vless-tls / vless-xhttp-tls")
    return changed


def menu_site(data: dict) -> bool:
    cur = (data.get("site") or {}).get("type", "auth")
    opts = [
        ("auth", "HTTP Basic auth prompt to nowhere (default)"),
        ("blank", "Bare 'It works' page"),
        ("404", "Plain 404"),
    ]
    for name, title in sites.STATIC_PRESETS.items():
        opts.append((name, f"Static: {title}"))
    opts.append(("proxy", "Reverse-proxy a real site (presets or custom URL)"))
    kind = util.choose(f"Camouflage site (current: {cur})", opts, cur)
    proxy_url = None
    if kind == "proxy":
        pos = [(k, f"{k}  ({v})") for k, v in sites.PROXY_PRESETS.items()]
        pos.append(("custom", "Enter a custom URL"))
        pick = util.choose("Upstream", pos)
        proxy_url = util.prompt("URL") if pick == "custom" else pick
    return set_site(data, kind, proxy_url)


# ---- interactive menus (driven from lib/menu.sh) -----------------------

def _list_inbounds(data: dict) -> None:
    if not data["inbounds"]:
        print("  (none)")
    for ib in data["inbounds"]:
        extra = ""
        if ib.get("port"):
            extra = f" :{ib['port']}"
        print(f"  - {ib['tag']:<16} {ib['type']}{extra}")


def menu_inbounds(data: dict) -> bool:
    while True:
        print("\n-- Inbounds --")
        _list_inbounds(data)
        act = util.choose("Action", [
            ("add", "Add inbound"),
            ("del", "Remove inbound"),
            ("back", "Back"),
        ], "back")
        if act == "back":
            return False
        if act == "add":
            itype = util.choose("Type", [
                ("vless-tls", "VLESS TLS (Vision, :443)"),
                ("vless-ws", "VLESS WebSocket (fallback on :443)"),
                ("vless-xhttp-reality", "VLESS XHTTP + REALITY (site masquerade, no domain)"),
                ("vless-xhttp-tls", "VLESS XHTTP + TLS certificate"),
                ("shadowsocks", "Shadowsocks"),
                ("hysteria2", "Hysteria2 (via local SOCKS5 -> Xray)"),
            ])
            if add_inbound(data, itype):
                return True
        elif act == "del":
            if not data["inbounds"]:
                continue
            tag = util.choose("Remove which", [(x["tag"], x["tag"]) for x in data["inbounds"]])
            if remove_inbound(data, tag):
                return True


def menu_outbounds(data: dict) -> bool:
    while True:
        print("\n-- Outbounds --")
        print(f"  WARP: {'on' if data['outbounds']['warp'] else 'off'}")
        print(f"  TOR : {'on' if data['outbounds']['tor'] else 'off'}")
        act = util.choose("Action", [
            ("warp", "Toggle WARP"),
            ("tor", "Toggle TOR"),
            ("back", "Back"),
        ], "back")
        if act == "back":
            return False
        cur = data["outbounds"][act]
        if set_outbound(data, act, not cur):
            return True


def menu_rules(data: dict) -> bool:
    buckets = ["block", "direct"]
    if data["outbounds"]["warp"]:
        buckets.append("warp")
    if data["outbounds"]["tor"]:
        buckets.append("tor")
    while True:
        print("\n-- Routing rules --")
        for b in buckets:
            print(f"  [{b}] " + (", ".join(data['rules'].get(b, [])) or "(empty)"))
        bucket = util.choose("Bucket", [(b, b) for b in buckets] + [("back", "Back")], "back")
        if bucket == "back":
            return False
        op = util.choose("Operation", [("add", "Add matcher"), ("remove", "Remove matcher")])
        val = util.prompt("Matcher (e.g. geosite:openai, domain:example.com, geoip:de, 1.2.3.0/24)")
        if val and rule_op(data, op, bucket, [val]):
            return True


def menu_template(data: dict) -> bool:
    r = data["routing"]
    template = util.choose("Template", [
        ("russia", "Russia (geoip:ru + category-ru -> WARP/TOR/block, never direct)"),
        ("iran", "Iran (geoip:ir + category-ir -> WARP/TOR/block, never direct)"),
        ("china", "China (geoip:cn + geosite:cn -> WARP/TOR/block, never direct)"),
        ("popular", "Popular direct (YouTube/Instagram/... direct, rest via WARP/TOR)"),
        ("none", "None (only private direct)"),
    ], r.get("template") or "none")

    if template in st.COUNTRY_TEMPLATES:
        country_exit = util.choose(
            "In-country traffic exits via",
            [("warp", "WARP (Cloudflare)"), ("tor", "TOR"), ("block", "Block outright")],
            r.get("country_exit") or "block")
        mode = util.choose("Exit mode for everything else", [
            ("direct", "Direct"),
            ("tunnel", "Through a tunnel (WARP/TOR)"),
        ], r.get("mode") or "direct")
        tunnel = None
        if mode == "tunnel":
            tunnel = util.choose("Tunnel", [("warp", "WARP (Cloudflare)"), ("tor", "TOR")],
                                  r.get("tunnel") or "warp")
        return set_template(data, template, country_exit=country_exit, mode=mode, tunnel=tunnel)

    if template == "popular":
        tunnel = util.choose("Tunnel for everything outside the popular list",
                              [("warp", "WARP (Cloudflare)"), ("tor", "TOR")],
                              r.get("tunnel") or "warp")
        return set_template(data, template, tunnel=tunnel)

    mode = util.choose("Exit mode", [
        ("direct", "Everything direct"),
        ("tunnel", "Everything through a tunnel (WARP/TOR)"),
    ], r.get("mode") or "direct")
    tunnel = None
    if mode == "tunnel":
        tunnel = util.choose("Tunnel", [("warp", "WARP (Cloudflare)"), ("tor", "TOR")],
                              r.get("tunnel") or "warp")
    return set_template(data, template, mode=mode, tunnel=tunnel)
