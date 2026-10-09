# XVEI

**A simple Xray server setup manager.**

XVEI installs [Xray](https://github.com/XTLS/Xray-core) on a Linux server and
then lets you change its setup from a menu or with short commands: add or
remove connection types, route sites through other servers, change what a
browser sees on your domain. Every change is checked before it goes live, and
a backup is made first.

## What it can do

- **Connection types (inbounds)** — VLESS (REALITY, Vision, XHTTP, WebSocket),
  Trojan, VMess, Shadowsocks, Hysteria2. Several of them can share port 443.
  [Inbounds](inbounds.md)
- **Second hop** — send all or some traffic through Cloudflare WARP, TOR, or
  another server added from a share link. [Routing](routing.md)
- **Country templates** — sites of your own country are never opened from the
  server's IP, which keeps the server from being blocked.
  [Routing](routing.md#templates)
- **Client links** — links, QR codes and full client configs.
  [Clients](clients.md)
- **Existing servers** — an Xray that is already set up is taken over as is;
  edits made by hand in its config are kept.
  [Installation](install.md#server-with-xray-already-installed)
- **Backups and rollback**, update checks, optional firewall setup.
  [Maintenance](maintenance.md)

## Install

Ubuntu 20.04+, Debian 11+ or CentOS Stream 9, as **root**:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

If `curl` is missing: `apt-get update && apt-get -y install curl` (Ubuntu /
Debian) or `dnf -y install curl tar` (CentOS). Step by step:
[getting started](getting-started.md).

## Where to go next

| I want to… | page |
|---|---|
| install and connect a phone | [Getting started](getting-started.md) |
| choose a protocol | [Inbounds](inbounds.md) |
| send some sites through another server | [Routing](routing.md) |
| look up a command | [Commands](commands.md) |
| roll back a change, update, uninstall | [Maintenance](maintenance.md) |
| fix something | [Troubleshooting](troubleshooting.md) |
