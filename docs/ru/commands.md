# Команды

`xvei` без аргументов открывает меню. Всё, что есть в меню, доступно и
командами.

## Настройка

```
xvei install                    мастер первичной установки
xvei apply                      перепроверить сертификат и сервисы, перезапустить
xvei set-meta --domain D --email E
```

## Inbounds и ссылки

```
xvei add-inbound <тип> [--port N] [--dest САЙТ] [--method ШИФР] [--tag T]
xvei remove-inbound <tag>
xvei links [tag]                все клиентские ссылки
xvei qr <tag> [клиент]          QR-код (клиент: имя или номер)
xvei client-config <tag>        полный конфиг Xray для клиентского приложения
```

Типы: `vless-tls`, `vless-ws`, `vless-xhttp-reality`, `vless-xhttp-tls`,
`trojan-tcp`, `trojan-ws`, `vmess-ws`, `shadowsocks`, `hysteria2`, `turnable` —
см. [inbounds](inbounds.md).

## Outbounds и маршрутизация

```
xvei add-outbound warp | tor | 'ССЫЛКА' [--tag T]
xvei remove-outbound <warp|tor|tag>
xvei rule add|remove <outbound> <матчер ...>
xvei rule list [outbound]       все правила с номерами
xvei rule delete <N>
xvei template russia|iran|china --exit <outbound> [--direct | --tunnel <outbound>]
xvei template popular --tunnel <outbound>
xvei template none [--direct | --tunnel <outbound>]
xvei site [auth | blank | 404 | <заготовка> | proxy <url>]
```

См. [маршрутизацию](routing.md) и [сайт-прикрытие](site.md).

## Обслуживание

```
xvei status                     сводка и сервисы
xvei show-config                config.json в читаемом виде
xvei backup [list [стр]]        резервные копии, по 10 на страницу
xvei backup create [заметка]    сделать копию сейчас
xvei backup show|diff <N>       посмотреть копию / сравнить с текущим конфигом
xvei backup restore <N>         откатиться
xvei backup delete <N>
xvei backup keep [N]            сколько хранить (по умолчанию 20, 0 = выкл.)
xvei firewall [status | open | setup]
xvei check-updates
xvei update-geo                 обновить списки сайтов и стран
xvei self-update                обновить только xvei
xvei remove [--all [--packages]] [--yes]
```

См. [обслуживание](maintenance.md).

## Примеры

```bash
xvei add-inbound vless-xhttp-reality --dest www.samsung.com
xvei add-outbound tor
xvei rule add tor geosite:openai
xvei template russia --exit warp --direct
xvei site game2048
xvei backup restore 1      # отменить последнее изменение
```
