# Commands &nbsp;·&nbsp; [🇷🇺 RU](../ru/commands.md)

[← README](../../README.md)

The script is called as `xvei`:

```
xvei                     interactive menu (or offer to install)
xvei install             guided first-time setup
xvei edit                interactive menu
xvei apply               regenerate + validate + restart from the current state

xvei add-inbound  <type> [--port N] [--dest SNI] [--method M]
xvei remove-inbound <tag>
xvei add-outbound   <warp|tor|LINK ...> [--tag T]
xvei remove-outbound <warp|tor|TAG>
xvei rule <add|remove|list> <block|direct|warp|tor|TAG> [matcher ...]
xvei template <russia|iran|china> --exit <warp|tor|block|TAG> [--tunnel <warp|tor|TAG> | --direct]
xvei template popular --tunnel <warp|tor|TAG>
xvei template none [--tunnel <warp|tor|TAG> | --direct | --keep]
xvei site [list | auth | blank | 404 | <preset> | proxy <url|preset>]

xvei links [tag]         print client share links
xvei qr <tag>            QR code for one inbound
xvei status              services + active template
xvei show-config [file]  print config.json readably (JSON5, comments kept)
xvei firewall [status | open | setup]   see maintenance.md, "Firewall"
xvei set-meta [--domain D --email E ...]
xvei check-updates       check xvei / xray / hysteria2 / geo data for updates
xvei update-geo          refresh geoip/geosite (optional; the xray installer ships them)
xvei self-update         re-fetch the script tree
xvei remove              uninstall everything
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

All configuration lives in one state file
(`/usr/local/etc/xray/xvei-state.json`); a small Python engine (standard library
only, no `pip` packages) regenerates `config.json`, validates it with
`xray -test`, and only then swaps it in and restarts the services.

Every command that changes the state re-runs generate → `xray -test` → swap →
restart automatically. If validation fails, the live config is left untouched.
