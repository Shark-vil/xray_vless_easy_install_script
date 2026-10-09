# How it works

## Parts

```mermaid
flowchart LR
    user([xvei menu / command]) --> bash[bash: lib/*.sh]
    bash --> engine[Python: pyengine/]
    engine <--> xcfg[(config.json)]
    engine <--> state[(xvei-state.json)]
    engine --> other[Hysteria2, Turnable, nginx configs]
    bash --> sys[packages, certificates, services, firewall, docker]
```

- **`config.json`** (`/usr/local/etc/xray/`) is the Xray config and the main
  source of truth. xvei reads it on every run, so edits made by hand are seen
  at once.
- **`xvei-state.json`** next to it keeps only what `config.json` cannot hold:
  domain, certificate, camouflage site, Hysteria2 / Turnable settings, and
  what xvei created itself (so it never touches someone else's nginx or WARP).
- **Python part** (standard library only) changes the config.
- **Bash part** does the system work: packages, certificates, nginx, services,
  firewall.

## How a change is applied

```mermaid
flowchart TD
    A[menu or command] --> B[back up config.json]
    B --> C[change a copy of config.json]
    C --> D[certificate, nginx, WARP, TOR if needed]
    D --> E{xray -test on the copy}
    E -- fails --> F[nothing changes]
    E -- passes --> G[replace config.json, restart Xray]
    G --> H{Xray running?}
    H -- no --> I[put the previous config back]
    H -- yes --> J[update Hysteria2, Turnable, nginx]
```

The change always starts from `config.json` as it is on disk, so hand edits are
kept.

## One port 443 for many inbounds

`vless-tls` holds port 443 and handles encryption. What is not VLESS it passes
on by request path and protocol:

```mermaid
flowchart LR
    C([client :443]) --> V[vless-tls]
    V -- "secret path" --> W[vless-ws / trojan-ws / vmess-ws / vless-xhttp-tls]
    V -- "HTTP/2" --> N2[nginx :8081 site]
    V -- "anything else" --> T{trojan-tcp?}
    T -- yes --> TR[trojan-tcp] -- not Trojan --> N1[nginx :8080 site]
    T -- no --> N1
```

The paths are random, so a browser always lands on the camouflage site. The
inner hops stay inside the server.

## Hysteria2 and Turnable

They are separate programs that pass traffic into a local Xray inbound, so
Xray's routing rules apply to them too:

```mermaid
flowchart LR
    H([Hysteria2 client]) -- UDP --> HS[hysteria-server] --> S[Xray 127.0.0.1]
    T([Turnable client]) -- VK calls --> TS[turnable] --> S
    S --> R[Xray routing]
```

The order of routing rules is described in [routing](routing.md#order-of-the-rules).
