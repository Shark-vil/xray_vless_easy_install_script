# Installation

## Supported systems

| system | status |
|---|---|
| Ubuntu 20.04 / 22.04 / 24.04 | ✅ supported |
| Debian 11 / 12 / 13 | ✅ supported |
| CentOS Stream 9 | ✅ supported |
| AlmaLinux / Rocky / RHEL 9, CentOS Stream 10, Fedora | ❓ not tested, probably works |
| CentOS 7, CentOS Stream 8, other EL8 | ❌ not supported (end of life, Python 3.6) |
| Alpine, systems without systemd | ❌ not supported |

On other systems the installer warns and asks before going on.

Needed: root, systemd, Python 3.7+ (installed if missing). Everything else —
Xray, certbot, nginx, Hysteria2, docker for WARP, tor — is installed only when a
setting needs it.

On CentOS the installer also turns on EPEL (certbot, tor and qrencode live
there), lets nginx use its local ports under SELinux, and turns on the
certificate renewal timer.

## Ways to install

Install `curl` first if it is missing: `apt-get update && apt-get -y install
curl` (Ubuntu / Debian) or `dnf -y install curl tar` (CentOS).

**Full install** — the script, Xray and the setup wizard:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

**Script only** — puts the script into `/usr/local/lib/xvei` and creates the
`xvei` command; nothing else is installed until you run `xvei install`:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) help
```

**From a git clone** — the `xvei` command then points to the clone, and you
update it with `git pull`:

```bash
git clone https://github.com/Shark-vil/xray_vless_easy_install_script.git
cd xray_vless_easy_install_script
bash xvei.sh install
```

## Server with Xray already installed

If the server already has Xray with `/usr/local/etc/xray/config.json`,
`xvei install` takes it over: nothing is installed, changed or restarted.

xvei works with that `config.json` as it is. It keeps no copy of its own, so
whatever you change in the file by hand is visible in xvei at once and stays
when you change something through xvei. You can:

- get links and QR codes for the existing connections, one per client;
- use the existing outbounds in rules and templates (if the config already has
  its own `warp_proxy` or `tor_proxy`, xvei uses it instead of starting its own);
- see, add and delete routing rules;
- add new connection types — WebSocket, XHTTP and Trojan go behind the existing
  TLS connection on port 443;
- remove inbounds and outbounds (not while a rule uses them).

xvei only stops or changes nginx, WARP, TOR and Hysteria2 if it started them
itself. Before its first change the original config is saved as
`config.json.xvei-orig`, comments included.

Not taken over (nothing changes, the reason is shown): Xray managed by a panel
(x-ui / 3x-ui), or `xray.service` that reads its config from another path or a
folder (`-confdir`).
