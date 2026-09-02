# XVEI — простая установка и живой редактор Xray (+ Hysteria2)

## [Documentation in English](/README.md)

Все команды выполняйте от **root**.

XVEI ставит и настраивает [Xray-core](https://github.com/XTLS/Xray-install)
(и по желанию [Hysteria2](https://v2.hysteria.network/)), а затем позволяет
менять конфигурацию **без переустановки** — добавлять/удалять inbounds,
включать/выключать WARP/TOR, править правила маршрутизации, менять шаблон
страны, подменять сайт-прикрытие. Каждое изменение проверяется и применяется
автоматически.

Вся конфигурация хранится в одном файле состояния
(`/usr/local/etc/xray/xvei-state.json`). Небольшой движок на Python (только
стандартная библиотека, без сторонних пакетов) заново собирает `config.json`,
проверяет его через `xray -test` и только после этого подменяет боевой конфиг и
перезапускает сервисы. Если проверка не прошла — рабочий конфиг не трогается.

## Возможности

### Inbounds
| тип | описание |
|---|---|
| `vless-tls` | VLESS + TCP + TLS + `xtls-rprx-vision`, порт `:443`, фолбэк в nginx |
| `vless-ws` | VLESS + WebSocket через фолбэк `:443` (нужен `vless-tls`) |
| `vless-xhttp-reality` | VLESS + XHTTP + **REALITY** — маскировка под чужой сайт, **домен и сертификат НЕ нужны** |
| `vless-xhttp-tls` | VLESS + XHTTP + TLS-сертификат (делит `:443` или отдельный порт) |
| `shadowsocks` | Shadowsocks 2022 / legacy шифры |
| `hysteria2` | Hysteria2 на `:443/udp`; **весь его трафик уходит в локальный SOCKS5-inbound Xray**, поэтому маршрутизацию делает Xray |

### Outbounds / туннели
`direct`, `block` и опционально **WARP** (Cloudflare, docker) или **TOR** —
второй прыжок, скрывающий IP сервера.

### Шаблоны маршрутизации
Выбираются при установке (потом меняются через `xvei template`):

* **Шаблон страны** — `russia` / `iran` / `china` / `none`.
  Внутристрановые адреса (`geoip:<cc>` + локальные категории `geosite`) всегда
  идут **напрямую**; остальное — по режиму выхода.
* **Режим выхода**
  * `--direct` — всё, кроме внутристранового списка, идёт напрямую наружу;
  * `--tunnel warp|tor` — всё, кроме внутристранового списка, идёт через туннель.

### Редактируемые группы правил
`block`, `direct`, `warp`, `tor` — добавляйте/удаляйте матчеры
(`geosite:…`, `geoip:…`, `domain:…`, `1.2.3.0/24`, `regexp:…`) на лету.

### Сайт-прикрытие
То, что видит обычный браузер при заходе на домен напрямую (фолбэк nginx для
`vless-tls` / `vless-xhttp-tls`). Меняется в любой момент через `xvei site`:

* `auth` — запрос HTTP Basic-авторизации в пустой файл, всегда 401 *(по умолчанию, как в старом скрипте)*
* `blank` / `404` — пустая страница / просто 404
* статические заготовки — **без единого внешнего запроса** (безопасно, работают офлайн):
  `nebula` (факты о планетах), `critters` (энциклопедия животных),
  `game2048`, `snake`, `notes` (личный блог)
* `proxy <url|preset>` — реверс-прокси реального сайта. Большинство сайтов
  ломаются при проксировании (защита от ботов, проверка Host, абсолютные
  редиректы), поэтому есть заготовки известных «проксируемых»: `example`, `rfc`,
  `cern`, `gnu`, `iana`.

## Установка

```bash
apt-get update && apt-get -y install curl
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

Первый запуск скачает дерево скриптов в `/usr/local/lib/xvei` и создаст симлинк
`xvei` в `/usr/local/bin` — дальше достаточно команды `xvei`.

## Команды

```
xvei                     интерактивное меню (или предложит установку)
xvei install             мастер первичной установки
xvei edit                интерактивное меню
xvei apply               пересобрать + проверить + перезапустить из текущего состояния

xvei add-inbound  <тип> [--port N] [--dest SNI] [--method M]
xvei remove-inbound <tag>
xvei add-outbound   <warp|tor>
xvei remove-outbound <warp|tor>
xvei rule <add|remove|list> <block|warp|tor|direct> [матчер ...]
xvei template <russia|iran|china|none> [--tunnel <warp|tor> | --direct]
xvei site [list | auth | blank | 404 | <заготовка> | proxy <url|preset>]

xvei links [tag]         вывести клиентские ссылки
xvei qr <tag>            QR-код для одного inbound
xvei status              сервисы и активный шаблон
xvei set-meta [--domain D --email E ...]
xvei update-geo          обновить geoip/geosite (необязательно; их ставит установщик xray)
xvei self-update         перекачать дерево скриптов
xvei remove              полное удаление
```

Примеры:

```bash
xvei add-inbound vless-xhttp-reality --dest www.samsung.com
xvei add-outbound tor
xvei rule add tor geosite:openai
xvei rule add block geosite:category-ads-all
xvei template russia --tunnel warp        # RU напрямую, остальное через WARP
xvei remove-inbound hy2                    # остановит и удалит Hysteria2, остальное не тронет
xvei site game2048                         # отдавать на домене игру 2048
xvei site proxy gnu                        # реверс-прокси www.gnu.org
```

Каждая команда, меняющая состояние, сама выполняет сборку → `xray -test` →
подмену → перезапуск.

Вместе с сертификатом ставится deploy-hook certbot
(`/etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh`): после каждого
продления Let's Encrypt он обновляет копию сертификата для Hysteria2 и
перезапускает `xray`, `nginx` и `hysteria2`.

## Где что лежит

| путь | содержимое |
|---|---|
| `/usr/local/etc/xray/xvei-state.json` | источник правды (root, `0600`) |
| `/usr/local/etc/xray/config.json` | сгенерированный конфиг Xray (`.bak` сохраняется) |
| `/etc/hysteria/config.yaml` | сгенерированный конфиг Hysteria2 |
| `~/xray_eis/<tag>.link` | клиентская ссылка на каждый inbound |
| `~/xray_eis/<tag>.json` | полный клиентский конфиг Xray на каждый inbound |

## Структура репозитория

```
xvei.sh            точка входа + bootstrap + разбор подкоманд
lib/*.sh           системная часть: пакеты, xray, nginx, сертификаты, hysteria2, warp, tor, apply, menu
pyengine/*.py      движок конфигурации (только stdlib): state, inbounds, outbounds, routing, sites, links, editor
assets/sites/*     автономные сайты-прикрытия (без внешних запросов)
```

## Клиенты

[v2rayNG](https://github.com/2dust/v2rayNG/releases/latest),
[NekoBox / nekoray](https://github.com/MatsuriDayo/nekoray/releases/latest),
[Hiddify](https://hiddify.com/). Для REALITY и XHTTP нужен свежий клиент.

## Совет по маршрутизации на клиенте

Шаблон страны уже кладёт правила «внутристрановое → напрямую» в
`~/xray_eis/<tag>.json`. Если приложение импортирует только ссылку `vless://`,
добавьте на клиенте правила direct вручную, например для России:

**IP:** `geoip:private`, `geoip:ru`
**Домены:** `geosite:private`, `geosite:category-ru`, `geosite:category-gov-ru`
