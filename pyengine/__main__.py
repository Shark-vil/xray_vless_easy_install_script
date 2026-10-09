"""xvei config engine — `python3 pyengine <subcommand> ...`.

Exit codes for mutating subcommands:
  0  state changed (caller should re-apply)
  2  no change
  1  error
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

import editor
import hy2conf
import turnconf
import json5lite
import links
import proxylinks
import sites
import state as st
import util
import xrayconf

XRAY_CONFIG_DEFAULT = "/usr/local/etc/xray/config.json"
HY2_CONFIG_DEFAULT = "/etc/hysteria/config.yaml"


def _load() -> dict:
    return st.load()


def _finish(changed: bool, data: dict) -> int:
    if changed:
        st.save(data)
        return 0
    util.log("no change")
    return 2


def cmd_init(_a) -> int:
    p = st.state_path()
    if os.path.exists(p):
        util.log(f"state already at {p}")
        return 2
    st.save(st.blank_state())
    util.ok(f"initialized {p}")
    return 0


def cmd_build(a) -> int:
    data = _load()
    cfg = xrayconf.build(data)
    util.write_json(a.xray_out, cfg, mode=0o600)
    util.ok(f"wrote {a.xray_out}")
    hy2 = hy2conf.build(data)
    if hy2 is not None:
        util.atomic_write(a.hy2_out, hy2, mode=0o600)
        util.ok(f"wrote {a.hy2_out}")
    tcfg = turnconf.build(data)
    if tcfg is not None and a.turnable_out:
        util.atomic_write(a.turnable_out, tcfg, mode=0o600)
        util.ok(f"wrote {a.turnable_out}")
    return 0


def cmd_turnable_info(a) -> int:
    """Print requested fields of the turnable inbound, space separated."""
    ib = st.get_type(_load(), "turnable")
    if not ib:
        return 1
    print(" ".join(str(ib.get(f, "")) for f in a.fields))
    return 0


def cmd_turnable_keys(a) -> int:
    data = _load()
    ib = st.get_type(data, "turnable")
    if not ib:
        util.die("no turnable inbound")
    ib["priv_key"], ib["pub_key"] = a.priv, a.pub
    st.save(data)
    return 0


def _inbound_or_die(data: dict, tag: str) -> dict:
    ib = st.inbound_by_tag(data, tag)
    if not ib:
        util.die(f"no inbound with tag {tag!r} (see: xvei links)")
    return ib


def cmd_link(a) -> int:
    """Print one share link of an inbound (for the QR code). An inbound with
    several clients asks which one, unless --client picks it (name or number)."""
    found = links.inbound_links(_load(), a.tag)
    if found is None:
        util.die(f"no inbound with tag {a.tag!r} (see: xvei links)")
    if not found:
        util.die(f"{a.tag}: no share link")
    pick = a.client
    if pick is None and len(found) > 1:
        pick = util.choose("Which client", [(str(i), name or f"#{i}")
                                            for i, (name, _l) in enumerate(found, 1)], "1")
    if pick is None:
        print(found[0][1])
        return 0
    for i, (name, link) in enumerate(found, 1):
        if pick in (str(i), name):
            print(link)
            return 0
    util.die(f"{a.tag}: no client {pick!r}")


def cmd_client_config(a) -> int:
    """Print the full Xray client config of one inbound (with routing rules)."""
    data = _load()
    ib = _inbound_or_die(data, a.tag)
    if ib["type"] == "hysteria2":
        util.die("hysteria2 has no Xray client config; use its share link")
    print(json.dumps(links.full_config(data, ib), indent=2))
    return 0


def cmd_show_links(a) -> int:
    links.print_links(_load(), a.tag)
    return 0


def cmd_state_get(a) -> int:
    data = _load()
    cur = data
    for part in a.key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return 1
    if isinstance(cur, (dict, list)):
        print(json.dumps(cur))
    elif cur is None:
        print("")
    else:
        print(cur)
    return 0


def cmd_needs(_a) -> int:
    print(" ".join(st.needs(_load())))
    return 0


def cmd_set_meta(a) -> int:
    data = _load()
    before = json.dumps(data, sort_keys=True)
    if a.domain is not None:
        data["domain"] = a.domain or None
    if a.email is not None:
        data["email"] = a.email
    if a.server_ip is not None:
        data["server_ip"] = a.server_ip
    if a.cert_mode is not None:
        data["cert"]["mode"] = a.cert_mode
    if a.cert_fullchain is not None:
        data["cert"]["fullchain"] = a.cert_fullchain
    if a.cert_privkey is not None:
        data["cert"]["privkey"] = a.cert_privkey
    if a.applied_sha is not None:
        data["applied_sha256"] = a.applied_sha
    return _finish(json.dumps(data, sort_keys=True) != before, data)


def cmd_add_inbound(a) -> int:
    data = _load()
    opts = {k: v for k, v in vars(a).items()
            if k in ("port", "dest", "method", "tag", "up_mbps", "down_mbps") and v is not None}
    return _finish(editor.add_inbound(data, a.type, **opts), data)


def cmd_remove_inbound(a) -> int:
    data = _load()
    if not st.inbound_by_tag(data, a.tag) and a.tag in st.base_tags(data):
        return _finish(editor.remove_base_inbound(data, a.tag), data)
    return _finish(editor.remove_inbound(data, a.tag), data)


def cmd_add_outbound(a) -> int:
    data = _load()
    if a.tag and len(a.items) > 1:
        util.die("--tag can only be used with a single link")
    changed = False
    for item in a.items:
        if "://" in item:
            changed |= editor.add_custom_outbound(data, item, a.tag)
        elif item in ("warp", "tor"):
            changed |= editor.set_outbound(data, item, True)
        else:
            util.die(f"{item!r} is neither warp, tor nor a share link")
    return _finish(changed, data)


def cmd_remove_outbound(a) -> int:
    data = _load()
    if a.name in ("warp", "tor"):
        return _finish(editor.set_outbound(data, a.name, False), data)
    if not st.custom_outbound(data, a.name) and a.name in st.base_tags(data):
        return _finish(editor.remove_base_outbound(data, a.name), data)
    return _finish(editor.remove_custom_outbound(data, a.name), data)


def cmd_rule(a) -> int:
    data = _load()
    if a.op == "delete":
        if not (a.bucket or "").isdigit():
            util.die("usage: rule delete <N>  (N from: rule list)")
        return _finish(editor.remove_base_rule(data, int(a.bucket)), data)
    if a.op == "list" and not a.bucket:
        for b in st.rule_buckets(data):
            if data["rules"].get(b):
                print(f"[{b}] {', '.join(data['rules'][b])}")
        for i, r in enumerate(st.base_rules(data), 1):
            print(f"{i:>2}) {st.describe_raw_rule(r)}")
        return 0
    if not a.bucket:
        util.die(f"rule {a.op} needs an outbound: {'|'.join(st.rule_buckets(data))}")
    changed = editor.rule_op(data, a.op, a.bucket, a.match)
    return _finish(changed, data)


def cmd_template(a) -> int:
    data = _load()
    if a.tunnel and not a.direct:
        mode = "tunnel"
    elif a.keep:
        mode = "keep"
    elif a.direct:
        mode = "direct"
    else:  # adopted: leave the current exit mode; otherwise direct as before
        mode = None if data.get("adopted") else "direct"
    if a.template in st.COUNTRY_TEMPLATES:
        changed = editor.set_template(data, a.template, country_exit=a.exit,
                                       mode=mode, tunnel=a.tunnel)
    elif a.template == "popular":
        changed = editor.set_template(data, a.template, tunnel=a.tunnel)
    else:
        changed = editor.set_template(data, a.template, mode=mode, tunnel=a.tunnel)
    return _finish(changed, data)


def cmd_menu(a) -> int:
    data = _load()
    fn = {
        "inbounds": editor.menu_inbounds,
        "outbounds": editor.menu_outbounds,
        "rules": editor.menu_rules,
        "template": editor.menu_template,
        "site": editor.menu_site,
    }[a.section]
    return _finish(fn(data), data)


def cmd_site(a) -> int:
    data = _load()
    if a.kind == "list":
        cur = (data.get("site") or {}).get("type", "auth")
        print(f"current: {cur}")
        print("  auth   - basic-auth prompt to nowhere (default)")
        print("  blank  - bare 'It works' page")
        print("  404    - plain 404")
        for n, t in sites.STATIC_PRESETS.items():
            print(f"  {n:<8} - static: {t}")
        print("  proxy <url|preset>  - reverse-proxy an upstream")
        for n, u in sites.PROXY_PRESETS.items():
            print(f"      preset {n}: {u}")
        return 2
    return _finish(editor.set_site(data, a.kind, a.url), data)


def cmd_nginx_conf(_a) -> int:
    print(sites.nginx_vhost(_load()), end="")
    return 0


def cmd_site_assets(_a) -> int:
    """Print the source dir of the active static preset, or empty."""
    kind = (_load().get("site") or {}).get("type", "auth")
    print(sites.preset_dir(kind) if sites.is_static(kind) else "")
    return 0


def cmd_list_inbounds(_a) -> int:
    data = _load()
    for ib in data["inbounds"]:
        print(f"{ib['tag']}\t{ib['type']}\t{ib.get('port', '')}")
    for ib in st.base_inbounds(data):
        if ib.get("tag"):
            print(f"{ib['tag']}\t{ib.get('protocol', '')}\t{ib.get('port', '')}")
    return 0


def cmd_adopt(a) -> int:
    """Take over an existing Xray config without changing anything: it becomes
    the "base" that every later build merges xvei's own parts into."""
    path = st.state_path()
    if os.path.exists(path):
        util.die(f"xvei state already exists ({path})")
    try:
        with open(a.config, "rb") as fh:
            raw = fh.read()
        base = json5lite.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError) as e:
        util.die(f"cannot read {a.config}: {e}")
    except json5lite.Json5Error as e:
        util.die(f"{a.config}: {e}")
    if not isinstance(base, dict):
        util.die(f"{a.config}: top level is not an object")
    data = st.blank_state()
    data["adopted"] = True
    data["base"] = base
    data["routing"]["mode"] = "keep"
    data["applied_sha256"] = hashlib.sha256(raw).hexdigest()
    # reuse an existing Let's Encrypt certificate for TLS inbounds added later
    for ib in base.get("inbounds") or []:
        tls = ((ib.get("streamSettings") or {}).get("tlsSettings") or {})
        for c in tls.get("certificates") or []:
            m = re.match(r"/etc/letsencrypt/live/([^/]+)/", str(c.get("certificateFile", "")))
            if m and not data["domain"]:
                data["domain"] = m.group(1)
                data["cert"] = {"mode": "letsencrypt",
                                "fullchain": f"/etc/letsencrypt/live/{m.group(1)}/fullchain.pem",
                                "privkey": f"/etc/letsencrypt/live/{m.group(1)}/privkey.pem"}
    st.save(data)
    util.ok(f"adopted {a.config} ({len(base.get('inbounds') or [])} inbounds, "
            f"{len(base.get('outbounds') or [])} outbounds, "
            f"{len((base.get('routing') or {}).get('rules') or [])} routing rules)")
    return 0


def cmd_pretty(a) -> int:
    try:
        with open(a.file, encoding="utf-8") as fh:
            text = fh.read()
        print(json5lite.pretty(text, color=a.color), end="")
    except OSError as e:
        util.die(f"cannot read {a.file}: {e}")
    except json5lite.Json5Error as e:
        util.die(f"{a.file}: {e}")
    return 0


def cmd_ports(_a) -> int:
    for p in st.public_ports(_load()):
        print(p)
    return 0


def cmd_summary(_a) -> int:
    data = _load()
    r = data["routing"]
    if data.get("adopted"):
        base = data.get("base") or {}
        print("mode        : adopted existing Xray config (kept as is, xvei parts merged in)")
        print("existing    :")
        for ib in base.get("inbounds") or []:
            print(f"  - inbound  {st.describe_raw_inbound(ib)}")
        for o in base.get("outbounds") or []:
            print(f"  - outbound {o.get('tag') or '(no tag)'} ({o.get('protocol', '?')})")
        print(f"  - {len((base.get('routing') or {}).get('rules') or [])} routing rules")
    print(f"domain      : {data.get('domain') or '(none)'}")
    print(f"cert        : {data['cert']['mode']}")
    detail = f"exit={r.get('mode')}" + (f" via {r.get('tunnel')}" if r.get('tunnel') else "")
    if r.get("country_exit"):
        detail = f"in-country -> {r.get('country_exit')}, rest {detail}"
    print(f"template    : {r.get('template')} / {detail}")
    print(f"outbounds   : warp={data['outbounds']['warp']} tor={data['outbounds']['tor']}")
    for c in data["custom_outbounds"]:
        name = f"  ({c['name']})" if c.get("name") else ""
        print(f"  - {c['tag']}: {proxylinks.describe(c['outbound'])}{name}")
    print("inbounds    :" + ("" if data["inbounds"] else " (none added by xvei)"))
    for ib in data["inbounds"]:
        print(f"  - {ib['tag']} ({ib['type']})")
    return 0


def cmd_wizard(a) -> int:
    data = _load()
    util.log("== xvei install wizard ==")
    types = [
        ("vless-tls", "VLESS TLS (Vision)"),
        ("vless-ws", "VLESS WebSocket"),
        ("vless-xhttp-reality", "VLESS XHTTP + REALITY"),
        ("vless-xhttp-tls", "VLESS XHTTP + TLS cert"),
        ("trojan-tcp", "Trojan (TCP, shares :443, legacy clients only)"),
        ("trojan-ws", "Trojan WebSocket (legacy clients only)"),
        ("vmess-ws", "VMess WebSocket (legacy clients only)"),
        ("shadowsocks", "Shadowsocks"),
        ("hysteria2", "Hysteria2"),
        ("turnable", "Turnable via VK calls (UNSTABLE, NOT anonymous: VK sees the server IP)"),
    ]
    chosen: list[str] = []
    for val, label in types:
        if util.confirm(f"Enable {label}?", default_yes=(val == "vless-tls")):
            chosen.append(val)
    if not chosen:
        util.die("nothing selected")
    tls_family = set(st.TLS_TYPES)
    need_domain = bool(tls_family & set(chosen)) or "hysteria2" in chosen
    rides_443 = set(st.FALLBACK_TYPES) | {"vless-xhttp-tls"}
    if rides_443 & set(chosen) and "vless-tls" not in chosen:
        util.log("vless-tls auto-enabled (required for the chosen fallback inbounds)")
        chosen.insert(0, "vless-tls")
    if need_domain:
        data["domain"] = util.prompt("Your real domain (A record -> this server)")
        data["email"] = util.prompt("Email for Let's Encrypt")
        data["cert"]["mode"] = "letsencrypt"
        data["cert"]["fullchain"] = f"/etc/letsencrypt/live/{data['domain']}/fullchain.pem"
        data["cert"]["privkey"] = f"/etc/letsencrypt/live/{data['domain']}/privkey.pem"

    for itype in chosen:
        editor.add_inbound(data, itype)

    if tls_family & set(chosen):
        if util.confirm("Configure the camouflage site (what a browser sees on the domain)?",
                        default_yes=False):
            editor.menu_site(data)

    editor.menu_template(data)
    st.save(data)
    util.ok("wizard complete; state saved")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pyengine")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init").set_defaults(fn=cmd_init)

    b = sub.add_parser("build")
    b.add_argument("--xray-out", default=XRAY_CONFIG_DEFAULT)
    b.add_argument("--hy2-out", default=HY2_CONFIG_DEFAULT)
    b.add_argument("--turnable-out", default=None)
    b.set_defaults(fn=cmd_build)

    lk = sub.add_parser("link")
    lk.add_argument("tag")
    lk.add_argument("--client", default=None)
    lk.set_defaults(fn=cmd_link)

    cc = sub.add_parser("client-config")
    cc.add_argument("tag")
    cc.set_defaults(fn=cmd_client_config)

    sl = sub.add_parser("show-links")
    sl.add_argument("--tag", default=None)
    sl.set_defaults(fn=cmd_show_links)

    sg = sub.add_parser("state-get")
    sg.add_argument("key")
    sg.set_defaults(fn=cmd_state_get)

    sub.add_parser("needs").set_defaults(fn=cmd_needs)
    sub.add_parser("list-inbounds").set_defaults(fn=cmd_list_inbounds)
    sub.add_parser("summary").set_defaults(fn=cmd_summary)
    sub.add_parser("ports").set_defaults(fn=cmd_ports)

    ti = sub.add_parser("turnable-info")
    ti.add_argument("fields", nargs="+")
    ti.set_defaults(fn=cmd_turnable_info)

    tk = sub.add_parser("turnable-keys")
    tk.add_argument("--priv", required=True)
    tk.add_argument("--pub", required=True)
    tk.set_defaults(fn=cmd_turnable_keys)

    ad = sub.add_parser("adopt")
    ad.add_argument("--config", default=XRAY_CONFIG_DEFAULT)
    ad.set_defaults(fn=cmd_adopt)

    pp = sub.add_parser("pretty")
    pp.add_argument("file", nargs="?", default=XRAY_CONFIG_DEFAULT)
    pp.add_argument("--color", action="store_true")
    pp.set_defaults(fn=cmd_pretty)
    sub.add_parser("wizard").set_defaults(fn=cmd_wizard)

    sm = sub.add_parser("set-meta")
    for opt in ("domain", "email", "server-ip", "cert-mode", "cert-fullchain", "cert-privkey",
                "applied-sha"):
        sm.add_argument("--" + opt, dest=opt.replace("-", "_"), default=None)
    sm.set_defaults(fn=cmd_set_meta)

    ai = sub.add_parser("add-inbound")
    ai.add_argument("type", choices=st.INBOUND_TYPES)
    ai.add_argument("--port", type=int)
    ai.add_argument("--dest")
    ai.add_argument("--method")
    ai.add_argument("--tag")
    ai.add_argument("--up-mbps", dest="up_mbps", type=int)
    ai.add_argument("--down-mbps", dest="down_mbps", type=int)
    ai.set_defaults(fn=cmd_add_inbound)

    ri = sub.add_parser("remove-inbound")
    ri.add_argument("tag")
    ri.set_defaults(fn=cmd_remove_inbound)

    ao = sub.add_parser("add-outbound")
    ao.add_argument("items", nargs="+", metavar="warp|tor|LINK",
                    help="warp, tor, or share links (vless vmess trojan ss socks5 http)")
    ao.add_argument("--tag", default=None, help="tag for a single added link")
    ao.set_defaults(fn=cmd_add_outbound)

    ro = sub.add_parser("remove-outbound")
    ro.add_argument("name", metavar="warp|tor|TAG")
    ro.set_defaults(fn=cmd_remove_outbound)

    ru = sub.add_parser("rule")
    ru.add_argument("op", choices=["add", "remove", "list", "delete"])
    ru.add_argument("bucket", nargs="?", metavar="block|direct|warp|tor|TAG|N")
    ru.add_argument("match", nargs="*")
    ru.set_defaults(fn=cmd_rule)

    tp = sub.add_parser("template")
    tp.add_argument("template", choices=list(st.TEMPLATES))
    tp.add_argument("--exit", default=None, metavar="warp|tor|block|TAG",
                    help="exit for in-country traffic (russia|iran|china templates only, "
                         "required -- never direct)")
    tp.add_argument("--tunnel", default=None, metavar="warp|tor|TAG",
                    help="tunnel for the rest of the traffic; required for 'popular'")
    tp.add_argument("--direct", action="store_true",
                    help="send the rest of the traffic direct (russia|iran|china|none only)")
    tp.add_argument("--keep", action="store_true",
                    help="adopted setups: no catch-all, the existing default stays")
    tp.set_defaults(fn=cmd_template)

    mn = sub.add_parser("menu")
    mn.add_argument("section",
                    choices=["inbounds", "outbounds", "rules", "template", "site"])
    mn.set_defaults(fn=cmd_menu)

    stp = sub.add_parser("site")
    stp.add_argument("kind", nargs="?", default="list",
                     help="auth|blank|404|proxy|<preset>|list")
    stp.add_argument("url", nargs="?", default=None, help="upstream for 'proxy'")
    stp.set_defaults(fn=cmd_site)

    sub.add_parser("nginx-conf").set_defaults(fn=cmd_nginx_conf)
    sub.add_parser("site-assets").set_defaults(fn=cmd_site_assets)

    return p


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 1
    except KeyboardInterrupt:
        util.err("interrupted")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
