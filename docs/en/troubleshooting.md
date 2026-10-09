# Troubleshooting

## Start here

```bash
xvei status          # summary and which services run
xvei show-config     # the Xray config
xvei firewall status # which ports are blocked
```

If a change broke something, roll it back: `xvei backup restore 1`.

## Logs

| what | command |
|---|---|
| Xray | `journalctl -u xray -n 50` |
| nginx (camouflage site) | `journalctl -u nginx -n 50` |
| Hysteria2 | `journalctl -u hysteria-server -n 50` |
| Turnable | `journalctl -u turnable -n 50` |
| TOR | `journalctl -u tor -n 50` |
| WARP | `docker logs warp-xray --tail 50` |
| certificate | `/var/log/letsencrypt/letsencrypt.log` |

## The client does not connect

1. **Ports** — `xvei firewall status`, and the firewall in your provider's
   control panel (xvei cannot see it).
2. **Old link** — re-adding an inbound changes its link. Take a fresh one:
   `xvei links`.
3. **Old app** — REALITY and XHTTP need a recent version.
4. **VMess only** — the server clock must be accurate: `timedatectl
   set-ntp true`.
5. **Trojan TCP only** — the link must have `alpn=http/1.1` (links from xvei
   have it).

## "certbot failed; falling back to a self-signed certificate"

Let's Encrypt could not check the domain, and clients will not accept the
temporary certificate.

1. The domain must point to this server: `dig +short your.domain`.
2. Port `80/tcp` must be open, including in the provider's panel.
3. Then run `xvei apply`.

## "the changed config failed validation"

The change did not pass the check and was not applied; Xray keeps the previous
config. The reason is printed above. If you edited `config.json` by hand, the
mistake may be there:
`xray run -test -config /usr/local/etc/xray/config.json`.

## "xray did not come up; rolling back"

The config is valid but Xray did not start, usually because another program
uses the port: `journalctl -u xray -n 50`, `ss -tulpn`.

## Turnable

- **Captcha** — open the local address the client prints.
- **Stopped working** — VK may have changed something; `xvei check-updates`
  shows a new Turnable version.
- **Slow** — VK limits a connection to about 250 KB/s.

## Start over

```bash
xvei remove --all
```

Then install again as in [getting started](getting-started.md).
