# Outbounds и маршрутизация

[🇬🇧 English version](../en/routing.md) · [← Главная](index.md)

## Outbounds / туннели
`direct`, `block`, опционально **WARP** (Cloudflare, docker) или **TOR** —
второй прыжок, скрывающий IP сервера, и **свои outbounds из share-ссылок**:

* `vless://` — транспорты tcp / ws / grpc / xhttp / httpupgrade, security none / tls / reality;
* `vmess://` — base64-JSON формата v2rayN или URL-формат, те же транспорты и security;
* `trojan://` — те же транспорты и security, по умолчанию `tls`;
* `ss://` — SIP002 (base64 или открытый `method:password`) и старый полностью base64-формат;
  AEAD и 2022 шифры (`aes-128-gcm`, `aes-256-gcm`, `chacha20-ietf-poly1305`,
  `xchacha20-ietf-poly1305`, `2022-blake3-*`);
* `socks://`, `socks5://` — с `user:pass` или без (в том числе base64-формат v2rayN);
* `http://`, `https://` — с `user:pass` или без.

Не поддерживаются: `hysteria2://`; ссылки с `allowInsecure=1` (в актуальном
Xray эта опция удалена); потоковые шифры Shadowsocks (`aes-256-cfb` и т.п.) и
плагины; старый VMess с `alterId > 0`.

Добавленный outbound получает тег (`vless1`, `socks1`, … или `--tag`). Как и
любой outbound в `config.json`, он может быть целью правил (`xvei rule add
<тег> …`), туннелем шаблона (`--tunnel <тег>`) и выходом для внутристранового
трафика (`--exit <тег>`). Часть ссылки после `#`
показывается только как подпись.

Добавить outbound (одинарные кавычки обязательны: в ссылке есть `&`):

```bash
xvei add-outbound 'vless://UUID@example.com:443?security=reality&sni=example.com&pbk=KEY&sid=ID&type=tcp&flow=xtls-rprx-vision' --tag fi
```

Добавить несколько сразу:

```bash
xvei add-outbound 'socks5://user:pass@203.0.113.30:1080' 'http://user:pass@203.0.113.40:8080'
```

Пустить через него трафик OpenAI:

```bash
xvei rule add fi geosite:openai
```

Пустить через него весь трафик:

```bash
xvei template none --tunnel fi
```

Удалить:

```bash
xvei remove-outbound fi
```

Outbound, который используется как туннель или выход шаблона, нельзя удалить,
пока шаблон не переключён. Меню: `xvei` → `2) Outbounds` → `Add from share link`.

## Шаблоны маршрутизации
Выбираются при установке (потом меняются через `xvei template`). Это правила
для **сервера**: то, что уходит с реального IP VPS, а не с устройства клиента.

* **Шаблон страны** — `russia` / `iran` / `china` / `none`.
  Внутристрановые адреса (`geoip:<cc>` + локальные категории `geosite`)
  **никогда** не идут напрямую с сервера — прямой выход VPS в сети РФ/Ирана/
  Китая палит его реальный IP перед этой сетью и рискует довести до блокировки.
  Вместо этого такой трафик обязателен `--exit warp|tor|block|<тег>`:
  * `warp` / `tor` / добавленный outbound — уходит вторым прыжком, IP сервера не светится;
  * `block` — просто блокируется.
  Остальной (не внутристрановой) трафик идёт по обычному режиму выхода:
  * `--direct` — напрямую наружу;
  * `--tunnel warp|tor|<тег>` — через туннель.
* **Шаблон «Популярное напрямую»** — `popular`.
  Общемировые сервисы (`geosite:youtube`, `instagram`, `google`, `telegram`,
  `netflix`, `github` и т.д. — теги, которые есть практически в любой сборке
  geosite.dat) идут напрямую для скорости; весь остальной трафик обязателен
  `--tunnel warp|tor|<тег>`.

## Свои правила

Направляйте домены / IP в любой outbound из `config.json` — `direct`, `block`,
`warp` / `tor` (xvei поднимет их при необходимости) или любой тег:

```bash
xvei rule add direct geosite:apple domain:example.com
xvei rule add warp geosite:openai
xvei rule add gemini_proxy geosite:google-gemini
xvei rule remove warp geosite:openai
```

Матчеры: `geosite:…`, `geoip:…`, `domain:…`, `full:…`, `regexp:…`,
`keyword:…`, IP или CIDR (`1.2.3.0/24`); просто имя превращается в
`domain:…`. Они дописываются в правило, которое уже отправляет такие матчеры в
этот outbound, или в новое правило наверху — так они проверяются раньше
шаблона.

`xvei rule list` показывает все правила из `config.json` с номерами, включая
написанные вручную; `xvei rule delete <N>` удаляет любое. Меню:
`xvei` → `3) Routing rules`.
