# Camouflage site

What a browser sees when it opens your domain. Only connection types with your
own domain (`vless-tls`, `vless-xhttp-tls`) have one.

| option | what the browser sees |
|---|---|
| `auth` | a login prompt that never accepts anything *(default)* |
| `blank` | a plain "It works" page |
| `404` | "page not found" |
| `nebula`, `critters`, `game2048`, `snake`, `notes` | a small ready-made site: solar system facts, animal encyclopedia, 2048 game, snake game, personal blog. Loads nothing from outside |
| `proxy <url>` | a real site shown through your server. Many sites break this way; these work: `example`, `rfc`, `cern`, `gnu`, `iana` |

```bash
xvei site game2048
xvei site proxy gnu
xvei site            # list the options
```

Menu: `xvei` → `5) Camouflage site`.
