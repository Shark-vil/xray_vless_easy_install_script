# Updates, firewall, files &nbsp;·&nbsp; [🇷🇺 RU](../ru/maintenance.md)

[← README](../../README.md)

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

## Certificate renewal

A certbot deploy hook (`/etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh`)
is installed with the certificate: after every Let's Encrypt renewal it refreshes
the Hysteria2 cert copy and restarts `xray`, `nginx` and `hysteria2`. Pre/post
hooks (`renewal-hooks/{pre,post}/xvei-free-port80.sh`) stop nginx for the
renewal challenge only if it holds `:80`, then start it again.

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
| `~/xray_eis/turnable.link`, `turnable.app.link` | `turnable://` link for the Turnable client and the `vless://` link for the proxy app |
| `/etc/turnable/config.json`, `/usr/local/bin/turnable` | Turnable server config and binary |

## Repository layout

```
xvei.sh            entry point + bootstrap + subcommand dispatch
lib/*.sh           system side: package install, xray, nginx, certs, hysteria2, warp, tor, apply, menu
pyengine/*.py      config engine (stdlib only): state, inbounds, outbounds, routing, sites, links, editor
assets/sites/*     self-contained camouflage sites (no external requests)
```
