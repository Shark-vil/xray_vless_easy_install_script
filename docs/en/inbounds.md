# Inbounds

An inbound is a way for clients to connect to the server. You can run several
at once.

## Which one to choose

| type | domain | status | in short |
|---|---|---|---|
| `vless-xhttp-reality` | no | ✅ recommended | imitates a big site (`www.microsoft.com` by default); traffic looks like ordinary web requests |
| `vless-tls` | yes | ✅ recommended | VLESS with Vision on port 443; a browser sees your [camouflage site](site.md) |
| `vless-xhttp-tls` | yes | ✅ recommended | like `vless-tls`, web-request-shaped traffic; works through a CDN |
| `vless-ws` | yes | 🟡 situational | WebSocket; for CDNs that only pass WebSocket |
| `hysteria2` | optional | 🟡 situational | fast on poor connections; some networks slow down or block UDP |
| `trojan-tcp`, `trojan-ws` | yes | 🟠 legacy | deprecated in Xray; only for clients without VLESS |
| `vmess-ws` | yes | 🟠 legacy | deprecated in Xray; the server clock must be accurate (±120 s) |
| `shadowsocks` | no | 🔴 weak where traffic is filtered | easy to recognise; fine on open networks |
| `turnable` | no | ⚠️ experimental | through VK calls; unstable and **shows the server IP to VK** — [read first](turnable.md) |

A good setup: `vless-xhttp-reality` plus `vless-tls`, with `hysteria2` as a fast
extra where UDP works. The status is as of 2026 and differs between countries
and providers.

## How they share port 443

`vless-tls` holds TCP port 443. `vless-ws`, `vless-xhttp-tls`, `trojan-*` and
`vmess-ws` work behind it, so they need it first (the wizard adds it
automatically). Each gets a random secret path; anything else that reaches the
port, such as a browser, gets the camouflage site.
[How it works](architecture.md#one-port-443-for-many-inbounds)

`hysteria2` and `turnable` are separate programs; they hand their traffic to
Xray, so routing rules apply to them too.

## Add or remove

```bash
xvei add-inbound vless-xhttp-reality --dest www.samsung.com
xvei add-inbound shadowsocks --port 5465
xvei remove-inbound ss
```

Or in the menu: `xvei` → `1) Inbounds`.
