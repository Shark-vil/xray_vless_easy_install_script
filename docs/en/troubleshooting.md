# Troubleshooting

[🇷🇺 Русская версия](../ru/troubleshooting.md) · [← Home](index.md)

## First checks

Services and the active template:

```bash
xvei status
```

The current Xray config, readable:

```bash
xvei show-config
```

Which ports a firewall on the server blocks:

```bash
xvei firewall status
```

## Logs

| component | command |
|---|---|
| Xray | `journalctl -u xray -n 50` |
| nginx (camouflage site) | `journalctl -u nginx -n 50` |
| Hysteria2 | `journalctl -u hysteria-server -n 50` |
| Turnable | `journalctl -u turnable -n 50` |
| TOR | `journalctl -u tor -n 50` (on Debian/Ubuntu also `tor@default`) |
| WARP | `docker logs warp-xray --tail 50` |
| certificate | `/var/log/letsencrypt/letsencrypt.log` |

## Clients cannot connect

1. **Ports.** Check `xvei firewall status`. Also check the firewall in your
   cloud provider's control panel — xvei cannot see or change it.
2. **Links are current.** Links change when an inbound is re-added. Print them
   again with `xvei links` and re-import.
3. **Client version.** REALITY and XHTTP need a recent client build.
4. **Server time** (VMess only). VMess fails when the server clock is off by
   more than 120 seconds. Check with `timedatectl`; enable time sync with
   `timedatectl set-ntp true`.
5. **Trojan on TCP** (`trojan-tcp`). The client must use ALPN `http/1.1` — it is
   in the generated link; if the link was typed by hand, add `alpn=http/1.1`.

## "certbot failed; falling back to a self-signed certificate"

Let's Encrypt could not verify the domain. Clients do not trust the
self-signed certificate, so TLS inbounds will not work until this is fixed.

1. The domain's A record must point to this server — check with
   `dig +short your.domain` or `ping your.domain`.
2. Port `80/tcp` must be reachable from the internet during the check — in the
   server's firewall and in the provider's control panel.
3. Then run `xvei apply` — it requests the certificate again.

## "the changed config failed validation; … was not touched"

The change was not applied and is dropped; Xray keeps running with the
previous config. The error from `xray -test` is printed above the message. If
`config.json` was edited by hand, the error may be in that edit - check it with
`xray run -test -config /usr/local/etc/xray/config.json`.

## "xray did not come up; rolling back to previous config"

The new config passed the check but Xray did not start — usually a port is
already in use by another program. See `journalctl -u xray -n 50`; list the
listening ports with `ss -tulpn`.

## Turnable

Read the [warnings](turnable.md) first: the method is unstable by design.

- **The client asks for a captcha** — open the local address it prints and
  follow the instructions there.
- **It stops working for everyone** — VK may have changed its call access;
  check for a new Turnable release (`xvei check-updates` shows it).
- **Slow** — VK limits each connection to about 250 KB/s.

## Start over

Remove everything xvei installed (on an adopted server — only what xvei
added):

```bash
xvei remove --all
```

Then install again as in [getting started](getting-started.md).
