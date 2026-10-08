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

Добавленный outbound получает тег (`vless1`, `socks1`, … или `--tag`). Тег
используется как группа правил, как туннель шаблона (`--tunnel <тег>`) и как
выход для внутристранового трафика (`--exit <тег>`). Часть ссылки после `#`
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

### Шаблоны маршрутизации
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

### Редактируемые группы правил
`block`, `direct`, `warp`, `tor` и по одной на каждый добавленный outbound (его тег) — добавляйте/удаляйте матчеры
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

## Поддерживаемые системы

| система | статус |
|---|---|
| Ubuntu 20.04 / 22.04 / 24.04 | ✅ поддерживается |
| Debian 11 / 12 / 13 | ✅ поддерживается |
| CentOS Stream 9 | ✅ поддерживается |
| AlmaLinux / Rocky / RHEL 9, CentOS Stream 10, Fedora | ❓ неизвестно — не тестировалось, скорее всего работает |
| CentOS 7, CentOS Stream 8, прочие EL8 | ❌ не поддерживается (EOL, Python 3.6) |
| Alpine, системы без systemd | ❌ не поддерживается |

На любой другой системе установщик предупредит и спросит, продолжать ли.

Требования: root, systemd, Python ≥ 3.7 (ставится автоматически, если его
нет). Всё остальное (xray, certbot, nginx, hysteria2, docker для WARP, tor)
ставится по мере необходимости.

На CentOS установщик дополнительно:
* включает **EPEL** (certbot, tor и qrencode есть только там);
* кладёт vhost nginx в `/etc/nginx/conf.d/`, а не в `sites-enabled/`;
* при включённом SELinux помечает локальные порты nginx 8080/8081 как
  `http_port_t` и включает `httpd_can_network_connect` для сайта-прикрытия в
  режиме реверс-прокси;
* включает `certbot-renew.timer` (там он по умолчанию выключен).

## Установка

Нужен `curl`.

Ubuntu / Debian:

```bash
apt-get update && apt-get -y install curl
```

CentOS:

```bash
dnf -y install curl tar
```

### Полная установка

Скачивает скрипт и запускает мастер установки: Xray и всё, что в нём выбрано
(сертификат, nginx, Hysteria2, WARP, TOR).

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

### Только скрипт

Скачивает скрипт в `/usr/local/lib/xvei` и создаёт команду `xvei`.
Компоненты (Xray, сертификат, nginx и т.д.) не устанавливаются.

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) help
```

Запуск мастера установки:

```bash
xvei install
```

### Из git-клона

```bash
git clone https://github.com/Shark-vil/xray_vless_easy_install_script.git
cd xray_vless_easy_install_script
bash xvei.sh install
```

Команда `xvei` указывает на папку клона. Обновление — через `git pull`;
`xvei self-update` в этом режиме недоступен.

### Сервер с уже установленным Xray

Если Xray уже установлен и есть `/usr/local/etc/xray/config.json`, но xvei
никогда не настраивался, `xvei install` **принимает существующую настройку**:
ничего не устанавливается (кроме Python, если его нет), не перезаписывается и
не перезапускается. Конфиг читается как JSON5 (комментарии, висячие запятые) и
сохраняется как основа состояния xvei.

Дальше правки через xvei накладываются на этот конфиг:

* существующие inbounds, outbounds, правила и все остальные секции (`log`,
  `dns`, `api`, `stats`, `policy`, …) не меняются;
* первый существующий outbound остаётся первым и остаётся маршрутом по
  умолчанию;
* правила и шаблоны xvei ставятся перед существующими правилами;
* правило «всё остальное → …» не добавляется, пока режим выхода не выбран
  явно (`xvei template none --keep` возвращает исходное поведение);
* tor, контейнер WARP, Hysteria2 и nginx останавливаются или перенастраиваются,
  только если их поднял сам xvei.

Перед первой записью оригинал сохраняется как `config.json.xvei-orig` (вместе с
комментариями; в пересобранном файле их нет). Если `config.json` правили
вручную после записи xvei, xvei спросит перед перезаписью. `xvei remove`
удаляет только добавленное xvei и предлагает вернуть оригинал.

Не принимаются (ничего не меняется, выводится причина): Xray под управлением
панели (x-ui / 3x-ui), `xray.service`, который читает конфиг из другого пути
или использует `-confdir`.

### Как работает однострочник

`bash <(curl …)` скачивает только `xvei.sh`. Скрипт скачивает весь репозиторий
в `/usr/local/lib/xvei`, создаёт симлинк `/usr/local/bin/xvei` →
`/usr/local/lib/xvei/xvei.sh` и перезапускает себя с тем же аргументом. Без
аргумента открывается меню с предложением установки.

`xvei.sh` — файл репозитория, `xvei` — установленная команда:
`xvei install` равносильно `bash /usr/local/lib/xvei/xvei.sh install`.

## Команды

Скрипт вызывается командой `xvei`:

```
xvei                     интерактивное меню (или предложит установку)
xvei install             мастер первичной установки
xvei edit                интерактивное меню
xvei apply               пересобрать + проверить + перезапустить из текущего состояния

xvei add-inbound  <тип> [--port N] [--dest SNI] [--method M]
xvei remove-inbound <tag>
xvei add-outbound   <warp|tor|LINK ...> [--tag T]
xvei remove-outbound <warp|tor|TAG>
xvei rule <add|remove|list> <block|direct|warp|tor|TAG> [матчер ...]
xvei template <russia|iran|china> --exit <warp|tor|block|TAG> [--tunnel <warp|tor|TAG> | --direct]
xvei template popular --tunnel <warp|tor|TAG>
xvei template none [--tunnel <warp|tor|TAG> | --direct | --keep]
xvei site [list | auth | blank | 404 | <заготовка> | proxy <url|preset>]

xvei links [tag]         вывести клиентские ссылки
xvei qr <tag>            QR-код для одного inbound
xvei status              сервисы и активный шаблон
xvei show-config [файл]  вывести config.json в читаемом виде (JSON5, комментарии сохраняются)
xvei firewall [status | open | setup]   см. раздел «Файрвол» ниже
xvei set-meta [--domain D --email E ...]
xvei check-updates       проверить обновления xvei / xray / hysteria2 / geo-данных
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
xvei template russia --exit warp --direct  # RU-трафик через WARP, остальное напрямую
xvei template popular --tunnel tor         # популярные сайты напрямую, остальное через TOR
xvei remove-inbound hy2                    # остановит и удалит Hysteria2, остальное не тронет
xvei site game2048                         # отдавать на домене игру 2048
xvei site proxy gnu                        # реверс-прокси www.gnu.org
```

Каждая команда, меняющая состояние, сама выполняет сборку → `xray -test` →
подмену → перезапуск.

Вместе с сертификатом ставится deploy-hook certbot
(`/etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh`): после каждого
продления Let's Encrypt он обновляет копию сертификата для Hysteria2 и
перезапускает `xray`, `nginx` и `hysteria2`. Pre/post-хуки
(`renewal-hooks/{pre,post}/xvei-free-port80.sh`) останавливают nginx на время
проверки, только если он занимает `:80`, и затем запускают его обратно.

## Обновления

`xvei check-updates` (в меню: `10) Check for updates`) показывает установленную
и последнюю версию каждого компонента и предлагает установить доступные
обновления:

| компонент | установлено | сравнивается с |
|---|---|---|
| xvei | установленный коммит | последний коммит `master` |
| xray | `xray version` | последний релиз [XTLS/Xray-core](https://github.com/XTLS/Xray-core/releases) |
| hysteria2 | `hysteria version` | последний релиз [apernet/hysteria](https://github.com/apernet/hysteria/releases) |
| geoip.dat / geosite.dat | sha256 файла | контрольные суммы последнего релиза [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat/releases) |

Неустановленные компоненты пропускаются. xvei обновляется последним, после
этого запустите `xvei` заново. В git-клоне xvei обновляется через `git pull`.

## Файрвол

xvei **никогда сам не включает, не сбрасывает и не ужесточает файрвол**:
неправильный default-deny может отрезать доступ по SSH (особенно если sshd
висит на нестандартном порту).

* Если **ufw** или **firewalld** уже включён и закрывает порты, нужные текущему
  конфигу (порты inbounds и `80/tcp` для Let's Encrypt), при каждом применении
  xvei покажет их и спросит, открыть ли. Это только *добавляет* разрешающие
  правила. Без терминала — просто предупреждение.
* `xvei firewall status` — какой файрвол активен, найденные SSH-порты и какие
  нужные порты открыты/закрыты.
* `xvei firewall open` — добавить разрешения для нужных портов (только если
  файрвол уже включён).
* `xvei firewall setup` — **опциональная** полная настройка: запретить все
  входящие, кроме SSH и портов xvei. SSH-порт определяется по `sshd -T`, по
  тому, что слушает sshd, и по текущей SSH-сессии. Сначала показывается весь
  план, можно добавить свои порты (например `2222/tcp 27015/udp`), и без явного
  «да» ничего не применяется. На Debian/Ubuntu — ufw (старые правила
  сохраняются, если не выбрать `ufw reset`), на CentOS — firewalld.

То же самое есть в меню: `xvei` → `9) Firewall`.

## Где что лежит

| путь | содержимое |
|---|---|
| `/usr/local/etc/xray/xvei-state.json` | источник правды (root, `0600`) |
| `/usr/local/etc/xray/config.json` | сгенерированный конфиг Xray (`.bak` сохраняется) |
| `/usr/local/etc/xray/config.json.xvei-orig` | принятая настройка: конфиг до xvei |
| `/etc/hysteria/config.yaml` | сгенерированный конфиг Hysteria2 |
| `/etc/nginx/sites-enabled/xvei.conf` (Debian/Ubuntu) или `/etc/nginx/conf.d/xvei.conf` (CentOS), `/var/www/xvei-site` | vhost фолбэка + сайт-прикрытие |
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

Это про локальный сплит-туннелинг на **устройстве клиента** (свой ISP вместо
VPN) — с сервером он не связан и не палит его IP. Шаблон уже кладёт такие
правила «внутристрановое / популярное → напрямую» в `~/xray_eis/<tag>.json`.
Если приложение импортирует только ссылку `vless://`, добавьте на клиенте
правила direct вручную, например для России:

**IP:** `geoip:private`, `geoip:ru`
**Домены:** `geosite:private`, `geosite:category-ru`, `geosite:category-gov-ru`
