# Установка

[🇬🇧 English version](../en/install.md) · [← Главная](index.md)

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
не перезапускается. Конфиг читается как JSON5 (комментарии, висячие запятые).

Своей копии xvei не хранит: `config.json` остаётся источником правды и
читается при каждом запуске, поэтому всё, что правят в нём вручную, сразу
видно в меню и сохраняется при следующем изменении через xvei.

* **ссылки и QR-коды** для каждого inbound: VLESS / VMess / Trojan /
  Shadowsocks (TCP, WS, XHTTP, HTTPUpgrade, gRPC; TLS или REALITY), по одной на
  клиента, с именем из его `email`. Inbound, который слушает unix-сокет или
  localhost и доступен через `fallbacks` TLS-inbound (например, WS за VLESS TLS
  на `:443`), получает порт и TLS этого inbound. Для открытых наружу SOCKS /
  HTTP — ссылки `socks5://` / `http://`, для SOCKS ещё `t.me/socks` для
  Telegram. `xvei qr <tag> [клиент]`;
* **outbounds** можно использовать как цель правил и как туннель или выход
  шаблона (например, существующий `warp_proxy` или SOCKS-прокси). Если в
  конфиге уже есть `warp_proxy` / `tor_proxy`, xvei не запускает рядом свой
  WARP / TOR;
* **правила маршрутизации** видны в том порядке, в котором их проверяет Xray
  (`xvei rule list`); домены / IP можно направить в любой outbound, любое
  правило — удалить (`xvei rule delete <N>`);
* WS / XHTTP / Trojan, добавленные через xvei, встают за `fallbacks`
  существующего TLS-inbound на `:443`, если он есть;
* inbounds и outbounds можно удалить (`xvei remove-inbound <tag>`,
  `xvei remove-outbound <tag>`); пока их использует правило, xvei откажет;
* первый outbound остаётся маршрутом по умолчанию; защитные правила и правило
  «всё остальное» не добавляются, пока выход не выбран явно;
* tor, контейнер WARP, Hysteria2 и nginx останавливаются или перенастраиваются,
  только если их поднял сам xvei.

Перед первым изменением файла через xvei оригинал сохраняется как
`config.json.xvei-orig` (вместе с комментариями; xvei пишет обычный JSON).
`xvei remove --all` удаляет только добавленное xvei и предлагает вернуть
оригинал.

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
