# Установка

## Поддерживаемые системы

| система | статус |
|---|---|
| Ubuntu 20.04 / 22.04 / 24.04 | ✅ поддерживается |
| Debian 11 / 12 / 13 | ✅ поддерживается |
| CentOS Stream 9 | ✅ поддерживается |
| AlmaLinux / Rocky / RHEL 9, CentOS Stream 10, Fedora | ❓ не проверялось, скорее всего работает |
| CentOS 7, CentOS Stream 8, другие EL8 | ❌ не поддерживается (срок поддержки истёк, Python 3.6) |
| Alpine, системы без systemd | ❌ не поддерживается |

На других системах установщик предупредит и спросит, продолжать ли.

Нужны root, systemd и Python 3.7+ (поставится, если его нет). Всё остальное —
Xray, certbot, nginx, Hysteria2, docker для WARP, tor — ставится, только когда
это требуется настройке.

На CentOS установщик ещё включает EPEL (там certbot, tor и qrencode),
разрешает nginx его локальные порты в SELinux и включает таймер продления
сертификата.

## Способы установки

Если нет `curl`, поставьте его: `apt-get update && apt-get -y install curl`
(Ubuntu / Debian) или `dnf -y install curl tar` (CentOS).

**Полная установка** — скрипт, Xray и мастер настройки:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

**Только скрипт** — кладёт скрипт в `/usr/local/lib/xvei` и создаёт команду
`xvei`; больше ничего не ставится, пока вы не запустите `xvei install`:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) help
```

**Из git-клона** — команда `xvei` будет указывать на клон, обновление через
`git pull`:

```bash
git clone https://github.com/Shark-vil/xray_vless_easy_install_script.git
cd xray_vless_easy_install_script
bash xvei.sh install
```

## Сервер с уже установленным Xray

Если на сервере уже есть Xray с `/usr/local/etc/xray/config.json`,
`xvei install` принимает его: ничего не ставится, не меняется и не
перезапускается.

xvei работает с этим `config.json` как он есть. Своей копии он не хранит,
поэтому всё, что вы меняете в файле вручную, сразу видно в xvei и остаётся
при изменениях через xvei. Можно:

- получить ссылки и QR-коды для существующих подключений, по одной на клиента;
- использовать существующие outbounds в правилах и шаблонах (если в конфиге
  уже есть свой `warp_proxy` или `tor_proxy`, xvei использует его, а не
  запускает свой);
- смотреть, добавлять и удалять правила маршрутизации;
- добавлять новые типы — WebSocket, XHTTP и Trojan встают за существующее
  TLS-подключение на порту 443;
- удалять inbounds и outbounds (пока их не использует правило).

nginx, WARP, TOR и Hysteria2 xvei останавливает или меняет, только если сам
их запустил. Перед первым изменением исходный конфиг сохраняется как
`config.json.xvei-orig` вместе с комментариями.

Не принимаются (ничего не меняется, причина выводится): Xray под управлением
панели (x-ui / 3x-ui) или `xray.service`, который читает конфиг из другого
пути или папки (`-confdir`).
