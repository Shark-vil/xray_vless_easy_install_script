# Installation

[🇷🇺 Русская версия](../ru/install.md) · [← Home](index.md)

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
