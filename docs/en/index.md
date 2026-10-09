# XVEI

**A simple Xray server setup manager.**

[🇷🇺 Русская версия](../ru/index.md) · [GitHub](https://github.com/Shark-vil/xray_vless_easy_install_script)

XVEI installs [Xray-core](https://github.com/XTLS/Xray-core) on a Linux server
(optionally with [Hysteria2](https://v2.hysteria.network/)) and stays on as an
editor: inbounds, tunnels, routing and the camouflage site are changed with one
command or from a menu, without reinstalling. Every change is checked with
`xray -test` before it goes live; if the check fails, the running config is not
touched.

## What it does

- **Inbounds** — VLESS (REALITY, Vision, XHTTP, WebSocket), Trojan, VMess,
  Shadowsocks, Hysteria2 and the experimental Turnable. Several of them share
  port 443. See [inbounds](inbounds.md).
- **Second hop** — Cloudflare WARP, TOR, or any server of your own added from a
  share link (`vless://`, `vmess://`, `trojan://`, `ss://`, `socks5://`,
  `http://`). See [routing](routing.md).
- **Routing** — country templates that never send in-country traffic from the
  server's own IP, a "popular sites direct" template, and editable rule lists.
- **Camouflage site** — what a browser sees on your domain: a login prompt, a
  static site, or a reverse proxy. See [camouflage site](site.md).
- **Client links** — share links, QR codes and full client configs for every
  inbound.
- **Existing servers** — an Xray that is already configured is taken over as
  is, without changing anything. See
  [installation](install.md#server-with-xray-already-installed).
- **Maintenance** — update checks, optional firewall setup, automatic
  certificate renewal. See [maintenance](maintenance.md).

## Quick start

Supported systems: Ubuntu 20.04+, Debian 11+, CentOS Stream 9. Run as **root**.

Ubuntu / Debian:

```bash
apt-get update && apt-get -y install curl
```

CentOS:

```bash
dnf -y install curl tar
```

Install and run the setup wizard:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

The wizard is explained step by step in [getting started](getting-started.md).

## Where to go next

| I want to… | page |
|---|---|
| install for the first time and connect a phone | [Getting started](getting-started.md) |
| choose which protocol to use | [Inbounds](inbounds.md) |
| route some sites through another server | [Outbounds and routing](routing.md) |
| look up a command | [Commands](commands.md) |
| understand what happens on the server | [How it works](architecture.md) |
| fix something that does not work | [Troubleshooting](troubleshooting.md) |
| pick a client app | [Clients](clients.md) |
