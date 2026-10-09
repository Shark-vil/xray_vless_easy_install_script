# Commands

[🇷🇺 Русская версия](../ru/commands.md) · [← Home](index.md)

The script is called as `xvei`:

```
xvei                     interactive menu (or offer to install)
xvei install             guided first-time setup
xvei edit                interactive menu
xvei apply               re-check what the config needs (certificate, services) and restart

xvei add-inbound  <type> [--port N] [--dest SNI] [--method M]
xvei remove-inbound <tag>
xvei add-outbound   <warp|tor|LINK ...> [--tag T]
xvei remove-outbound <warp|tor|TAG>
xvei rule add|remove <OUTBOUND|warp|tor> <matcher ...>
                         send domains / IPs to an outbound (or stop)
xvei rule list [OUTBOUND] all rules, numbered (or what goes to one outbound)
xvei rule delete <N>     delete rule N
xvei template <russia|iran|china> --exit <warp|tor|block|TAG> [--tunnel <warp|tor|TAG> | --direct]
xvei template popular --tunnel <warp|tor|TAG>
xvei template none [--tunnel <warp|tor|TAG> | --direct | --keep]
xvei site [list | auth | blank | 404 | <preset> | proxy <url|preset>]

xvei links [tag]         print client share links
xvei qr <tag> [client]   QR code for one inbound (client: name or number)
xvei client-config <tag> full Xray client config (with routing rules)
xvei status              services + active template
xvei show-config [file]  print config.json readably (JSON5, comments kept)
xvei firewall [status | open | setup]   see maintenance.md, "Firewall"
xvei set-meta [--domain D --email E ...]
xvei check-updates       check xvei / xray / hysteria2 / geo data for updates
xvei update-geo          refresh geoip/geosite (optional; the xray installer ships them)
xvei self-update         re-fetch the script tree
xvei remove [--all [--packages]] [--yes]
                         uninstall only xvei; --all: with everything it set up; asks first
```

Examples:

```bash
xvei add-inbound vless-xhttp-reality --dest www.samsung.com
xvei add-outbound tor
xvei rule add tor geosite:openai
xvei rule add block geosite:category-ads-all
xvei template russia --exit warp --direct  # RU traffic via WARP, rest direct
xvei template popular --tunnel tor         # popular sites direct, rest via TOR
xvei remove-inbound hy2                    # stops & removes Hysteria2, keeps the rest
xvei site game2048                         # serve a 2048 game on the domain
xvei site proxy gnu                        # reverse-proxy www.gnu.org
```

## How changes are applied

`/usr/local/etc/xray/config.json` is the source of truth and is read on every
run - edits made in it by hand show up at once. A command that changes
something works on a copy of it; a small Python engine (standard library only,
no `pip` packages) writes the copy, `xray -test` checks it, and only then it is
swapped in and the services restarted. If the check fails, the live config is
left untouched. `xvei-state.json` next to it keeps only what `config.json`
cannot hold (domain, certificate, site, Hysteria2 / Turnable settings).
