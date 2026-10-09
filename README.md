# XVEI — Xray (+ Hysteria2) easy install & live editor

## [Документация на русском](/docs/RU.md)

XVEI installs and configures [Xray-core](https://github.com/XTLS/Xray-install)
(and optionally [Hysteria2](https://v2.hysteria.network/)) and then lets you
reshape the configuration **without reinstalling** — inbounds, WARP / TOR and
your own outbounds, routing rules and templates, the camouflage site. Every
change is validated with `xray -test` before it is applied; a failed check
leaves the running config untouched. An Xray that is already set up on the
server is taken over as is.

Run everything as **root**. Supported: Ubuntu 20.04+, Debian 11+, CentOS
Stream 9 ([details](docs/en/install.md#supported-systems)).

## Install

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

Other ways (script only, git clone, a server with Xray already installed):
[installation](docs/en/install.md).

## Use

After installation the script is the `xvei` command. Open the menu:

```bash
xvei
```

Print the client links:

```bash
xvei links
```

All commands: [commands](docs/en/commands.md).

## Which inbound

Recommended in 2026: `vless-xhttp-reality` (no domain needed) and `vless-tls`
(own domain), with `hysteria2` as a fast extra where UDP works. All types and
their status: [inbounds](docs/en/inbounds.md).

## Documentation

| page | contents |
|---|---|
| [Installation](docs/en/install.md) | supported systems, install variants, taking over an existing Xray |
| [Inbounds](docs/en/inbounds.md) | all inbound types, which to choose in 2026 |
| [Turnable](docs/en/turnable.md) | ⚠️ VK-call tunnel: unstable, **reveals the server IP** |
| [Outbounds and routing](docs/en/routing.md) | WARP / TOR, outbounds from share links, templates, rules |
| [Camouflage site](docs/en/site.md) | what a browser sees on the domain |
| [Commands](docs/en/commands.md) | full command reference with examples |
| [Updates, firewall, files](docs/en/maintenance.md) | `check-updates`, firewall, certificate renewal, file locations |
| [Clients](docs/en/clients.md) | client apps, client-side routing |

## Clients

[v2rayNG](https://github.com/2dust/v2rayNG/releases/latest),
[NekoBox / nekoray](https://github.com/MatsuriDayo/nekoray/releases/latest),
[Hiddify](https://hiddify.com/) — more in [clients](docs/en/clients.md).

> [!CAUTION]
> A client app sees all of your traffic. Use only apps you trust, download
> them from their official pages, and keep in mind that every executable you
> install is your own decision and your own risk.
