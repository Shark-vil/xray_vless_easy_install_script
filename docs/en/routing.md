# Outbounds and routing

[🇷🇺 Русская версия](../ru/routing.md) · [← Home](index.md)

## Outbounds / tunnels
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

An added outbound gets a tag (`vless1`, `socks1`, … or `--tag`). Like any
outbound in `config.json`, it can be the target of rules (`xvei rule add <tag>
…`), the template tunnel (`--tunnel <tag>`) and the in-country exit of a
country template (`--exit <tag>`). The `#name` part of a
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

## Routing templates
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

## Your own rules

Send domains / IPs to any outbound in `config.json` — `direct`, `block`,
`warp` / `tor` (xvei sets them up when needed) or any tag:

```bash
xvei rule add direct geosite:apple domain:example.com
xvei rule add warp geosite:openai
xvei rule add gemini_proxy geosite:google-gemini
xvei rule remove warp geosite:openai
```

Matchers: `geosite:…`, `geoip:…`, `domain:…`, `full:…`, `regexp:…`,
`keyword:…`, an IP or a CIDR (`1.2.3.0/24`); a bare name becomes `domain:…`.
They are added to a rule that already sends such matchers to that outbound, or
to a new one at the top, so they are checked before the template.

`xvei rule list` shows every rule in `config.json` with its number, including
the ones written by hand; `xvei rule delete <N>` deletes one. Menu:
`xvei` → `3) Routing rules`.
