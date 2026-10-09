"""Changes to config.json (and the xvei state). Each returns True when
something changed; the caller then stages the config for lib/apply.sh.

`data` is the xvei state, `cfg` the config.json being changed. Everything
works on whatever is in config.json - inbounds, outbounds and rules added by
hand are listed, linked, used and removed like the ones xvei added.
"""
from __future__ import annotations

import os
import re

import inbounds as ibmod
import outbounds as obmod
import proxylinks
import reality
import routing
import sites
import state as st
import util
import xrayconf as xc


# lib/hysteria2.sh touches this when xvei itself set up Hysteria2
HY2_MARKER = "/var/lib/xvei/managed/hysteria2"


def _used_ports(data: dict, cfg: dict) -> set[int]:
    ports = xc.used_ports(cfg)
    for name in ("hysteria2", "turnable"):
        rec = st.service(data, cfg, name)
        if rec:
            ports |= {rec[k] for k in ("port", "socks_port", "local_port")
                      if isinstance(rec.get(k), int)}
    return ports


def _port_owner(cfg: dict, port: int) -> str:
    return next((x.get("tag") or "?" for x in xc.inbounds(cfg) if xc.port_of(x) == port), "?")


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


def _free_socket(cfg: dict, base: str) -> str:
    taken = {str(x.get("listen")) for x in xc.inbounds(cfg)}
    sock, n = base, 2
    while sock in taken:
        sock, n = f"{base}-{n}", n + 1
    return sock


def _is_catch_all(fb: dict) -> bool:
    return not any(k in fb for k in ("path", "alpn", "name"))


# ---- inbounds ---------------------------------------------------------------

def _new_record(data: dict, cfg: dict, itype: str, opts: dict) -> dict:
    """Everything needed to build the new inbound: tag, credentials, ports..."""
    tag = opts.get("tag") or ibmod.default_tag(itype)
    if tag in xc.tags(cfg):
        util.die(f"tag {tag!r} is already used in config.json (pick another with --tag)")
    if itype in ("hysteria2", "turnable") and st.service(data, cfg, itype):
        util.die(f"{itype} is already set up ({data[itype]['tag']}); remove it first")
    if (itype == "hysteria2" and os.path.exists("/etc/hysteria/config.yaml")
            and not os.path.exists(HY2_MARKER)):
        util.die("Hysteria2 is already configured on this server outside xvei "
                 "(/etc/hysteria/config.yaml); xvei will not overwrite it")
    if itype in st.TLS_TYPES:
        _ensure_domain(data)
    ib: dict = {"type": itype, "tag": tag, "uuid": util.new_uuid(),
                "email": data.get("email") or "user@xvei"}
    used = _used_ports(data, cfg)

    if itype == "vless-tls":
        if 443 in xc.used_ports(cfg):
            util.die(f"port 443 is already used by {_port_owner(cfg, 443)}")
        ib["port"] = 443
    elif itype in st.FALLBACK_TYPES:
        if not xc.terminator(cfg):
            util.die(f"{itype} rides the fallbacks of a TLS inbound on :443; "
                     "add vless-tls first")
        if itype != "trojan-tcp":
            ib["ws_path"] = util.token(12)
        if itype.startswith("trojan"):
            ib["password"] = util.token(16)
    elif itype == "vless-xhttp-reality":
        default_port = "443" if 443 not in used else "8443"
        port = int(opts.get("port") or util.prompt("REALITY listen port", default_port))
        if port in used:
            util.die(f"port {port} is already used by {_port_owner(cfg, port)}")
        dest_in = opts.get("dest") or util.prompt(
            "Masquerade site (SNI to borrow)", reality.DEFAULT_DESTS[0])
        dest, name = reality.normalize_dest(dest_in)
        priv, pub = reality.gen_keypair()
        ib.update(port=port, dest=dest, server_names=[name],
                  private_key=priv, public_key=pub,
                  short_ids=[reality.gen_short_id()], xhttp_path=util.token(12))
    elif itype == "vless-xhttp-tls":
        ib["xhttp_path"] = util.token(12)
        if not xc.terminator(cfg):
            if 443 in xc.used_ports(cfg):
                util.die(f"port 443 is used by {_port_owner(cfg, 443)}, which has no "
                         "fallbacks to carry XHTTP")
            ib["standalone"] = True
            ib["port"] = 443
    elif itype == "shadowsocks":
        port = int(opts.get("port") or util.prompt("Shadowsocks port", "5465"))
        if port in used:
            util.die(f"port {port} is already used by {_port_owner(cfg, port)}")
        method = opts.get("method") or util.choose(
            "Encryption method",
            [(m, m) for m in ibmod.SS_METHODS], ibmod.SS_METHODS[0])
        ib.update(port=port, method=method, password=util.rand_password(16))
    elif itype == "hysteria2":
        port = int(opts.get("port") or util.prompt("Hysteria2 UDP port", "443"))
        socks_port = 10808
        while socks_port in used:
            socks_port += 1
        ib.update(port=port, socks_port=socks_port,
                  password=util.rand_password(16),
                  up_mbps=int(opts.get("up_mbps") or 0),
                  down_mbps=int(opts.get("down_mbps") or 0))
    elif itype == "turnable":
        util.warn("Turnable is UNSTABLE and NOT anonymous: VK relays the traffic "
                  "and sees this server's real IP address; VK can break it at any time.")
        port = int(opts.get("port") or util.prompt("Turnable UDP port", "56000"))
        if port in used:
            util.die(f"port {port} already used")
        raw = opts.get("dest") or util.prompt(
            "VK call link or ID (any public https://vk.com/call/join/... link)")
        call_id = raw.strip().rstrip("/").split("/call/join/")[-1].split("?")[0]
        if not re.fullmatch(r"[A-Za-z0-9_-]{4,}", call_id):
            util.die("not a VK call link or ID")
        local_port = 10900
        while local_port in used:
            local_port += 1
        ib.update(port=port, call_id=call_id, local_port=local_port,
                  turnable_uuid=util.new_uuid(), peers=5)
    else:
        util.die(f"unknown inbound type {itype!r}")
    return ib


def add_inbound(data: dict, cfg: dict, itype: str, **opts) -> bool:
    if itype not in st.INBOUND_TYPES:
        util.die(f"unknown inbound type {itype!r}; one of {', '.join(st.INBOUND_TYPES)}")
    ib = _new_record(data, cfg, itype, opts)
    obj = ibmod.build(ib, data)

    if itype in ibmod.SOCKETS and not ib.get("standalone"):
        sock = _free_socket(cfg, ibmod.SOCKETS[itype])
        obj["listen"] = sock
        fbs = xc.terminator(cfg)["settings"]["fallbacks"]
        if itype == "trojan-tcp":
            # Trojan takes over the catch-all and falls back to where it went
            catch = next((f for f in fbs if _is_catch_all(f)), None)
            if catch and str(catch.get("dest", "")).startswith(("@", "/")):
                util.die(f"the catch-all fallback already goes to {catch['dest']}")
            obj["settings"]["fallbacks"] = [{"dest": catch["dest"] if catch else 8080, "xver": 0}]
            if catch:
                catch["dest"] = sock
            else:
                fbs.append({"dest": sock, "xver": 0})
        else:
            path = "/" + (ib.get("ws_path") or ib.get("xhttp_path"))
            fbs.insert(0, {"path": path, "dest": sock, "xver": 0})

    cfg.setdefault("inbounds", []).append(obj)
    data["owned"]["inbounds"][ib["tag"]] = itype
    if itype == "hysteria2":
        data["hysteria2"] = {k: ib[k] for k in (
            "tag", "port", "socks_port", "password", "up_mbps", "down_mbps")}
    elif itype == "turnable":
        data["turnable"] = {k: ib.get(k) for k in (
            "tag", "port", "call_id", "local_port", "turnable_uuid", "peers")}
    util.ok(f"added inbound {ib['tag']} ({itype})")
    return True


def remove_inbound(data: dict, cfg: dict, tag: str) -> bool:
    ib = xc.find_inbound(cfg, tag)
    if ib is None:
        util.die(f"no inbound tagged {tag!r} in config.json")
    used = xc.rule_users(cfg, inbound=tag)
    if used:
        util.die(f"routing rule(s) {', '.join(map(str, used))} use inbound {tag!r}; "
                 "remove them first")
    own_fbs = (ib.get("settings") or {}).get("fallbacks") or []
    riders = [x.get("tag") or "?" for x in xc.inbounds(cfg) if x is not ib
              and any(str(f.get("dest")) == str(x.get("listen")) for f in own_fbs)]
    if riders:
        util.die(f"remove {', '.join(riders)} first (they ride {tag}'s fallbacks)")
    # fallbacks that hand traffic to it: drop them; a catch-all that Trojan took
    # over goes back to where Trojan itself fell back to
    dests = {str(ib.get("listen") or ""), str(ib.get("port") or "")} - {""}
    own_catch = next((f.get("dest") for f in own_fbs if _is_catch_all(f)), None)
    for x in xc.inbounds(cfg):
        fbs = (x.get("settings") or {}).get("fallbacks")
        if not isinstance(fbs, list):
            continue
        for f in list(fbs):
            if str(f.get("dest")) in dests:
                if _is_catch_all(f) and own_catch is not None:
                    f["dest"] = own_catch
                else:
                    fbs.remove(f)
    cfg["inbounds"] = [x for x in xc.inbounds(cfg) if x is not ib]
    data["owned"]["inbounds"].pop(tag, None)
    for name in ("hysteria2", "turnable"):
        if (data.get(name) or {}).get("tag") == tag:
            data[name] = None
    util.ok(f"removed inbound {tag}")
    return True


def sync_cert(data: dict, cfg: dict) -> bool:
    """Point xvei's TLS inbounds at the certificate in the state (after it was
    issued, replaced by a self-signed one, or the domain changed)."""
    fc, pk = data["cert"].get("fullchain"), data["cert"].get("privkey")
    if not fc or not pk:
        return False
    changed = False
    for tag in st.owned_present(data, cfg):
        tls = ((xc.find_inbound(cfg, tag).get("streamSettings") or {}).get("tlsSettings"))
        if isinstance(tls, dict) and "certificates" in tls:
            want = [{"certificateFile": fc, "keyFile": pk}]
            if tls["certificates"] != want:
                tls["certificates"] = want
                changed = True
    return changed


# ---- outbounds --------------------------------------------------------------

def set_builtin(data: dict, cfg: dict, name: str, on: bool) -> bool:
    """xvei's own WARP / TOR: an outbound in config.json plus the service."""
    if name not in ("warp", "tor"):
        util.die("must be 'warp' or 'tor'")
    tag = st.builtin_tag(name)
    present = xc.find_outbound(cfg, tag) is not None
    if on:
        if present:
            if data["owned"][name]:
                return False
            util.die(f"config.json already has an outbound {tag!r} (not set up by xvei); "
                     f"use it directly, as {tag}")
        cfg.setdefault("outbounds", []).append(obmod.builtin(name))
        data["owned"][name] = True
        util.ok(f"enabled {name.upper()} (outbound {tag})")
        return True
    if not present:
        was = data["owned"][name]
        data["owned"][name] = False
        return was
    if not data["owned"][name]:
        util.die(f"{tag} was not set up by xvei; to delete it: xvei remove-outbound {tag}")
    return remove_outbound(data, cfg, tag)


def _next_tag(cfg: dict, proto: str) -> str:
    proto = {"shadowsocks": "ss"}.get(proto, proto)
    taken = xc.tags(cfg)
    n = 1
    while f"{proto}{n}" in taken:
        n += 1
    return f"{proto}{n}"


def add_custom_outbound(data: dict, cfg: dict, link: str, tag: str | None = None) -> bool:
    ob, name = proxylinks.parse(link)
    for o in xc.outbounds(cfg):
        if {k: v for k, v in o.items() if k != "tag"} == ob:
            util.warn(f"this outbound is already in config.json as {o.get('tag')!r}")
            return False
    tag = tag or _next_tag(cfg, ob["protocol"])
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", tag):
        util.die("tag may only contain letters, digits, '_' and '-' (max 32)")
    if tag in xc.tags(cfg) or tag in ("warp", "tor"):
        util.die(f"tag {tag!r} is already taken")
    cfg.setdefault("outbounds", []).append({"tag": tag, **ob})
    if name:
        data["outbound_names"][tag] = name
    util.ok(f"added outbound {tag}: {proxylinks.describe(ob)}" + (f" ({name})" if name else ""))
    return True


def remove_outbound(data: dict, cfg: dict, tag: str) -> bool:
    obs = xc.outbounds(cfg)
    if not any(o.get("tag") == tag for o in obs):
        util.die(f"no outbound tagged {tag!r} in config.json")
    used = xc.rule_users(cfg, outbound=tag)
    if used:
        util.die(f"routing rule(s) {', '.join(map(str, used))} send traffic to {tag!r}; "
                 "remove them first")
    if obs[0].get("tag") == tag:
        util.warn(f"{tag} was the first outbound (Xray's default route); "
                  f"now it is {obs[1].get('tag') if len(obs) > 1 else 'none'}")
    cfg["outbounds"] = [o for o in obs if o.get("tag") != tag]
    for name in ("warp", "tor"):
        if tag == st.builtin_tag(name):
            data["owned"][name] = False
    data["outbound_names"].pop(tag, None)
    util.ok(f"removed outbound {tag}")
    return True


def tunnel_names(data: dict, cfg: dict) -> list[str]:
    """What may carry tunnelled traffic: xvei's WARP / TOR (by name) and every
    proxy outbound in config.json (by tag)."""
    names = [n for n in ("warp", "tor") if st.builtin_free(data, cfg, n)]
    mine = {st.builtin_tag(n) for n in names}
    names += [o["tag"] for o in xc.outbounds(cfg) if o.get("tag") and o["tag"] not in mine
              and o.get("protocol") not in xc.NOT_PROXIES]
    return names


def resolve_target(data: dict, cfg: dict, name: str) -> str:
    """Outbound tag for a target name; sets up xvei's WARP / TOR when named
    and missing, and "direct" / "block" when the config lacks them."""
    if name in ("warp", "tor"):
        tag = st.builtin_tag(name)
        if not xc.find_outbound(cfg, tag):
            set_builtin(data, cfg, name, True)
        return tag
    if name in ("direct", "block"):
        xc.ensure_outbound(cfg, name)
        return name
    if not xc.find_outbound(cfg, name):
        util.die(f"no outbound {name!r} in config.json")
    return name


# ---- routing ----------------------------------------------------------------

def rule_add(data: dict, cfg: dict, target: str, matchers: list[str]) -> bool:
    if not matchers:
        util.die("no matchers given")
    tag = resolve_target(data, cfg, target)
    changed = False
    for m in matchers:
        changed |= routing.add_matcher(cfg, tag, m)
    if changed:
        util.ok(f"{', '.join(matchers)} -> {tag}")
    return changed


def rule_remove(data: dict, cfg: dict, target: str, matchers: list[str]) -> bool:
    tag = st.builtin_tag(target) if target in ("warp", "tor") else target
    changed = False
    for m in matchers:
        if routing.remove_matcher(cfg, tag, m):
            changed = True
            util.ok(f"removed {m} from {tag}")
        else:
            util.warn(f"{m} is not sent to {tag} by a plain rule")
    return changed


def rule_delete(cfg: dict, number: int) -> bool:
    rules = xc.rules(cfg)
    if not 1 <= number <= len(rules):
        util.die(f"no rule #{number} (there are {len(rules)})")
    gone = rules.pop(number - 1)
    util.ok(f"deleted rule #{number}: {xc.describe_rule(gone)}")
    return True


def set_template(data: dict, cfg: dict, template: str, *, country_exit: str | None = None,
                 mode: str | None = None, tunnel: str | None = None) -> bool:
    """mode: "keep" (leave the exit rule), "direct" or "tunnel" (via `tunnel`)."""
    if template not in st.TEMPLATES:
        util.die(f"template must be one of {', '.join(st.TEMPLATES)}")
    tunnels = tunnel_names(data, cfg)

    def via(name: str | None, what: str) -> str:
        if name not in tunnels and name not in ("warp", "tor"):
            util.die(f"{what} --tunnel {'|'.join(tunnels) or 'warp|tor'}")
        return resolve_target(data, cfg, name)

    ce_tag = None
    if template in st.COUNTRY_TEMPLATES:
        if country_exit not in ["block", "warp", "tor"] + tunnels:
            util.die(f"country templates need --exit {'|'.join(['block'] + tunnels)} "
                     "(in-country traffic is never sent direct from the server "
                     "-- that would expose its real IP)")
        ce_tag = resolve_target(data, cfg, country_exit)
    if template == "popular":
        exit_tag = via(tunnel, "the 'popular' template sends everything outside the "
                               "popular list through a tunnel; it needs")
        xc.ensure_outbound(cfg, "direct")
    elif mode == "tunnel":
        exit_tag = via(tunnel, "tunnel mode needs")
    elif mode == "direct":
        exit_tag = resolve_target(data, cfg, "direct")
    else:
        exit_tag = "keep"
    changed = routing.apply_template(cfg, template, country_exit=ce_tag, exit=exit_tag)
    if changed:
        now = routing.detect(cfg)
        detail = f"everything else -> {now['exit'] or 'default route (first outbound)'}"
        if now["country_exit"]:
            detail = f"in-country -> {now['country_exit']}, {detail}"
        util.ok(f"template: {template}, {detail}")
    return changed


# ---- camouflage site ---------------------------------------------------------

def set_site(data: dict, cfg: dict, kind: str, proxy_url: str | None = None) -> bool:
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
        if "cert" not in st.needs(data, cfg):
            util.warn("xvei has no TLS inbound here - the site only takes effect "
                      "once you add vless-tls / vless-xhttp-tls")
    return changed


# ---- interactive menus (driven from lib/menu.sh) -----------------------

def _item(name: str, detail: str = "", *, dim: bool = True, width: int = 16) -> None:
    """One list line: `    • name      detail`."""
    detail = util.paint(detail, util.DIM) if dim else detail
    print(f"    {util.SYM['bullet']} {util.paint(f'{name:<{width}}', util.BOLD)} {detail}".rstrip())


def _none() -> None:
    print(util.paint("    (none)", util.DIM))


def menu_site(data: dict, cfg: dict) -> bool:
    util.header("Camouflage site")
    cur = (data.get("site") or {}).get("type", "auth")
    opts = [
        ("auth", "HTTP Basic auth prompt to nowhere (default)"),
        ("blank", "Bare 'It works' page"),
        ("404", "Plain 404"),
    ]
    for name, title in sites.STATIC_PRESETS.items():
        opts.append((name, f"Static: {title}"))
    opts.append(("proxy", "Reverse-proxy a real site (presets or custom URL)"))
    kind = util.choose(f"Camouflage site (current: {cur})", opts + [("back", "Back")], "back")
    if kind == "back":
        return False
    proxy_url = None
    if kind == "proxy":
        pos = [(k, f"{k}  ({v})") for k, v in sites.PROXY_PRESETS.items()]
        pos.append(("custom", "Enter a custom URL"))
        pick = util.choose("Upstream", pos)
        proxy_url = util.prompt("URL") if pick == "custom" else pick
    return set_site(data, cfg, kind, proxy_url)


def _list_inbounds(data: dict, cfg: dict) -> None:
    ibs = xc.inbounds(cfg)
    if not ibs:
        _none()
    for ib in ibs:
        own = st.owned_type(data, ib.get("tag", ""))
        _item(ib.get("tag") or "(no tag)", xc.inbound_detail(ib)
              + (f"   {util.SYM['sep']} xvei {own}" if own else ""))


_INBOUND_CHOICES = [
    ("vless-tls", "VLESS TLS (Vision, :443)"),
    ("vless-ws", "VLESS WebSocket (fallback on :443)"),
    ("vless-xhttp-reality", "VLESS XHTTP + REALITY (site masquerade, no domain)"),
    ("vless-xhttp-tls", "VLESS XHTTP + TLS certificate"),
    ("trojan-tcp", "Trojan (TCP, shares :443 via fallback, legacy)"),
    ("trojan-ws", "Trojan WebSocket (fallback on :443, legacy)"),
    ("vmess-ws", "VMess WebSocket (fallback on :443, legacy)"),
    ("shadowsocks", "Shadowsocks"),
    ("hysteria2", "Hysteria2 (via local SOCKS5 -> Xray)"),
    ("turnable", "Turnable via VK calls (UNSTABLE, NOT anonymous: VK sees the server IP)"),
]


def menu_inbounds(data: dict, cfg: dict) -> bool:
    while True:
        util.header("Inbounds")
        _list_inbounds(data, cfg)
        print()
        act = util.choose("Action", [
            ("add", "Add inbound"),
            ("del", "Remove inbound"),
            ("back", "Back"),
        ], "back")
        if act == "back":
            return False
        if act == "add":
            itype = util.choose("Type", _INBOUND_CHOICES + [("back", "Back")], "back")
            if itype != "back" and add_inbound(data, cfg, itype):
                return True
        elif act == "del":
            opts = [(x["tag"], x["tag"]) for x in xc.inbounds(cfg) if x.get("tag")]
            if not opts:
                continue
            tag = util.choose("Remove which", opts + [("back", "Back")], "back")
            if tag == "back":
                continue
            if not st.owned_type(data, tag) and not util.confirm(
                    f"{tag} was not added by xvei. Remove it from config.json? "
                    "Its clients stop working", default_yes=False):
                continue
            if remove_inbound(data, cfg, tag):
                return True


def _outbound_label(data: dict, o: dict) -> str:
    tag = o.get("tag") or "(no tag)"
    detail = xc.outbound_detail(o)
    name = data["outbound_names"].get(tag)
    for n in ("warp", "tor"):
        if tag == st.builtin_tag(n) and data["owned"][n]:
            name = f"xvei {n.upper()}"
    return f"{tag} ({detail})" + (f" {name}" if name else "")


def menu_outbounds(data: dict, cfg: dict) -> bool:
    while True:
        util.header("Outbounds")
        obs = xc.outbounds(cfg)
        if not obs:
            _none()
        for i, o in enumerate(obs):
            name = data["outbound_names"].get(o.get("tag"))
            extra = []
            if i == 0:
                extra.append(f"{util.SYM['back']} default route")
            for n in ("warp", "tor"):
                if o.get("tag") == st.builtin_tag(n) and data["owned"][n]:
                    extra.append(f"xvei {n.upper()}")
            if name:
                extra.append(name)
            _item(o.get("tag") or "(no tag)", xc.outbound_detail(o)
                  + (f"   {util.SYM['sep']} " + f" {util.SYM['sep']} ".join(extra) if extra else ""))
        print()
        acts = []
        for n in ("warp", "tor"):
            if st.builtin_free(data, cfg, n):
                on = st.builtin_on(data, cfg, n)
                acts.append((n, f"{'Disable' if on else 'Enable'} {n.upper()}"))
        acts.append(("add", "Add from share link (vless / vmess / trojan / ss / socks5 / http)"))
        if obs:
            acts.append(("del", "Remove an outbound"))
        acts.append(("back", "Back"))
        act = util.choose("Action", acts, "back")
        if act == "back":
            return False
        if act == "add":
            link = util.prompt("Share link")
            if not link:
                continue
            ob, _name = proxylinks.parse(link)
            tag = util.prompt("Tag (used in rules and templates)", _next_tag(cfg, ob["protocol"]))
            if add_custom_outbound(data, cfg, link, tag):
                return True
            continue
        if act == "del":
            tag = util.choose("Remove which", [(o["tag"], _outbound_label(data, o))
                                               for o in obs if o.get("tag")]
                              + [("back", "Back")], "back")
            if tag != "back" and remove_outbound(data, cfg, tag):
                return True
            continue
        if set_builtin(data, cfg, act, not st.builtin_on(data, cfg, act)):
            return True


def _target_options(data: dict, cfg: dict) -> list[tuple[str, str]]:
    opts = [(o["tag"], _outbound_label(data, o)) for o in xc.outbounds(cfg) if o.get("tag")]
    for n in ("warp", "tor"):
        if not xc.find_outbound(cfg, st.builtin_tag(n)):
            opts.append((n, f"{n.upper()} (xvei sets it up)"))
    return opts


def print_rules(cfg: dict) -> None:
    rules = xc.rules_view(cfg)
    if not rules:
        _none()
    arrow = util.paint(util.SYM["arrow"], util.CYAN)
    marks = routing.template_marks(rules)
    for i, r in enumerate(rules, 1):
        what, target = xc.rule_parts(r)
        note = ""
        if i - 1 in marks:
            note = f"template {marks[i - 1]}"
        elif i == len(rules) and routing.is_exit(r):
            note = "everything else"
        print(f"    {util.paint(f'{i:>2})', util.CYAN)} {what}  {arrow} "
              f"{util.paint(target, util.BOLD)}" + (util.paint(f"   ({note})", util.DIM) if note else ""))


def menu_rules(data: dict, cfg: dict) -> bool:
    while True:
        util.header("Routing rules")
        print(util.paint("  Checked top to bottom, the first matching rule wins. With no "
                         "match: the first outbound.", util.DIM))
        print_rules(cfg)
        print()
        acts = [("add", "Send domains / IPs to an outbound"),
                ("remove", "Stop sending a domain / IP to an outbound"),
                ("delete", "Delete a rule"),
                ("back", "Back")]
        act = util.choose("Action", acts, "back")
        if act == "back":
            return False
        if act == "delete":
            raw = util.prompt("Rule number (empty = back)")
            if raw.isdigit() and rule_delete(cfg, int(raw)):
                return True
            continue
        if act == "add":
            target = util.choose("Outbound", _target_options(data, cfg) + [("back", "Back")], "back")
            if target == "back":
                continue
            val = util.prompt("Matcher (e.g. geosite:openai, domain:example.com, geoip:de, 1.2.3.0/24)")
            if val and rule_add(data, cfg, target, [val]):
                return True
            continue
        pool = [(o["tag"], o["tag"]) for o in xc.outbounds(cfg)
                if o.get("tag") and routing.matchers_for(cfg, o["tag"])]
        if not pool:
            util.warn("no plain domain / IP rules to take matchers from")
            continue
        target = util.choose("Outbound", pool + [("back", "Back")], "back")
        if target == "back":
            continue
        val = util.choose("Matcher", [(m, m) for m in routing.matchers_for(cfg, target)]
                          + [("back", "Back")], "back")
        if val != "back" and rule_remove(data, cfg, target, [val]):
            return True


def _tunnel_options(data: dict, cfg: dict) -> list[tuple[str, str]]:
    names = {"warp": "WARP (Cloudflare)", "tor": "TOR"}
    opts = []
    for n in tunnel_names(data, cfg):
        o = xc.find_outbound(cfg, n)
        opts.append((n, names.get(n) or (_outbound_label(data, o) if o else n)))
    return opts


def menu_template(data: dict, cfg: dict) -> bool:
    util.header("Routing template")
    now = routing.detect(cfg)
    print(util.paint(f"  Now: {now['template']}"
                     + (f", in-country -> {now['country_exit']}" if now["country_exit"] else "")
                     + f", everything else -> {now['exit'] or 'default route (first outbound)'}",
                     util.DIM))
    template = util.choose("Template", [
        ("russia", "Russia (geoip:ru + category-ru -> tunnel/block, never direct)"),
        ("iran", "Iran (geoip:ir + category-ir -> tunnel/block, never direct)"),
        ("china", "China (geoip:cn + geosite:cn -> tunnel/block, never direct)"),
        ("popular", "Popular direct (YouTube/Instagram/... direct, rest via a tunnel)"),
        ("none", "None"),
        ("back", "Back"),
    ], "back")
    if template == "back":
        return False
    tunnels = _tunnel_options(data, cfg)
    default_tunnel = now["exit"] if now["exit"] in dict(tunnels) else (tunnels[0][0] if tunnels else "")

    if template == "popular":
        tunnel = util.choose("Tunnel for everything outside the popular list", tunnels,
                             default_tunnel)
        return set_template(data, cfg, template, tunnel=tunnel)

    country_exit = None
    if template in st.COUNTRY_TEMPLATES:
        cur = now["country_exit"] if now["country_exit"] in dict(tunnels) else "block"
        country_exit = util.choose("In-country traffic exits via",
                                   tunnels + [("block", "Block outright")], cur)
    mode = util.choose("Everything else", [
        ("keep", f"Keep as is (now: {now['exit'] or 'default route'})"),
        ("direct", "Direct"),
        ("tunnel", "Through a tunnel (WARP / TOR / an outbound)"),
    ], "keep")
    tunnel = None
    if mode == "tunnel":
        tunnel = util.choose("Tunnel", tunnels, default_tunnel)
    return set_template(data, cfg, template, country_exit=country_exit, mode=mode, tunnel=tunnel)
