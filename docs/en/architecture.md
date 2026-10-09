# How it works

[🇷🇺 Русская версия](../ru/architecture.md) · [← Home](index.md)

## Components

```mermaid
flowchart LR
    user([xvei command / menu]) --> bash[bash: lib/*.sh]
    bash --> engine[Python engine: pyengine/]
    engine <--> xcfg[(config.json)]
    engine <--> state[(xvei-state.json)]
    engine --> hcfg[hysteria config.yaml]
    engine --> tcfg[turnable config.json]
    engine --> ncfg[nginx vhost]
    bash --> sys[packages, certbot, systemd, firewall, docker]
```

- **`config.json`** is the source of truth for everything Xray runs:
  inbounds, outbounds and routing rules. Every command reads it fresh, so what
  was edited by hand is shown in the menus, linked and used at once.
- **State file** `/usr/local/etc/xray/xvei-state.json` keeps only what
  `config.json` cannot hold: domain, e-mail, certificate paths, the camouflage
  site, which inbounds and services xvei created itself (so it never stops
  someone else's nginx or WARP), and the Hysteria2 / Turnable settings.
- **Python engine** (standard library only) makes a change on a copy of
  `config.json` and stages it; it renders the Hysteria2 / Turnable / nginx
  configs. It never touches the system.
- **Bash part** does everything system-side: packages, certificates, nginx,
  services, firewall, WARP container, Turnable.

## Applying a change

```mermaid
flowchart TD
    A[command or menu changes a copy of config.json] --> B[provision: certificate, nginx, WARP, TOR, Turnable]
    B --> D{xray -test on the copy}
    D -- fails --> E[live config untouched; the change is dropped]
    D -- passes --> F[back up config.json, swap in, restart xray]
    F --> G{xray running?}
    G -- no --> H[restore the backup, restart]
    G -- yes --> I[apply Hysteria2 / Turnable, refresh nginx]
```

Every change starts from `config.json` as it is on disk, so edits made by hand
are kept - xvei never rebuilds the file from its own copy.

## One port 443 for many inbounds

`vless-tls` owns TCP port 443 and terminates TLS. Whatever is not VLESS is
handed on by *fallbacks*, chosen by request path and ALPN:

```mermaid
flowchart LR
    C([client :443]) --> V[vless-tls<br/>TLS + VLESS]
    V -- "path /…xhttp" --> X[vless-xhttp-tls]
    V -- "path /…ws" --> W[vless-ws / trojan-ws / vmess-ws]
    V -- "ALPN h2" --> N2[nginx :8081<br/>HTTP/2 site]
    V -- "anything else" --> T{trojan-tcp<br/>enabled?}
    T -- yes --> TR[trojan-tcp] -- not Trojan --> N1[nginx :8080<br/>site]
    T -- no --> N1
```

The secret paths are random; a normal browser always ends up on the camouflage
site. The internal hops use local sockets and never leave the server.

## Inbounds that are not Xray

Hysteria2 and Turnable are separate programs. They receive the traffic and pass
it into a local inbound of Xray, so Xray does all the routing for them too:

```mermaid
flowchart LR
    H([Hysteria2 client]) -- UDP --> HS[hysteria-server] --> S[Xray SOCKS 127.0.0.1]
    T([Turnable client]) -- VK TURN relays --> TS[turnable server] --> V[Xray VLESS 127.0.0.1]
    S --> R[Xray routing]
    V --> R
```

## Routing order

Rules are checked top to bottom; the first match wins; traffic that matches
nothing takes the first outbound. A fresh config starts like this:

1. **Guardrails** — BitTorrent, private addresses and Windows file-sharing
   ports are blocked.
2. **Your rules** — `xvei rule add <outbound> <matcher>` adds to a rule that
   already sends such matchers there, or creates one at the top (after the
   guardrails).
3. **Template** — in-country traffic goes to the chosen exit (WARP, TOR, an
   outbound, or block — never direct); for `popular`, the popular services go
   direct. A template's rules are recognised by what they match; one edited by
   hand becomes an ordinary rule.
4. **Everything else** — the last rule, when it only matches `network
   tcp,udp`: direct, or through the chosen tunnel.

All of it is plain rules in `config.json`; `xvei rule list` shows them
numbered, `xvei rule delete <N>` removes any of them.

## Taking over an existing setup

Adopting an existing Xray changes nothing, and from then on its `config.json`
is handled like any other: its inbounds, outbounds and rules are listed,
linked, used and removable; its first outbound stays the default route; no
guardrails and no "everything else" rule are added unless chosen. tor, the WARP
container, Hysteria2, Turnable and nginx are only stopped or changed if xvei
started them itself (markers in `/var/lib/xvei/managed`).
