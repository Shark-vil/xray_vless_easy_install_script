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
