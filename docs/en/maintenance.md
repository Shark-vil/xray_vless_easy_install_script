# Updates, firewall, files

[🇷🇺 Русская версия](../ru/maintenance.md) · [← Home](index.md)

## Updates

`xvei check-updates` (menu: `10) Check for updates`) prints the installed and
latest version of each component and offers to install the available updates:

| component | installed | compared with |
|---|---|---|
| xvei | installed commit | latest commit of `master` |
| xray | `xray version` | latest [XTLS/Xray-core](https://github.com/XTLS/Xray-core/releases) release |
| hysteria2 | `hysteria version` | latest [apernet/hysteria](https://github.com/apernet/hysteria/releases) release |
| geoip.dat / geosite.dat | file sha256 | checksums of the latest [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat/releases) release |

Components that are not installed are skipped. With several updates you can
install all of them (`all`, the default), none (`none`) or only some — list
names from the prompt, e.g. `geo` or `xray geo`. xvei is updated last; run
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

## Removing xvei (keeping Xray)

**Adopted setup** (Xray was there before xvei): `xvei remove` (menu:
`11) Uninstall xvei`) already keeps Xray. It removes only what xvei set up
itself (WARP, TOR, Hysteria2, Turnable, its nginx vhost, certbot hooks), asks
whether to restore `config.json.xvei-orig`, and deletes the xvei state. Xray,
its service and certificates stay. Then remove the command and code:

```bash
sed -i '/_renew-hook/d' /etc/letsencrypt/renewal/*.conf
rm -f /usr/local/bin/xvei
rm -rf /usr/local/lib/xvei      # or your git clone folder
```

**Regular install** (xvei installed Xray): `xvei remove` uninstalls Xray too.
To remove only xvei and leave everything running as it is now (Xray with the
current `config.json`, nginx, WARP, TOR, Hysteria2), delete xvei's files by
hand:

```bash
rm -f /usr/local/etc/xray/xvei-state.json /usr/local/etc/xray/xvei-state.json.bak
rm -rf /var/lib/xvei
rm -f /etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh
rm -f /etc/letsencrypt/renewal-hooks/{pre,post}/xvei-free-port80.sh
sed -i '/_renew-hook/d' /etc/letsencrypt/renewal/*.conf
rm -f /usr/local/bin/xvei
rm -rf /usr/local/lib/xvei      # or your git clone folder
rm -rf ~/xray_eis               # left by older xvei versions, if present
```

Without the certbot hooks, restart Xray yourself after a certificate renewal
(`systemctl restart xray`), or add your own deploy hook.

## Files

| path | contents |
|---|---|
| `/usr/local/etc/xray/xvei-state.json` | source of truth (root, `0600`) |
| `/usr/local/etc/xray/config.json` | generated Xray config (`.bak` kept) |
| `/usr/local/etc/xray/config.json.xvei-orig` | adopted setups: the config as it was before xvei |
| `/etc/hysteria/config.yaml` | generated Hysteria2 config (+ `cert.crt`/`cert.key`) |
| `/etc/nginx/sites-enabled/xvei.conf` (Debian/Ubuntu) or `/etc/nginx/conf.d/xvei.conf` (CentOS), `/var/www/xvei-site` | fallback vhost + camouflage site |
| `/etc/turnable/config.json`, `/usr/local/bin/turnable` | Turnable server config and binary |

## Repository layout

```
xvei.sh            entry point + bootstrap + subcommand dispatch
lib/*.sh           system side: package install, xray, nginx, certs, hysteria2, warp, tor, apply, menu
pyengine/*.py      config engine (stdlib only): state, inbounds, outbounds, routing, sites, links, editor
assets/sites/*     self-contained camouflage sites (no external requests)
```
