# Outbounds and routing

An **outbound** is where traffic leaves the server to: `direct` (straight to
the internet), `block` (dropped), or a second hop — WARP, TOR or another server.
**Routing rules** decide which traffic goes where.

## Second hop: WARP, TOR, your own server

A second hop hides the server's IP from the sites you open.

```bash
xvei add-outbound warp    # Cloudflare WARP (runs in docker)
xvei add-outbound tor
```

Another server is added from its share link. Quote the link — it contains `&`:

```bash
xvei add-outbound 'vless://UUID@example.com:443?security=reality&sni=example.com&pbk=KEY&sid=ID&type=tcp' --tag fi
```

Supported links: `vless://`, `vmess://`, `trojan://` (tcp / ws / grpc / xhttp /
httpupgrade; none / tls / reality), `ss://` (AEAD and 2022 ciphers),
`socks5://`, `http://`. Not supported: `hysteria2://`, links with
`allowInsecure=1`, old Shadowsocks ciphers and plugins, VMess with
`alterId > 0`.

The tag (`fi` above, or `vless1`, `socks1`… by default) is how you refer to
the outbound in rules and templates. Remove it with `xvei remove-outbound fi`
(not while a rule uses it). Menu: `xvei` → `2) Outbounds`.

## Your rules

Send sites or addresses to an outbound:

```bash
xvei rule add fi geosite:openai          # OpenAI through the "fi" server
xvei rule add block geosite:category-ads-all
xvei rule add direct domain:example.com
xvei rule remove fi geosite:openai
```

What can be matched: `geosite:…` (site lists such as `geosite:youtube`),
`geoip:…` (countries, e.g. `geoip:de`), `domain:…`, `full:…`, `regexp:…`,
`keyword:…`, an IP or a network (`1.2.3.0/24`). A plain name like
`example.com` means `domain:example.com`.

`xvei rule list` shows all rules with numbers, including ones written by hand
in `config.json`; `xvei rule delete <N>` deletes one. Menu: `xvei` →
`3) Routing rules`.

## Templates

A template is a ready set of rules for the server.

**Country** — `russia`, `iran`, `china`. Sites of that country are **never**
opened from the server's own IP: a foreign server that goes straight to them
gets noticed and blocked. They go through a second hop or are blocked:

```bash
xvei template russia --exit warp --direct    # Russian sites via WARP, the rest direct
xvei template russia --exit block --tunnel tor
```

**Popular** — big international services (YouTube, Google, Instagram,
Telegram, Netflix, GitHub…) go directly for speed, the rest through a tunnel:

```bash
xvei template popular --tunnel warp
```

**None** — no template; set only where the rest goes:

```bash
xvei template none --direct       # everything directly
xvei template none --tunnel fi    # everything through "fi"
```

Without `--direct` or `--tunnel` the "everything else" rule stays as it is.
Menu: `xvei` → `4) Routing template`.

## Order of the rules

Rules are checked from the top; the first one that matches wins. Traffic that
matches none goes to the first outbound. A new config looks like this:

1. **Protection** — BitTorrent, local addresses and Windows file-sharing ports
   are blocked.
2. **Your rules** — `xvei rule add` puts new ones here.
3. **Template** — country or popular sites.
4. **Everything else** — direct or through a tunnel.

All of these are ordinary rules in `config.json`. A template rule changed by
hand stops being part of the template and becomes your own rule.
