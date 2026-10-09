# XVEI — простая установка и живой редактор Xray (+ Hysteria2)

## [Documentation in English](/README.md)

📖 **Сайт документации: <https://shark-vil.github.io/xray_vless_easy_install_script/ru/>**

XVEI ставит и настраивает [Xray-core](https://github.com/XTLS/Xray-install)
(и по желанию [Hysteria2](https://v2.hysteria.network/)), а затем позволяет
менять конфигурацию **без переустановки** — inbounds, WARP / TOR и свои
outbounds, правила и шаблоны маршрутизации, сайт-прикрытие. Каждое изменение
проверяется через `xray -test` до применения; если проверка не прошла, рабочий
конфиг не трогается. Уже настроенный на сервере Xray принимается как есть.

Все команды выполняйте от **root**. Поддерживаются: Ubuntu 20.04+, Debian 11+,
CentOS Stream 9 ([подробнее](ru/install.md#поддерживаемые-системы)).

## Установка

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

Другие способы (только скрипт, git-клон, сервер с уже установленным Xray):
[установка](ru/install.md).

## Использование

После установки скрипт доступен как команда `xvei`. Открыть меню:

```bash
xvei
```

Вывести клиентские ссылки:

```bash
xvei links
```

Все команды: [команды](ru/commands.md).

## Какой inbound

Рекомендуется в 2026: `vless-xhttp-reality` (домен не нужен) и `vless-tls`
(свой домен), плюс `hysteria2` как быстрый дополнительный вариант там, где
работает UDP. Все типы и их статус: [inbounds](ru/inbounds.md).

## Документация

| страница | содержание |
|---|---|
| [Первая установка](ru/getting-started.md) | первая установка по шагам, подключение клиента |
| [Установка](ru/install.md) | поддерживаемые системы, способы установки, приём существующего Xray |
| [Inbounds](ru/inbounds.md) | все типы inbounds, какой выбрать в 2026 |
| [Turnable](ru/turnable.md) | ⚠️ туннель через звонки VK: нестабильно, **раскрывает IP сервера** |
| [Outbounds и маршрутизация](ru/routing.md) | WARP / TOR, outbounds из ссылок, шаблоны, правила |
| [Сайт-прикрытие](ru/site.md) | что видит браузер на домене |
| [Команды](ru/commands.md) | полный список команд с примерами |
| [Как это работает](ru/architecture.md) | компоненты, применение изменений, общий порт 443, порядок правил |
| [Обновления, файрвол, файлы](ru/maintenance.md) | `check-updates`, файрвол, продление сертификата, где что лежит |
| [Решение проблем](ru/troubleshooting.md) | логи, частые ошибки и что делать |
| [Клиенты](ru/clients.md) | клиентские приложения, маршрутизация на клиенте |

## Клиенты

[v2rayNG](https://github.com/2dust/v2rayNG/releases/latest),
[NekoBox / nekoray](https://github.com/MatsuriDayo/nekoray/releases/latest),
[Hiddify](https://hiddify.com/) — подробнее в разделе [клиенты](ru/clients.md).

> [!CAUTION]
> Клиентское приложение видит весь ваш трафик. Используйте только приложения,
> которым доверяете, скачивайте их с официальных страниц и помните: любой
> исполняемый файл вы устанавливаете на свой страх и риск.
