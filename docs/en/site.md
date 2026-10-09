# Camouflage site &nbsp;·&nbsp; [🇷🇺 RU](../ru/site.md)

[← README](../../README.md)

What a normal browser sees when it opens the domain directly (the nginx
fallback for `vless-tls` / `vless-xhttp-tls`). Change any time with `xvei site`:

* `auth` — HTTP Basic auth prompt against an empty file, always 401 *(default, same as the old script)*
* `blank` / `404` — a bare page / plain 404
* static presets — self-contained pages with **no external requests** (safe, work offline):
  `nebula` (solar-system facts), `critters` (animal encyclopedia),
  `game2048`, `snake`, `notes` (a personal blog)
* `proxy <url|preset>` — reverse-proxy a real upstream. Most sites break when
  proxied (bot walls, host checks, absolute redirects), so a few known-proxyable
  ones are presets: `example`, `rfc`, `cern`, `gnu`, `iana`.
