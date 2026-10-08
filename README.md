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
| `trojan-tcp` | Trojan + TCP, shares `:443` with `vless-tls`: anything that is not VLESS goes to Trojan, anything that is not Trojan goes to the camouflage site. The client must use ALPN `http/1.1` (set in the generated link) |
| `trojan-ws` | Trojan + WebSocket through the `:443` fallback (needs `vless-tls`) |
| `vmess-ws` | VMess (AEAD) + WebSocket through the `:443` fallback (needs `vless-tls`); the server clock must be accurate to ±120 s |
| `shadowsocks` | Shadowsocks 2022 / legacy ciphers |
| `hysteria2` | Hysteria2 on `:443/udp`; **all its traffic is forwarded into a local SOCKS5 inbound of Xray**, so Xray does the routing |

### Which inbound to choose (2026)

| inbound | status | why |
|---|---|---|
| `vless-xhttp-reality` | ✅ recommended | No domain or certificate; the TLS handshake is a real one borrowed from a large site, and XHTTP traffic looks like ordinary HTTP requests |
| `vless-tls` (Vision) | ✅ recommended | Real domain and certificate, a working site on the same address; Vision removes the TLS-inside-TLS pattern |
| `vless-xhttp-tls` | ✅ recommended | Like `vless-tls`, HTTP-shaped traffic; can also run behind a CDN |
| `vless-ws` | 🟡 situational | Needed mainly for CDNs that only pass WebSocket; the WebSocket upgrade is a well-known pattern, XHTTP is preferred |
| `hysteria2` | 🟡 situational | Fast on lossy links; UDP/QUIC is throttled or dropped entirely on some networks |
| `trojan-tcp`, `trojan-ws` | 🟠 legacy | Xray itself marks Trojan as deprecated (startup notice) and recommends VLESS; no Vision, so the TLS-inside-TLS pattern remains; keep for clients that only speak Trojan |
| `vmess-ws` | 🟠 legacy | Deprecated in Xray (startup notice), no forward secrecy, depends on the clock; keep for old clients only |
| `shadowsocks` (2022 / AEAD) | 🔴 weak on filtered networks | Fully random-looking traffic is recognised by its byte statistics alone (documented since 2021); fine on unfiltered networks |

Status reflects Xray's own deprecation notices and public measurements as of
2026; the situation differs between countries and providers. A practical
setup: `vless-xhttp-reality` plus `vless-tls`, with `hysteria2` as a fast
extra where UDP works.

### Outbounds / tunnels
`direct`, `block`, optionally **WARP** (Cloudflare, docker) or **TOR** as a
second hop that hides the server IP, and **your own outbounds from share
links**:

* `vless://` — transports tcp / ws / grpc / xhttp / httpupgrade, security none / tls / reality;
* `vmess://` — v2rayN base64 JSON or URL form, same transports and security;
* `trojan://` — same transports and security, `tls` by default;
* `ss://` — SIP002 (base64 or plain `method:password`) and the legacy all-base64 form;
  AEAD and 2022 ciphers (`aes-128-gcm`, `aes-256-gcm`, `chacha20-ietf-poly1305`,
  `xchacha20-ietf-poly1305`, `2022-blake3-*`);
* `socks://`, `socks5://` — with or without `user:pass` (also v2rayN base64 form);
* `http://`, `https://` — with or without `user:pass`.

Not supported: `hysteria2://`; links with `allowInsecure=1` (current Xray
removed that option); Shadowsocks stream ciphers (`aes-256-cfb` etc.) and
plugins; legacy VMess with `alterId > 0`.

An added outbound gets a tag (`vless1`, `socks1`, … or `--tag`). The tag is
used as a rule bucket, as the template tunnel (`--tunnel <tag>`) and as the
in-country exit of a country template (`--exit <tag>`). The `#name` part of a
link is shown as a label only.

Add an outbound (single quotes are required: the link contains `&`):

```bash
xvei add-outbound 'vless://UUID@example.com:443?security=reality&sni=example.com&pbk=KEY&sid=ID&type=tcp&flow=xtls-rprx-vision' --tag fi
```

Add several at once:

```bash
xvei add-outbound 'socks5://user:pass@203.0.113.30:1080' 'http://user:pass@203.0.113.40:8080'
```

Send OpenAI traffic through it:

```bash
xvei rule add fi geosite:openai
```

Send everything through it:

```bash
xvei template none --tunnel fi
```

Remove it:

```bash
xvei remove-outbound fi
```

An outbound used as the template tunnel or exit cannot be removed until the
template is switched. Menu: `xvei` → `2) Outbounds` → `Add from share link`.

### Routing templates
Pick at install time (changeable later with `xvei template`). These are
**server-side** rules — what leaves the VPS on its own real IP, not what the
client device does.

* **Country template** — `russia` / `iran` / `china` / `none`.
  In-country destinations (`geoip:<cc>` + local `geosite` categories)
  **never** go direct from the server — a VPS reaching straight into RU/IR/CN
  networks exposes its real IP to them and risks getting the server
  blacklisted. That traffic requires `--exit warp|tor|block|<tag>`:
  * `warp` / `tor` / an added outbound — leaves through a second hop, the server IP stays hidden;
  * `block` — dropped outright.
  Everything else (not in-country) follows the regular exit mode:
  * `--direct` — straight out;
  * `--tunnel warp|tor|<tag>` — through a tunnel.
* **"Popular direct" template** — `popular`.
  Global, non-country-specific services (`geosite:youtube`, `instagram`,
  `google`, `telegram`, `netflix`, `github`, etc. — tags present in
  essentially any geosite.dat build) go direct for speed; everything else
  requires `--tunnel warp|tor|<tag>`.

### Editable rule buckets
`block`, `direct`, `warp`, `tor` and one per added outbound (its tag) — add/remove matchers
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

## Supported systems

| system | status |
|---|---|
| Ubuntu 20.04 / 22.04 / 24.04 | ✅ supported |
| Debian 11 / 12 / 13 | ✅ supported |
| CentOS Stream 9 | ✅ supported |
| AlmaLinux / Rocky / RHEL 9, CentOS Stream 10, Fedora | ❓ unknown — not tested, probably works |
| CentOS 7, CentOS Stream 8, other EL8 | ❌ not supported (EOL, Python 3.6) |
| Alpine, systems without systemd | ❌ not supported |

On any other system the installer warns and asks before continuing.

Requirements: root, systemd, Python ≥ 3.7 (installed automatically if
missing). Everything else (xray, certbot, nginx, hysteria2, docker for WARP,
tor) is installed on demand.

On CentOS the installer additionally:
* enables **EPEL** (certbot, tor and qrencode only live there);
* writes the nginx vhost to `/etc/nginx/conf.d/` instead of `sites-enabled/`;
* with SELinux enforcing, labels nginx's local ports 8080/8081 as
  `http_port_t` and turns on `httpd_can_network_connect` for the
  reverse-proxy camouflage site;
* enables `certbot-renew.timer` (shipped disabled there).

## Install

Requires `curl`.

Ubuntu / Debian:

```bash
apt-get update && apt-get -y install curl
```

CentOS:

```bash
dnf -y install curl tar
```

### Full install

Downloads the script and runs the setup wizard: Xray plus everything selected
in it (certificate, nginx, Hysteria2, WARP, TOR).

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

### Script only

Downloads the script to `/usr/local/lib/xvei` and creates the `xvei` command.
Components (Xray, certificate, nginx, etc.) are not installed.

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) help
```

Run the setup wizard:

```bash
xvei install
```

### From a git clone

```bash
git clone https://github.com/Shark-vil/xray_vless_easy_install_script.git
cd xray_vless_easy_install_script
bash xvei.sh install
```

The `xvei` command points to the clone folder. Update with `git pull`;
`xvei self-update` is not available in this mode.

### Server with Xray already installed

If Xray is installed and `/usr/local/etc/xray/config.json` exists but xvei has
never been set up, `xvei install` **adopts** the existing setup: nothing is
installed (except Python, if missing), rewritten or restarted. The config is
read as JSON5 (comments, trailing commas) and stored as the base of the xvei
state.

Afterwards xvei edits are merged into that config:

* existing inbounds, outbounds, rules and all other sections (`log`, `dns`,
  `api`, `stats`, `policy`, …) stay unchanged;
* the first existing outbound stays first and remains the default route;
* xvei rules and templates go before the existing rules;
* no catch-all rule is added unless an exit mode is chosen explicitly
  (`xvei template none --keep` returns to the existing default);
* tor, the WARP container, Hysteria2 and nginx are stopped or reconfigured
  only if xvei set them up itself.

Before the first write the original is saved as `config.json.xvei-orig`
(comments included; the rebuilt file has none). If `config.json` is edited by
hand after xvei wrote it, xvei asks before overwriting it. `xvei remove`
removes only what xvei added and offers to restore the original.

Not adopted (nothing is changed, the reason is printed): Xray run by a panel
(x-ui / 3x-ui), `xray.service` reading a config from another path or using
`-confdir`.

### How the one-liner works

`bash <(curl …)` downloads only `xvei.sh`. The script downloads the full
repository to `/usr/local/lib/xvei`, creates the symlink
`/usr/local/bin/xvei` → `/usr/local/lib/xvei/xvei.sh` and re-runs itself with
the same argument. Without an argument it opens the menu, which offers to
install.

`xvei.sh` is the repository file, `xvei` is the installed command:
`xvei install` is the same as `bash /usr/local/lib/xvei/xvei.sh install`.

## Usage

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
xvei firewall [status | open | setup]   see "Firewall" below
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

Every command that changes the state re-runs generate → `xray -test` → swap →
restart automatically. If validation fails, the live config is left untouched.

A certbot deploy hook (`/etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh`)
is installed with the certificate: after every Let's Encrypt renewal it refreshes
the Hysteria2 cert copy and restarts `xray`, `nginx` and `hysteria2`. Pre/post
hooks (`renewal-hooks/{pre,post}/xvei-free-port80.sh`) stop nginx for the
renewal challenge only if it holds `:80`, then start it again.

## Updates

`xvei check-updates` (menu: `10) Check for updates`) prints the installed and
latest version of each component and offers to install the available updates:

| component | installed | compared with |
|---|---|---|
| xvei | installed commit | latest commit of `master` |
| xray | `xray version` | latest [XTLS/Xray-core](https://github.com/XTLS/Xray-core/releases) release |
| hysteria2 | `hysteria version` | latest [apernet/hysteria](https://github.com/apernet/hysteria/releases) release |
| geoip.dat / geosite.dat | file sha256 | checksums of the latest [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat/releases) release |

Components that are not installed are skipped. xvei is updated last; run
`xvei` again afterwards. In a git clone xvei is updated with `git pull`.

## Firewall

xvei **never enables, resets or tightens a firewall by itself** — a wrong
default-deny can cut you off from SSH (especially if sshd runs on a
non-standard port).

* If **ufw** or **firewalld** is already active and blocks ports the current
  config needs (inbound ports, plus `80/tcp` for Let's Encrypt), every apply
  lists them and asks whether to open them. This only *adds* allow rules.
  Without a terminal it just prints a warning.
* `xvei firewall status` — which firewall is active, the detected SSH port(s),
  and which needed ports are open or closed.
* `xvei firewall open` — add allow rules for the needed ports (active firewall only).
* `xvei firewall setup` — **opt-in** lockdown: deny all incoming except SSH +
  xvei ports. The SSH port is detected from `sshd -T`, from what sshd listens
  on, and from the current SSH session. The full plan is shown first, you can
  add extra ports (e.g. `2222/tcp 27015/udp`), and nothing happens without an
  explicit "yes". Uses ufw on Debian/Ubuntu (existing rules are kept unless
  you choose `ufw reset`), firewalld on CentOS.

The same actions are in the menu: `xvei` → `9) Firewall`.

## Files

| path | contents |
|---|---|
| `/usr/local/etc/xray/xvei-state.json` | source of truth (root, `0600`) |
| `/usr/local/etc/xray/config.json` | generated Xray config (`.bak` kept) |
| `/usr/local/etc/xray/config.json.xvei-orig` | adopted setups: the config as it was before xvei |
| `/etc/hysteria/config.yaml` | generated Hysteria2 config (+ `cert.crt`/`cert.key`) |
| `/etc/nginx/sites-enabled/xvei.conf` (Debian/Ubuntu) or `/etc/nginx/conf.d/xvei.conf` (CentOS), `/var/www/xvei-site` | fallback vhost + camouflage site |
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
