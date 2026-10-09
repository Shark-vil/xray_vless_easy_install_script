# Commands

`xvei` without arguments opens the menu. Everything in the menu is also a
command.

## Setup

```
xvei install                    first-time setup wizard
xvei apply                      re-check certificate and services, restart
xvei set-meta --domain D --email E
```

## Inbounds and links

```
xvei add-inbound <type> [--port N] [--dest SITE] [--method CIPHER] [--tag T]
xvei remove-inbound <tag>
xvei links [tag]                all client links
xvei qr <tag> [client]          QR code (client: name or number)
xvei client-config <tag>        full Xray config for a client app
```

Types: `vless-tls`, `vless-ws`, `vless-xhttp-reality`, `vless-xhttp-tls`,
`trojan-tcp`, `trojan-ws`, `vmess-ws`, `shadowsocks`, `hysteria2`, `turnable` —
see [inbounds](inbounds.md).

## Outbounds and routing

```
xvei add-outbound warp | tor | 'LINK' [--tag T]
xvei remove-outbound <warp|tor|tag>
xvei rule add|remove <outbound> <matcher ...>
xvei rule list [outbound]       all rules, numbered
xvei rule delete <N>
xvei template russia|iran|china --exit <outbound> [--direct | --tunnel <outbound>]
xvei template popular --tunnel <outbound>
xvei template none [--direct | --tunnel <outbound>]
xvei site [auth | blank | 404 | <preset> | proxy <url>]
```

See [routing](routing.md) and [camouflage site](site.md).

## Maintenance

```
xvei status                     summary and services
xvei show-config                config.json, readable
xvei backup [list [page]]       backups, 10 per page
xvei backup create [note]       back up now
xvei backup show|diff <N>       view a backup / compare with the current config
xvei backup restore <N>         roll back
xvei backup delete <N>
xvei backup keep [N]            how many to keep (default 20, 0 = off)
xvei firewall [status | open | setup]
xvei check-updates
xvei update-geo                 refresh the site and country lists
xvei self-update                update xvei only
xvei remove [--all [--packages]] [--yes]
```

See [maintenance](maintenance.md).

## Examples

```bash
xvei add-inbound vless-xhttp-reality --dest www.samsung.com
xvei add-outbound tor
xvei rule add tor geosite:openai
xvei template russia --exit warp --direct
xvei site game2048
xvei backup restore 1      # undo the last change
```
