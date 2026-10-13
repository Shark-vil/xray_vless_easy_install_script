"""xvei config engine — `python3 pyengine <subcommand> ...`.

config.json is the source of truth and is read fresh by every subcommand.
Mutating subcommands write the changed config to a staging file (see
xrayconf.pending_path) that lib/apply.sh validates and swaps in.

Exit codes for mutating subcommands:
  0  something changed (caller should apply)
  2  no change
  1  error
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

import backups
import editor
import hy2conf
import turnconf
import json5lite
import links
import routing
import sites
import state as st
import util
import xrayconf as xc

HY2_CONFIG_DEFAULT = "/etc/hysteria/config.yaml"

# what the automatic backup before a change is labelled with (set in main)
_REASON = ""


def _load() -> dict:
    return st.load()


def _cfg(*, pending: bool = False) -> dict:
    return xc.load(pending=pending)


def _finish(changed: bool, data: dict, cfg: dict | None = None, *,
            backup: bool = True) -> int:
    """Back up what is on disk now, save the state, stage the changed
    config; 0 if anything changed."""
    if changed:
        if backup:
            backups.create(_REASON)
        st.save(data)
        if cfg is not None:
            xc.save_pending(cfg)
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
    """Render the Hysteria2 / Turnable configs for the config being applied."""
    data, cfg = _load(), _cfg(pending=True)
    hy2 = hy2conf.build(data, cfg)
    if hy2 is not None:
        util.atomic_write(a.hy2_out, hy2, mode=0o640)
        util.ok(f"wrote {a.hy2_out}")
    tcfg = turnconf.build(data, cfg)
    if tcfg is not None and a.turnable_out:
        util.atomic_write(a.turnable_out, tcfg, mode=0o600)
        util.ok(f"wrote {a.turnable_out}")
    return 0


def cmd_sync_cert(_a) -> int:
    """After the certificate was issued / replaced: point xvei's inbounds at it."""
    data, cfg = _load(), _cfg(pending=True)
    if editor.sync_cert(data, cfg):
        xc.save_pending(cfg)
        util.log("certificate paths updated in config.json")
        return 0
    return 2


def cmd_turnable_info(a) -> int:
    """Print requested fields of xvei's Turnable, space separated."""
    data = _load()
    rec = st.service(data, _cfg(pending=True), "turnable")
    if not rec:
        return 1
    print(" ".join(str(rec.get(f, "")) for f in a.fields))
    return 0


def cmd_turnable_keys(a) -> int:
    data = _load()
    if not data.get("turnable"):
        util.die("no turnable inbound")
    data["turnable"]["priv_key"], data["turnable"]["pub_key"] = a.priv, a.pub
    st.save(data)
    return 0


def _print_link(tag: str, name: str, link: str, labelled: bool) -> int:
    sep = f" {util.SYM['sep']} "
    print(f"{tag}{sep + name if name else ''}\t{link}" if labelled else link)
    return 0


def cmd_link(a) -> int:
    """Print one share link of an inbound (for the QR code). An inbound with
    several clients asks which one, unless --client picks it (name or number).
    With --label: "<inbound · client>\\t<link>"."""
    found = links.inbound_links(_load(), _cfg(), a.tag)
    if found is None:
        util.die(f"no inbound with tag {a.tag!r} (see: xvei links)")
    if not found:
        util.die(f"{a.tag}: no share link")
    pick = a.client
    if pick is None and len(found) > 1:
        pick = util.choose("Which client", [(str(i), name or f"#{i}")
                                            for i, (name, _l) in enumerate(found, 1)]
                           + [("back", "Back")], "back")
        if pick == "back":
            return 2
    if pick is None:
        return _print_link(a.tag, "", found[0][1], a.label)
    for i, (name, link) in enumerate(found, 1):
        if pick in (str(i), name):
            return _print_link(a.tag, name if len(found) > 1 else "", link, a.label)
    util.die(f"{a.tag}: no client {pick!r}")


def cmd_qr_pick(_a) -> int:
    """Menu "Links / QR codes": pick an inbound, then a client; prints
    "<inbound · client>\\t<link>", or exits 2 on Back."""
    data, cfg = _load(), _cfg()
    rows = [(ib["tag"], xc.inbound_detail(ib)) for ib in xc.inbounds(cfg)
            if ib.get("tag") and links.inbound_links(data, cfg, ib["tag"])]
    if not rows:
        util.warn("no inbound has a share link")
        return 2
    w = max(len(t) for t, _ in rows)
    opts = [(t, f"{t:<{w}}  {util.paint(d, util.DIM, stream=sys.stderr)}") for t, d in rows]
    tag = util.choose("QR code for which inbound", opts + [("back", "Back")], "back")
    if tag == "back":
        return 2
    return cmd_link(argparse.Namespace(tag=tag, client=None, label=True))


def cmd_client_config(a) -> int:
    data, cfg = _load(), _cfg()
    found = links.inbound_links(data, cfg, a.tag)
    if found is None:
        util.die(f"no inbound with tag {a.tag!r} (see: xvei links)")
    usable = [(n, l) for n, l in found if not l.startswith(("hysteria2://", "turnable://",
                                                            "https://t.me/"))]
    if not usable:
        util.die(f"{a.tag}: no Xray client config (use its share link)")
    name, link = usable[0]
    if a.client:
        match = [(n, l) for i, (n, l) in enumerate(usable, 1) if a.client in (str(i), n)]
        if not match:
            util.die(f"{a.tag}: no client {a.client!r}")
        name, link = match[0]
    print(json.dumps(links.full_config(cfg, link), indent=2))
    return 0


def cmd_show_links(a) -> int:
    links.print_links(_load(), _cfg(), a.tag)
    return 0


def cmd_state_get(a) -> int:
    cur = _load()
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
    print(" ".join(st.needs(_load(), _cfg(pending=True))))
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
    # the server IP is refreshed on every apply: no backup for that alone
    only_ip = all(getattr(a, k) is None for k in (
        "domain", "email", "cert_mode", "cert_fullchain", "cert_privkey"))
    return _finish(json.dumps(data, sort_keys=True) != before, data, backup=not only_ip)


def cmd_add_inbound(a) -> int:
    data, cfg = _load(), _cfg()
    opts = {k: v for k, v in vars(a).items()
            if k in ("port", "dest", "method", "tag", "up_mbps", "down_mbps") and v is not None}
    return _finish(editor.add_inbound(data, cfg, a.type, **opts), data, cfg)


def cmd_remove_inbound(a) -> int:
    data, cfg = _load(), _cfg()
    return _finish(editor.remove_inbound(data, cfg, a.tag), data, cfg)


def cmd_add_outbound(a) -> int:
    data, cfg = _load(), _cfg()
    if a.tag and len(a.items) > 1:
        util.die("--tag can only be used with a single link")
    changed = False
    for item in a.items:
        if item in ("warp", "tor"):
            changed |= editor.set_builtin(data, cfg, item, True)
        else:
            changed |= editor.add_custom_outbound(data, cfg, item, a.tag)
    return _finish(changed, data, cfg)


def cmd_remove_outbound(a) -> int:
    data, cfg = _load(), _cfg()
    if a.name in ("warp", "tor"):
        return _finish(editor.set_builtin(data, cfg, a.name, False), data, cfg)
    return _finish(editor.remove_outbound(data, cfg, a.name), data, cfg)


def cmd_rule(a) -> int:
    data, cfg = _load(), _cfg()
    if a.op == "delete":
        if not (a.target or "").isdigit():
            util.die("usage: rule delete <N>  (N from: rule list)")
        return _finish(editor.rule_delete(cfg, int(a.target)), data, cfg)
    if a.op == "list":
        if a.target:
            tag = st.builtin_tag(a.target) if a.target in ("warp", "tor") else a.target
            for m in routing.matchers_for(cfg, tag):
                print(m)
        else:
            for i, r in enumerate(xc.rules_view(cfg), 1):
                print(f"{i:>2}) {xc.describe_rule(r)}")
        return 0
    if not a.target:
        util.die(f"rule {a.op} needs an outbound (see: xvei rule list)")
    if a.op == "add":
        return _finish(editor.rule_add(data, cfg, a.target, a.match), data, cfg)
    return _finish(editor.rule_remove(data, cfg, a.target, a.match), data, cfg)


def cmd_template(a) -> int:
    data, cfg = _load(), _cfg()
    if a.tunnel and not a.direct:
        mode = "tunnel"
    elif a.direct:
        mode = "direct"
    else:
        mode = "keep"
    changed = editor.set_template(data, cfg, a.template, country_exit=a.exit,
                                  mode=mode, tunnel=a.tunnel)
    return _finish(changed, data, cfg)


def cmd_menu(a) -> int:
    data, cfg = _load(), _cfg()
    fn = {
        "inbounds": editor.menu_inbounds,
        "outbounds": editor.menu_outbounds,
        "rules": editor.menu_rules,
        "template": editor.menu_template,
        "site": editor.menu_site,
    }.get(a.section)
    if fn is None:  # backups: restoring stages the config itself
        return 0 if backups.menu(data) else 2
    return _finish(fn(data, cfg), data, cfg)


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
    # the site lives in nginx, config.json stays as it is
    return _finish(editor.set_site(data, _cfg(), a.kind, a.url), data)


def cmd_backup_create(a) -> int:
    bid = backups.create("manual" + (f": {' '.join(a.note)}" if a.note else ""), force=True)
    if bid:
        util.ok(f"backup {bid} created in {backups.backup_dir()}")
    return 0


def cmd_backup_list(a) -> int:
    pages = backups.print_page(a.page - 1)
    if pages > 1:
        print(util.paint(f"\n  more: xvei backup list <page 1..{pages}>", util.DIM))
    return 0


def cmd_backup_show(a) -> int:
    backups.pager(backups.show_text(backups.resolve(a.ref)))
    return 0


def cmd_backup_diff(a) -> int:
    backups.pager(backups.diff_text(backups.resolve(a.ref)))
    return 0


def cmd_backup_restore(a) -> int:
    bid = backups.resolve(a.ref)
    if not a.yes and not util.confirm(
            f"Restore config.json and the xvei state from {bid}? "
            "The current ones are backed up first", default_yes=False):
        return 2
    backups.restore(bid)
    return 0


def cmd_backup_delete(a) -> int:
    backups.delete(backups.resolve(a.ref))
    return 0


def cmd_backup_keep(a) -> int:
    if a.n is None:
        print(backups.keep_limit(_load()))
        return 0
    if a.n < 0:
        util.die("the number of backups to keep must be 0 or more")
    backups.set_keep(a.n)
    return 0


def cmd_nginx_conf(_a) -> int:
    print(sites.nginx_vhost(_load()), end="")
    return 0


def cmd_site_assets(_a) -> int:
    """Print the source dir of the active static preset, or empty."""
    kind = (_load().get("site") or {}).get("type", "auth")
    print(sites.preset_dir(kind) if sites.is_static(kind) else "")
    return 0


def cmd_list_inbounds(_a) -> int:
    for ib in xc.inbounds(_cfg()):
        if ib.get("tag"):
            print(f"{ib['tag']}\t{ib.get('protocol', '')}\t{ib.get('port', '')}")
    return 0


def cmd_adopt(a) -> int:
    """Start using xvei on an Xray config it did not create. Nothing in the
    config changes; xvei only notes the domain / certificate it uses."""
    path = st.state_path()
    if os.path.exists(path):
        util.die(f"xvei state already exists ({path})")
    cfg = xc.load()
    data = st.blank_state()
    data["adopted"] = True
    # reuse an existing Let's Encrypt certificate for TLS inbounds added later
    for ib in xc.inbounds(cfg):
        tls = ((ib.get("streamSettings") or {}).get("tlsSettings") or {})
        for c in tls.get("certificates") or []:
            m = re.match(r"/etc/letsencrypt/live/([^/]+)/", str(c.get("certificateFile", "")))
            if m and not data["domain"]:
                data["domain"] = m.group(1)
                data["cert"] = {"mode": "letsencrypt",
                                "fullchain": f"/etc/letsencrypt/live/{m.group(1)}/fullchain.pem",
                                "privkey": f"/etc/letsencrypt/live/{m.group(1)}/privkey.pem"}
    st.save(data)
    util.ok(f"now managing {xc.config_path()} ({len(xc.inbounds(cfg))} inbounds, "
            f"{len(xc.outbounds(cfg))} outbounds, {len(xc.rules_view(cfg))} routing rules)")
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
    for p in st.public_ports(_load(), _cfg(pending=True)):
        print(p)
    return 0


def cmd_summary(_a) -> int:
    data, cfg = _load(), _cfg()
    dim, bold = (lambda s: util.paint(s, util.DIM)), (lambda s: util.paint(s, util.BOLD))

    def kv(key: str, val: str) -> None:
        print(f"  {dim(f'{key:<12}')} {val}")

    def items(title: str, rows: list[tuple[str, str]]) -> None:
        print(util.paint(f"  {title}", util.BOLD, util.YELLOW))
        if not rows:
            print(dim("    (none)"))
        width = max((len(t) for t, _ in rows), default=0)
        for t, d in rows:
            print(f"    {util.SYM['bullet']} {bold(f'{t:<{width}}')}  {dim(d)}")

    util.header("Overview")
    kv("Config", xc.config_path())
    kv("Domain", data.get("domain") or dim("(none)"))
    kv("Certificate", data["cert"]["mode"])
    now = routing.detect(cfg)
    detail = f"everything else {util.SYM['arrow']} {now['exit'] or 'default route'}"
    if now["country_exit"]:
        detail = f"in-country {util.SYM['arrow']} {now['country_exit']}, {detail}"
    kv("Template", f"{now['template']} {util.SYM['sep']} {detail}")
    print()
    sep = f" {util.SYM['sep']} "
    items("Inbounds", [(ib.get("tag") or "(no tag)", xc.inbound_detail(ib)
                        + (f"{sep}xvei {st.owned_type(data, ib.get('tag', ''))}"
                           if st.owned_type(data, ib.get("tag", "")) else ""))
                       for ib in xc.inbounds(cfg)])
    items("Outbounds", [(o.get("tag") or "(no tag)", xc.outbound_detail(o)
                         + (f"{sep}default route" if i == 0 else ""))
                        for i, o in enumerate(xc.outbounds(cfg))])
    print(dim(f"  {len(xc.rules_view(cfg))} routing rules (menu: Routing rules)"))
    return 0


_WIZARD_TYPES = [
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


def cmd_wizard(a) -> int:
    data, cfg = _load(), _cfg()
    util.header("Install wizard")
    if not data.get("adopted") and not xc.outbounds(cfg) and not xc.inbounds(cfg):
        cfg = {**xc.skeleton(), **{k: v for k, v in cfg.items()
                                   if k not in ("inbounds", "outbounds", "routing")}}
    chosen: list[str] = []
    for val, label in _WIZARD_TYPES:
        if util.confirm(f"Enable {label}?", default_yes=(val == "vless-tls")):
            chosen.append(val)
    if not chosen:
        util.die("nothing selected")
    rides_443 = set(st.FALLBACK_TYPES) | {"vless-xhttp-tls"}
    if rides_443 & set(chosen) and "vless-tls" not in chosen and not xc.terminator(cfg):
        util.log("vless-tls auto-enabled (required for the chosen fallback inbounds)")
        chosen.insert(0, "vless-tls")
    if (set(st.TLS_TYPES) & set(chosen) or "hysteria2" in chosen) and not data.get("domain"):
        data["domain"] = util.prompt("Your real domain (A record -> this server)")
        data["email"] = util.prompt("Email for Let's Encrypt")
        data["cert"]["mode"] = "letsencrypt"
        data["cert"]["fullchain"] = f"/etc/letsencrypt/live/{data['domain']}/fullchain.pem"
        data["cert"]["privkey"] = f"/etc/letsencrypt/live/{data['domain']}/privkey.pem"

    for itype in chosen:
        editor.add_inbound(data, cfg, itype)

    if set(st.TLS_TYPES) & set(chosen):
        if util.confirm("Configure the camouflage site (what a browser sees on the domain)?",
                        default_yes=False):
            editor.menu_site(data, cfg)

    editor.menu_template(data, cfg)
    st.save(data)
    xc.save_pending(cfg)
    util.ok("wizard complete")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pyengine")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(fn=cmd_init)

    b = sub.add_parser("build")
    b.add_argument("--hy2-out", default=HY2_CONFIG_DEFAULT)
    b.add_argument("--turnable-out", default=None)
    b.set_defaults(fn=cmd_build)

    sub.add_parser("sync-cert").set_defaults(fn=cmd_sync_cert)

    lk = sub.add_parser("link")
    lk.add_argument("tag")
    lk.add_argument("--client", default=None)
    lk.add_argument("--label", action="store_true")
    lk.set_defaults(fn=cmd_link)

    sub.add_parser("qr-pick").set_defaults(fn=cmd_qr_pick)

    cc = sub.add_parser("client-config")
    cc.add_argument("tag")
    cc.add_argument("client", nargs="?", default=None)
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
    ad.set_defaults(fn=cmd_adopt)

    pp = sub.add_parser("pretty")
    pp.add_argument("file", nargs="?", default=xc.XRAY_CONFIG_DEFAULT)
    pp.add_argument("--color", action="store_true")
    pp.set_defaults(fn=cmd_pretty)
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
    ao.add_argument("items", nargs="+", metavar="warp|tor|LINK",
                    help="warp, tor, or share links (vless vmess trojan ss socks5 http)")
    ao.add_argument("--tag", default=None, help="tag for a single added link")
    ao.set_defaults(fn=cmd_add_outbound)

    ro = sub.add_parser("remove-outbound")
    ro.add_argument("name", metavar="warp|tor|TAG")
    ro.set_defaults(fn=cmd_remove_outbound)

    ru = sub.add_parser("rule")
    ru.add_argument("op", choices=["add", "remove", "list", "delete"])
    ru.add_argument("target", nargs="?", metavar="OUTBOUND|warp|tor|N")
    ru.add_argument("match", nargs="*")
    ru.set_defaults(fn=cmd_rule)

    tp = sub.add_parser("template")
    tp.add_argument("template", choices=list(st.TEMPLATES))
    tp.add_argument("--exit", default=None, metavar="warp|tor|block|TAG",
                    help="exit for in-country traffic (russia|iran|china templates only, "
                         "required -- never direct)")
    tp.add_argument("--tunnel", default=None, metavar="warp|tor|TAG",
                    help="send everything else through this tunnel; required for 'popular'")
    tp.add_argument("--direct", action="store_true",
                    help="send everything else direct")
    tp.add_argument("--keep", action="store_true",
                    help="leave the rule for everything else as it is (the default)")
    tp.set_defaults(fn=cmd_template)

    mn = sub.add_parser("menu")
    mn.add_argument("section",
                    choices=["inbounds", "outbounds", "rules", "template", "site", "backups"])
    mn.set_defaults(fn=cmd_menu)

    stp = sub.add_parser("site")
    stp.add_argument("kind", nargs="?", default="list",
                     help="auth|blank|404|proxy|<preset>|list")
    stp.add_argument("url", nargs="?", default=None, help="upstream for 'proxy'")
    stp.set_defaults(fn=cmd_site)

    bc = sub.add_parser("backup-create")
    bc.add_argument("note", nargs="*")
    bc.set_defaults(fn=cmd_backup_create)
    bl = sub.add_parser("backup-list")
    bl.add_argument("page", nargs="?", type=int, default=1)
    bl.set_defaults(fn=cmd_backup_list)
    for name, fn in (("backup-show", cmd_backup_show), ("backup-diff", cmd_backup_diff),
                     ("backup-delete", cmd_backup_delete)):
        x = sub.add_parser(name)
        x.add_argument("ref", help="number in the list (1 = newest) or backup id")
        x.set_defaults(fn=fn)
    br = sub.add_parser("backup-restore")
    br.add_argument("ref")
    br.add_argument("--yes", action="store_true")
    br.set_defaults(fn=cmd_backup_restore)
    bk = sub.add_parser("backup-keep")
    bk.add_argument("n", nargs="?", type=int, default=None)
    bk.set_defaults(fn=cmd_backup_keep)

    sub.add_parser("nginx-conf").set_defaults(fn=cmd_nginx_conf)
    sub.add_parser("site-assets").set_defaults(fn=cmd_site_assets)

    return p


def main(argv: list[str]) -> int:
    global _REASON
    # share links carry credentials: keep them out of backup labels
    _REASON = " ".join(a for a in argv if "://" not in a)[:80]
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
