# XVEI — Xray (+ Hysteria2) easy install & live editor

## [Документация на русском](/docs/RU.md)

Run everything as **root**.

XVEI installs and configures [Xray-core](https://github.com/XTLS/Xray-install)
(and optionally [Hysteria2](https://v2.hysteria.network/)) and then lets you
reshape the configuration **without reinstalling** — add/remove inbounds,
add/remove WARP/TOR, edit routing rules, switch the country template, swap the
camouflage site. Every change is validated and applied automatically.

All configuration lives in one state file
(`/usr/local/etc/xray/xvei-state.json`); a small Python engine (standard library
only, no `pip` packages) regenerates `config.json`, validates it with
`xray -test`, and only then swaps it in and restarts the services.

## What it can do

### Inbounds
| type | notes |
|---|---|
| `vless-tls` | VLESS + TCP + TLS + `xtls-rprx-vision`, on `:443`, nginx fallback |
| `vless-ws` | VLESS + WebSocket, rides the `:443` fallback (needs `vless-tls`) |
| `vless-xhttp-reality` | VLESS + XHTTP + **REALITY** — site masquerade, **no domain/cert required** |
| `vless-xhttp-tls` | VLESS + XHTTP + TLS certificate (shares `:443` or standalone) |
| `shadowsocks` | Shadowsocks 2022 / legacy ciphers |
| `hysteria2` | Hysteria2 on `:443/udp`; **all its traffic is forwarded into a local SOCKS5 inbound of Xray**, so Xray does the routing |

### Outbounds / tunnels
`direct`, `block`, and optionally **WARP** (Cloudflare, docker) or **TOR** as a
second hop that hides the server IP.

### Routing templates
Pick at install time (changeable later with `xvei template`):

* **Country template** — `russia` / `iran` / `china` / `none`.
  In-country destinations (`geoip:<cc>` + local `geosite` categories) always go
  **direct**; everything else follows the exit mode.
* **Exit mode**
  * `--direct` — everything except the in-country list goes straight out;
  * `--tunnel warp|tor` — everything except the in-country list goes through the tunnel.

### Editable rule buckets
`block`, `direct`, `warp`, `tor` — add/remove matchers
(`geosite:…`, `geoip:…`, `domain:…`, `1.2.3.0/24`, `regexp:…`) live.

### Camouflage site
What a normal browser sees when it opens the domain directly (the nginx
fallback for `vless-tls` / `vless-xhttp-tls`). Change any time with `xvei site`:

* `auth` — HTTP Basic auth prompt against an empty file, always 401 *(default, same as the old script)*
* `blank` / `404` — a bare page / plain 404
* static presets — self-contained pages with **no external requests** (safe, work offline):
  `nebula` (solar-system facts), `critters` (animal encyclopedia),
  `game2048`, `snake`, `notes` (a personal blog)
* `proxy <url|preset>` — reverse-proxy a real upstream. Most sites break when
  proxied (bot walls, host checks, absolute redirects), so a few known-proxyable
  ones are presets: `example`, `rfc`, `cern`, `gnu`, `iana`.

## Install

```bash
apt-get update && apt-get -y install curl
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

The first run downloads the script tree to `/usr/local/lib/xvei` and symlinks
`xvei` into `/usr/local/bin`, so afterwards just run `xvei`.

## Usage

```
xvei                     interactive menu (or offer to install)
xvei install             guided first-time setup
xvei edit                interactive menu
xvei apply               regenerate + validate + restart from the current state

xvei add-inbound  <type> [--port N] [--dest SNI] [--method M]
xvei remove-inbound <tag>
xvei add-outbound   <warp|tor>
xvei remove-outbound <warp|tor>
xvei rule <add|remove|list> <block|warp|tor|direct> [matcher ...]
xvei template <russia|iran|china|none> [--tunnel <warp|tor> | --direct]
xvei site [list | auth | blank | 404 | <preset> | proxy <url|preset>]

xvei links [tag]         print client share links
xvei qr <tag>            QR code for one inbound
xvei status              services + active template
xvei set-meta [--domain D --email E ...]
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
xvei template russia --tunnel warp        # RU direct, rest via WARP
xvei remove-inbound hy2                    # stops & removes Hysteria2, keeps the rest
xvei site game2048                         # serve a 2048 game on the domain
xvei site proxy gnu                        # reverse-proxy www.gnu.org
```

Every command that changes the state re-runs generate → `xray -test` → swap →
restart automatically. If validation fails, the live config is left untouched.

A certbot deploy hook (`/etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh`)
is installed with the certificate: after every Let's Encrypt renewal it refreshes
the Hysteria2 cert copy and restarts `xray`, `nginx` and `hysteria2`.

## Files

| path | contents |
|---|---|
| `/usr/local/etc/xray/xvei-state.json` | source of truth (root, `0600`) |
| `/usr/local/etc/xray/config.json` | generated Xray config (`.bak` kept) |
| `/etc/hysteria/config.yaml` | generated Hysteria2 config (+ `cert.crt`/`cert.key`) |
| `/etc/nginx/sites-enabled/xvei.conf`, `/var/www/xvei-site` | fallback vhost + camouflage site |
| `~/xray_eis/<tag>.link` | client share link per inbound |
| `~/xray_eis/<tag>.json` | full Xray client config per inbound (not for `hysteria2`) |

## Repository layout

```
xvei.sh            entry point + bootstrap + subcommand dispatch
lib/*.sh           system side: package install, xray, nginx, certs, hysteria2, warp, tor, apply, menu
pyengine/*.py      config engine (stdlib only): state, inbounds, outbounds, routing, sites, links, editor
assets/sites/*     self-contained camouflage sites (no external requests)
```

## Clients

[v2rayNG](https://github.com/2dust/v2rayNG/releases/latest),
[NekoBox / nekoray](https://github.com/MatsuriDayo/nekoray/releases/latest),
[Hiddify](https://hiddify.com/). REALITY and XHTTP need a reasonably recent
client build; the `hysteria2` inbound needs a Hysteria2-capable client
(Hiddify, NekoBox, the official `hysteria` client).

`xvei links` prints the share URIs; `xvei qr <tag>` shows a scannable code.
Apps that cannot import a `vless://` / `ss://` link can load the full config
from `~/xray_eis/<tag>.json`.
