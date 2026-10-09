# Outbounds и маршрутизация

**Outbound** — куда трафик уходит с сервера: `direct` (сразу в интернет),
`block` (отбрасывается) или второй прыжок — WARP, TOR или другой сервер.
**Правила маршрутизации** решают, какой трафик куда идёт.

## Второй прыжок: WARP, TOR, свой сервер

Второй прыжок скрывает IP сервера от сайтов, которые вы открываете.

```bash
xvei add-outbound warp    # Cloudflare WARP (работает в docker)
xvei add-outbound tor
```

Другой сервер добавляется по его ссылке. Берите ссылку в кавычки — в ней
есть `&`:

```bash
xvei add-outbound 'vless://UUID@example.com:443?security=reality&sni=example.com&pbk=KEY&sid=ID&type=tcp' --tag fi
```

Поддерживаются: `vless://`, `vmess://`, `trojan://` (tcp / ws / grpc / xhttp /
httpupgrade; none / tls / reality), `ss://` (шифры AEAD и 2022),
`socks5://`, `http://`. Не поддерживаются: `hysteria2://`, ссылки с
`allowInsecure=1`, старые шифры и плагины Shadowsocks, VMess с `alterId > 0`.

По тегу (`fi` выше, по умолчанию `vless1`, `socks1`…) на outbound ссылаются
правила и шаблоны. Удалить: `xvei remove-outbound fi` (пока его не использует
правило). Меню: `xvei` → `2) Outbounds`.

## Свои правила

Направить сайты или адреса в outbound:

```bash
xvei rule add fi geosite:openai          # OpenAI через сервер "fi"
xvei rule add block geosite:category-ads-all
xvei rule add direct domain:example.com
xvei rule remove fi geosite:openai
```

Что можно указывать: `geosite:…` (списки сайтов, например `geosite:youtube`),
`geoip:…` (страны, например `geoip:de`), `domain:…`, `full:…`, `regexp:…`,
`keyword:…`, IP или подсеть (`1.2.3.0/24`). Просто имя вроде `example.com`
означает `domain:example.com`.

`xvei rule list` показывает все правила с номерами, включая написанные вручную
в `config.json`; `xvei rule delete <N>` удаляет правило. Меню: `xvei` →
`3) Routing rules`.

## Шаблоны

Шаблон — готовый набор правил для сервера.

**Страна** — `russia`, `iran`, `china`. Сайты этой страны **никогда** не
открываются с собственного IP сервера: зарубежный сервер, который ходит на них
напрямую, замечают и блокируют. Они идут через второй прыжок или блокируются:

```bash
xvei template russia --exit warp --direct    # российские сайты через WARP, остальное напрямую
xvei template russia --exit block --tunnel tor
```

**Популярное** — крупные международные сервисы (YouTube, Google, Instagram,
Telegram, Netflix, GitHub…) идут напрямую ради скорости, остальное через
туннель:

```bash
xvei template popular --tunnel warp
```

**Без шаблона** — задаётся только, куда идёт всё остальное:

```bash
xvei template none --direct       # всё напрямую
xvei template none --tunnel fi    # всё через "fi"
```

Без `--direct` и `--tunnel` правило «всё остальное» не меняется. Меню:
`xvei` → `4) Routing template`.

## Порядок правил

Правила проверяются сверху вниз, срабатывает первое подходящее. Трафик, под
который не подошло ни одно, идёт в первый outbound. Новый конфиг выглядит так:

1. **Защита** — блокируются BitTorrent, локальные адреса и порты общего доступа
   к файлам Windows.
2. **Ваши правила** — сюда добавляет `xvei rule add`.
3. **Шаблон** — сайты страны или популярные.
4. **Всё остальное** — напрямую или через туннель.

Всё это — обычные правила в `config.json`. Правило шаблона, изменённое
вручную, перестаёт быть частью шаблона и становится вашим.
