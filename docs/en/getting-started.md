# Getting started

From an empty server to a connected phone.

## What you need

- A VPS with Ubuntu 20.04+, Debian 11+ or CentOS Stream 9, root access and a
  public IPv4 address.
- Open ports: `443/tcp` for most connection types, `80/tcp` for the
  certificate, and the ports you choose in the wizard.
- **A domain — only for some types.** `vless-xhttp-reality`, `shadowsocks`,
  `hysteria2` and `turnable` work without one. The others need a domain whose
  A record points to the server's IP; set it up before installing.

!!! note
    Many cloud providers (AWS, Oracle, Google Cloud…) have their own firewall in
    the control panel. xvei cannot open ports there — do it in the panel.

Not sure what to choose? Take `vless-xhttp-reality`: no domain needed and it
works well today. [Compare the types](inbounds.md).

## 1. Install

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

If `curl` is missing, install it first: `apt-get update && apt-get -y install
curl` (Ubuntu / Debian) or `dnf -y install curl tar` (CentOS).

The installer sets up Xray and starts a short wizard. If Xray is already set up
on the server, it is taken over without changes —
[details](install.md#server-with-xray-already-installed).

## 2. Answer the wizard

Press Enter to accept the value in brackets.

1. **Connection types** — a yes/no question for each. Types that work behind
   port 443 (`vless-ws`, `trojan-*`, `vmess-ws`, `vless-xhttp-tls`) turn on
   `vless-tls` as well.
2. **Domain and e-mail** — only if a chosen type needs a certificate. The
   e-mail goes to Let's Encrypt only.
3. **Settings of the types** — ports, the site REALITY imitates
   (`www.microsoft.com` by default), the Shadowsocks cipher.
4. **Camouflage site** — what a browser sees on your domain. Can be skipped.
5. **Routing template** — if unsure, choose `None` and keep the rest as it
   is: all traffic goes out directly. [Templates](routing.md#templates)

xvei then gets the certificate, starts everything and prints the links.

## 3. Connect a client

Print the links again any time:

```bash
xvei links
```

Show a QR code (the tag is in the list, e.g. `vless_reality`):

```bash
xvei qr vless_reality
```

Import the link or scan the code in v2rayNG, NekoBox or Hiddify —
[clients](clients.md).

## 4. Change things later

```bash
xvei
```

The menu changes everything from the wizard and more. Each change is checked
and applied at once; the previous config is backed up. All of it is also
available as [commands](commands.md).
