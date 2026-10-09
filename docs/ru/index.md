# XVEI

**Простой менеджер настройки Xray-сервера.**

[🇬🇧 English version](../en/index.md) · [GitHub](https://github.com/Shark-vil/xray_vless_easy_install_script)

XVEI ставит [Xray-core](https://github.com/XTLS/Xray-core) на Linux-сервер (по
желанию вместе с [Hysteria2](https://v2.hysteria.network/)) и остаётся
редактором: inbounds, туннели, маршрутизация и сайт-прикрытие меняются одной
командой или из меню, без переустановки. Каждое изменение проверяется через
`xray -test` до применения; если проверка не прошла, рабочий конфиг не
трогается.

## Что умеет

- **Inbounds** — VLESS (REALITY, Vision, XHTTP, WebSocket), Trojan, VMess,
  Shadowsocks, Hysteria2 и экспериментальный Turnable. Несколько из них делят
  порт 443. См. [inbounds](inbounds.md).
- **Второй прыжок** — Cloudflare WARP, TOR или любой свой сервер из
  share-ссылки (`vless://`, `vmess://`, `trojan://`, `ss://`, `socks5://`,
  `http://`). См. [маршрутизацию](routing.md).
- **Маршрутизация** — шаблоны стран, которые никогда не отправляют
  внутристрановой трафик с IP сервера, шаблон «популярное напрямую» и
  редактируемые списки правил.
- **Сайт-прикрытие** — что видит браузер на вашем домене: окно входа,
  статический сайт или реверс-прокси. См. [сайт-прикрытие](site.md).
- **Клиентские ссылки** — share-ссылки, QR-коды и полные клиентские конфиги
  для каждого inbound.
- **Уже настроенные серверы** — существующий Xray принимается как есть, без
  изменений. См. [установку](install.md#сервер-с-уже-установленным-xray).
- **Обслуживание** — проверка обновлений, необязательная настройка файрвола,
  автоматическое продление сертификата. См. [обслуживание](maintenance.md).

## Быстрый старт

Поддерживаемые системы: Ubuntu 20.04+, Debian 11+, CentOS Stream 9. Запуск от
**root**.

Ubuntu / Debian:

```bash
apt-get update && apt-get -y install curl
```

CentOS:

```bash
dnf -y install curl tar
```

Установка и запуск мастера:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) install
```

Мастер установки пошагово разобран в разделе [первая установка](getting-started.md).

## Куда дальше

| Я хочу… | страница |
|---|---|
| установить впервые и подключить телефон | [Первая установка](getting-started.md) |
| выбрать протокол | [Inbounds](inbounds.md) |
| пустить часть сайтов через другой сервер | [Outbounds и маршрутизация](routing.md) |
| найти команду | [Команды](commands.md) |
| понять, что происходит на сервере | [Как это работает](architecture.md) |
| починить то, что не работает | [Решение проблем](troubleshooting.md) |
| выбрать клиентское приложение | [Клиенты](clients.md) |
