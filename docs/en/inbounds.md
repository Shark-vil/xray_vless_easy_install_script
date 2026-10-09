# Inbounds

[🇷🇺 Русская версия](../ru/inbounds.md) · [← Home](index.md)

| type | notes |
|---|---|
| `vless-tls` | VLESS + TCP + TLS + `xtls-rprx-vision`, on `:443`, nginx fallback |
| `vless-ws` | VLESS + WebSocket, rides the `:443` fallback (needs `vless-tls`) |
| `vless-xhttp-reality` | VLESS + XHTTP + **REALITY** — site masquerade, **no domain/cert required** |
| `vless-xhttp-tls` | VLESS + XHTTP + TLS certificate (shares `:443` or standalone) |
| `trojan-tcp` | Trojan + TCP, shares `:443` with `vless-tls`: anything that is not VLESS goes to Trojan, anything that is not Trojan goes to the camouflage site. The client must use ALPN `http/1.1` (set in the generated link) |
| `trojan-ws` | Trojan + WebSocket through the `:443` fallback (needs `vless-tls`) |
| `vmess-ws` | VMess (AEAD) + WebSocket through the `:443` fallback (needs `vless-tls`); the server clock must be accurate to ±120 s |
| `shadowsocks` | Shadowsocks 2022 / legacy ciphers |
| `hysteria2` | Hysteria2 on `:443/udp`; **all its traffic is forwarded into a local SOCKS5 inbound of Xray**, so Xray does the routing |
| `turnable` | ⚠️ **Unstable, not anonymous.** Tunnel through the TURN relays of VK calls into a local VLESS inbound; **VK sees the server's IP**. See [Turnable](turnable.md) |

## Which inbound to choose (2026)

| inbound | status | why |
|---|---|---|
| `vless-xhttp-reality` | ✅ recommended | No domain or certificate; the TLS handshake is a real one borrowed from a large site, and XHTTP traffic looks like ordinary HTTP requests |
| `vless-tls` (Vision) | ✅ recommended | Real domain and certificate, a working site on the same address; Vision removes the TLS-inside-TLS pattern |
| `vless-xhttp-tls` | ✅ recommended | Like `vless-tls`, HTTP-shaped traffic; can also run behind a CDN |
| `vless-ws` | 🟡 situational | Needed mainly for CDNs that only pass WebSocket; the WebSocket upgrade is a well-known pattern, XHTTP is preferred |
| `hysteria2` | 🟡 situational | Fast on lossy links; UDP/QUIC is throttled or dropped entirely on some networks |
| `trojan-tcp`, `trojan-ws` | 🟠 legacy | Xray itself marks Trojan as deprecated (startup notice) and recommends VLESS; no Vision, so the TLS-inside-TLS pattern remains; keep for clients that only speak Trojan |
| `vmess-ws` | 🟠 legacy | Deprecated in Xray (startup notice), no forward secrecy, depends on the clock; keep for old clients only |
| `shadowsocks` (2022 / AEAD) | 🔴 weak on filtered networks | Fully random-looking traffic is recognised by its byte statistics alone (documented since 2021); fine on unfiltered networks |
| `turnable` | ⚠️ experimental | Unstable (depends on VK's anonymous call access) and not anonymous: VK sees the server's IP; ~250 KB/s per connection |

Status reflects Xray's own deprecation notices and public measurements as of
2026; the situation differs between countries and providers. A practical
setup: `vless-xhttp-reality` plus `vless-tls`, with `hysteria2` as a fast
extra where UDP works.
