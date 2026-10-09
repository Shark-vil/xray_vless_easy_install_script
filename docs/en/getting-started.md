# Getting started

[🇷🇺 Русская версия](../ru/getting-started.md) · [← Home](index.md)

This page walks through a first installation: from an empty VPS to a phone
that is connected.

## Before you start

You need:

- a VPS with Ubuntu 20.04+, Debian 11+ or CentOS Stream 9, root access and a
  public IPv4 address;
- free ports: `443/tcp` for most inbounds, `80/tcp` while a Let's Encrypt
  certificate is issued or renewed, plus the ports of the inbounds you choose;
- **a domain only if you need one.** `vless-xhttp-reality`, `shadowsocks`,
  `hysteria2` and `turnable` work without it. `vless-tls`, `vless-ws`,
  `vless-xhttp-tls`, `trojan-*` and `vmess-ws` need a domain whose A record
  points to the server's IP — create the record before installing and wait
  until it resolves.

> [!NOTE]
> Many cloud providers (AWS, Oracle Cloud, Google Cloud, …) have their own
> firewall in the control panel ("security group", "security list"). xvei
> cannot open ports there — open them in the panel yourself.

Not sure which inbounds to pick? Start with `vless-xhttp-reality`: it needs no
domain and is one of the recommended options in 2026. More in
[inbounds](inbounds.md#which-inbound-to-choose-2026).

## 1. Install curl

Ubuntu / Debian:

```bash
apt-get update && apt-get -y install curl
```

CentOS:

```bash
dnf -y install curl tar
```

## 2. Run the installer

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

The installer checks the system, installs the dependencies and Xray, and then
starts the wizard.

> [!TIP]
> If Xray is already configured on this server, nothing is installed or
> changed: the existing setup is taken over as is. See
> [installation](install.md#server-with-xray-already-installed).

## 3. Answer the wizard

The wizard asks questions in this order. Press Enter to accept the value in
brackets.

1. **Which inbounds to enable** — one yes/no question per type. Only
   `vless-tls` is suggested by default. Inbounds that live behind port 443
   (`vless-ws`, `trojan-*`, `vmess-ws`, `vless-xhttp-tls`) automatically
   enable `vless-tls`.
2. **Domain and e-mail** — asked when a chosen inbound needs a certificate (or
   for `hysteria2`). The e-mail is only given to Let's Encrypt.
3. **Settings of each inbound**:
   - `vless-xhttp-reality` — port (443 if free, otherwise 8443) and the site
     to imitate (default `www.microsoft.com`);
   - `shadowsocks` — port and cipher;
   - `hysteria2` — UDP port;
   - `turnable` — UDP port and a VK call link (read the
     [warnings](turnable.md) first).
4. **Camouflage site** — what a browser sees on your domain. You can skip it
   and change it later with `xvei site`.
5. **Routing template** — how traffic leaves the server. If unsure, pick
   `none` with "Everything direct"; the templates are explained in
   [routing](routing.md#routing-templates).

After the last answer xvei requests the certificate (if needed), writes the
configs, validates them, starts the services and prints the client links.

## 4. Connect a client

The links are printed at the end of the installation. Print them again any
time:

```bash
xvei links
```

Show a QR code for one inbound (the tag is shown in the list, e.g.
`vless_reality`):

```bash
xvei qr vless_reality
```

Import the link or scan the QR code in a client app such as v2rayNG, NekoBox
or Hiddify — see [clients](clients.md). The full Xray client config (with the
template's routing rules) is printed by `xvei client-config <tag>`.

## 5. Change things later

Open the menu:

```bash
xvei
```

Everything from the wizard can be changed there: add or remove inbounds, turn
on WARP or TOR, add rules, switch the template, change the site. Each change
is validated and applied immediately. The same is available as commands — see
[commands](commands.md).

## Example: no domain, one inbound

Answer **yes** only to "VLESS XHTTP + REALITY", accept the default port and
site, skip everything else and choose the `none` template with "Everything
direct". The result is one inbound on port 443 that needs no domain and no
certificate.
