"""xvei config engine — `python3 pyengine <subcommand> ...`.

Exit codes for mutating subcommands:
  0  state changed (caller should re-apply)
  2  no change
  1  error
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import editor
import hy2conf
import links
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
    return 0


def cmd_links(a) -> int:
    data = _load()
    for p in links.write_all(data, a.dir):
        util.log(p)
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
    return _finish(json.dumps(data, sort_keys=True) != before, data)


def cmd_add_inbound(a) -> int:
    data = _load()
    opts = {k: v for k, v in vars(a).items()
            if k in ("port", "dest", "method", "tag", "up_mbps", "down_mbps") and v is not None}
    return _finish(editor.add_inbound(data, a.type, **opts), data)


def cmd_remove_inbound(a) -> int:
    data = _load()
    return _finish(editor.remove_inbound(data, a.tag), data)


def cmd_add_outbound(a) -> int:
    data = _load()
    return _finish(editor.set_outbound(data, a.name, True), data)


def cmd_remove_outbound(a) -> int:
    data = _load()
    return _finish(editor.set_outbound(data, a.name, False), data)


def cmd_rule(a) -> int:
    data = _load()
    changed = editor.rule_op(data, a.op, a.bucket, a.match)
    return _finish(changed, data)


def cmd_template(a) -> int:
    data = _load()
    mode = "tunnel" if a.tunnel else "direct"
    if a.direct:
        mode = "direct"
    return _finish(editor.set_template(data, a.country, mode, a.tunnel), data)


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
    return 0


def cmd_summary(_a) -> int:
    data = _load()
    r = data["routing"]
    print(f"domain      : {data.get('domain') or '(none)'}")
    print(f"cert        : {data['cert']['mode']}")
    print(f"template    : {r.get('country')} / exit={r.get('mode')}"
          + (f" via {r.get('tunnel')}" if r.get('tunnel') else ""))
    print(f"outbounds   : warp={data['outbounds']['warp']} tor={data['outbounds']['tor']}")
    print("inbounds    :")
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
        ("shadowsocks", "Shadowsocks"),
        ("hysteria2", "Hysteria2"),
    ]
    chosen: list[str] = []
    for val, label in types:
        if util.confirm(f"Enable {label}?", default_yes=(val == "vless-tls")):
            chosen.append(val)
    if not chosen:
        util.die("nothing selected")
    tls_family = {"vless-tls", "vless-ws", "vless-xhttp-tls"}
    need_domain = bool(tls_family & set(chosen)) or "hysteria2" in chosen
    if ("vless-ws" in chosen or "vless-xhttp-tls" in chosen) and "vless-tls" not in chosen:
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

    country = util.choose("Country template", [
        ("russia", "Russia"), ("iran", "Iran"), ("china", "China"), ("none", "None"),
    ], "none")
    mode = util.choose("Exit mode", [
        ("direct", "Everything direct except in-country"),
        ("tunnel", "Everything through a tunnel"),
    ], "direct")
    tunnel = util.choose("Tunnel", [("warp", "WARP"), ("tor", "TOR")]) if mode == "tunnel" else None
    editor.set_template(data, country, mode, tunnel)
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
    b.set_defaults(fn=cmd_build)

    lk = sub.add_parser("links")
    lk.add_argument("--dir", default=None)
    lk.set_defaults(fn=cmd_links)

    sl = sub.add_parser("show-links")
    sl.add_argument("--tag", default=None)
    sl.set_defaults(fn=cmd_show_links)

    sg = sub.add_parser("state-get")
    sg.add_argument("key")
    sg.set_defaults(fn=cmd_state_get)

    sub.add_parser("needs").set_defaults(fn=cmd_needs)
    sub.add_parser("list-inbounds").set_defaults(fn=cmd_list_inbounds)
    sub.add_parser("summary").set_defaults(fn=cmd_summary)
    sub.add_parser("wizard").set_defaults(fn=cmd_wizard)

    sm = sub.add_parser("set-meta")
    for opt in ("domain", "email", "server-ip", "cert-mode", "cert-fullchain", "cert-privkey"):
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
    ao.add_argument("name", choices=["warp", "tor"])
    ao.set_defaults(fn=cmd_add_outbound)

    ro = sub.add_parser("remove-outbound")
    ro.add_argument("name", choices=["warp", "tor"])
    ro.set_defaults(fn=cmd_remove_outbound)

    ru = sub.add_parser("rule")
    ru.add_argument("op", choices=["add", "remove", "list"])
    ru.add_argument("bucket", choices=list(st.RULE_BUCKETS))
    ru.add_argument("match", nargs="*")
    ru.set_defaults(fn=cmd_rule)

    tp = sub.add_parser("template")
    tp.add_argument("country", choices=list(st.COUNTRIES))
    tp.add_argument("--tunnel", choices=["warp", "tor"], default=None)
    tp.add_argument("--direct", action="store_true")
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
