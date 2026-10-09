# Turnable (VK calls) — unstable, not anonymous

[🇷🇺 Русская версия](../ru/turnable.md) · [← Home](index.md)

> [!WARNING]
> **This method reveals the server's IP address.** Traffic is relayed by the
> TURN servers of VK calls, so VK sees and can log the real IP of this server
> and when it is used — the opposite of what the country templates protect
> against. It is also **unstable**: it depends on VK's anonymous call access,
> which VK can restrict or break at any time (captcha, limits).

`turnable` uses [Turnable](https://github.com/TheAirBlow/Turnable/releases/latest) 0.6.4: the client joins a public VK call
as an anonymous guest and sends its traffic through VK's TURN relays to this
server, which hands it to a local VLESS inbound of Xray (so Xray does the
routing, as with Hysteria2). No VK account, app ID or password is needed.
Limits on VK's side: about 250 KB/s per peer connection, up to 10 connections
per IP.

The server side is a pinned Turnable release checked by sha256; xvei does not
update it automatically (`xvei check-updates` shows when a newer one exists).

Adding it asks for a UDP port (default `56000`) and a link to any public VK
call (`https://vk.com/call/join/...`):

```bash
xvei add-inbound turnable --dest 'https://vk.com/call/join/CALL_ID'
```

On the client device two programs run together:

1. The Turnable client with the `turnable://` link from `xvei links`:

```bash
turnable client -l 127.0.0.1:1080 'turnable://...'
```

2. A proxy app (v2rayNG, NekoBox, …) with the second link from `xvei links`:
   a `vless://` link to `127.0.0.1:1080`.

If VK shows a captcha, the Turnable client prints a local address with
instructions for solving it in a browser. Turnable's config format changes
between versions: if the latest client does not connect, use client 0.6.4.
