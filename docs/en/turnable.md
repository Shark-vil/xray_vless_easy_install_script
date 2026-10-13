# Turnable

!!! danger "Unstable and not anonymous"
    Traffic goes through a third-party service, so **that service sees the real
    IP of your server** and when it is used. It can also restrict or break the
    method at any time.

[Turnable](https://github.com/TheAirBlow/Turnable/releases/latest) joins a
public call on an external service as an anonymous guest and passes your
traffic through its relays to the server. No account is needed. Speed is about 250 KB/s per
connection, up to 10 connections per IP.

## Set up

You need a UDP port (default `56000`) and a link to any public call:

```bash
xvei add-inbound turnable --dest 'https://vk.com/call/join/CALL_ID'
```

xvei installs Turnable 0.7.1 (checked by sha256). It is not updated
automatically; `xvei check-updates` shows when a new version is out.

## Connect

`xvei links` prints two links. On the client device run both programs:

1. The Turnable client with the `turnable://` link:

    ```bash
    turnable client -l 127.0.0.1:1080 'turnable://...'
    ```

2. A client app (v2rayNG, NekoBox…) with the `vless://` link — it connects to
   `127.0.0.1:1080`.

The client must be Turnable 0.7.0 or newer: the link uses the `mpath`
transport, which older clients do not know. After xvei updates Turnable, take
the `turnable://` link from `xvei links` again.

If the service asks for a captcha, the Turnable client prints a local address where you
can solve it in a browser. If the newest client does not connect, use version
0.7.1.
