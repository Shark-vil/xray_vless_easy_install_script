# Maintenance

## Backups and rollback

Before every change through xvei, the current `config.json` (comments
included) and xvei's settings are saved to `/usr/local/etc/xray/xvei-backups/`.
The last 20 are kept.

Menu: `xvei` → `11) Backups`. The list shows 10 per page (`n` / `p` turn pages).
Open a backup to view its config, see what rolling back would change, roll
back or delete it. `c` makes a backup now, `k` sets how many to keep.

```bash
xvei backup                  # list
xvei backup restore 1        # undo the last change
xvei backup diff 3           # what rolling back to backup 3 would change
xvei backup create "note"    # back up now, e.g. before editing config.json by hand
xvei backup keep 50          # keep 50; 0 = no automatic backups
```

A rollback is checked like any change, and the current config is backed up
first, so a rollback can be undone too.

## Updates

```bash
xvei check-updates
```

Shows the installed and latest versions of xvei, Xray, Hysteria2 and the
site / country lists, then asks which to update (all by default). Menu:
`10) Updates`. In a git clone, update xvei with `git pull`.

## Firewall

xvei **never turns on or tightens a firewall by itself**: a wrong setting can
lock you out of SSH.

- If ufw or firewalld is already on and blocks a port xvei needs, xvei offers
  to open it. It only adds permissions.
- `xvei firewall status` — which ports are open or closed.
- `xvei firewall open` — open the ports xvei needs.
- `xvei firewall setup` — optional lockdown: block all incoming traffic except
  SSH and xvei's ports. The SSH port is detected automatically; the plan is
  shown first and nothing happens without your "yes".

Menu: `9) Firewall`.

## Certificate

The Let's Encrypt certificate renews itself. After renewal xvei's hook
restarts Xray, nginx and Hysteria2 so they use the new certificate.

## Uninstall

```bash
xvei remove          # xvei only; Xray and everything else keep running
xvei remove --all    # xvei and everything it set up
```

Both show what will be removed and ask first. Menu: `12) Uninstall xvei`.

- **`xvei remove`** deletes the xvei command, its files and backups. Xray, its
  config, nginx, WARP, TOR, Hysteria2 and certificates stay and keep working.
- **`xvei remove --all`** also removes Xray and its config, Hysteria2, Turnable,
  WARP, TOR and xvei's nginx site. If Xray was there before xvei, Xray stays
  and you can restore its original config. Then it asks whether to remove the
  packages xvei installed (nginx, certbot, tor, qrencode, docker).

Certificates are always kept. In scripts add `--yes` (and `--packages` to
remove the packages without asking). A git clone is not deleted.

## Files

| path | what |
|---|---|
| `/usr/local/etc/xray/config.json` | Xray config — edit by hand or through xvei |
| `/usr/local/etc/xray/xvei-backups/` | backups |
| `/usr/local/etc/xray/xvei-state.json` | xvei's settings: domain, certificate, site, Hysteria2 / Turnable |
| `/usr/local/etc/xray/config.json.xvei-orig` | original config of a server xvei took over |
| `/etc/hysteria/config.yaml` | Hysteria2 config |
| `/etc/nginx/sites-enabled/xvei.conf` or `/etc/nginx/conf.d/xvei.conf`, `/var/www/xvei-site` | camouflage site |
| `/etc/turnable/config.json` | Turnable config |
| `/usr/local/lib/xvei` | xvei itself |
