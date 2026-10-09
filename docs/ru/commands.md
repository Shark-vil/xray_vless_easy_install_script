# Команды

[🇬🇧 English version](../en/commands.md) · [← Главная](index.md)

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
xvei rule list           все правила; правила принятого конфига пронумерованы
xvei rule delete <N>     удалить правило N принятого конфига
xvei template <russia|iran|china> --exit <warp|tor|block|TAG> [--tunnel <warp|tor|TAG> | --direct]
xvei template popular --tunnel <warp|tor|TAG>
xvei template none [--tunnel <warp|tor|TAG> | --direct | --keep]
xvei site [list | auth | blank | 404 | <заготовка> | proxy <url|preset>]

xvei links [tag]         вывести клиентские ссылки
xvei qr <tag> [клиент]   QR-код для одного inbound (клиент: имя или номер)
xvei client-config <tag> полный клиентский конфиг Xray (с правилами маршрутизации)
xvei status              сервисы и активный шаблон
xvei show-config [файл]  вывести config.json в читаемом виде (JSON5, комментарии сохраняются)
xvei firewall [status | open | setup]   см. maintenance.md, «Файрвол»
xvei set-meta [--domain D --email E ...]
xvei check-updates       проверить обновления xvei / xray / hysteria2 / geo-данных
xvei update-geo          обновить geoip/geosite (необязательно; их ставит установщик xray)
xvei self-update         перекачать дерево скриптов
xvei remove [--all [--packages]] [--yes]
                         удалить только xvei; --all: вместе со всем, что он настроил; спрашивает подтверждение
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

## Как применяются изменения

Вся конфигурация хранится в одном файле состояния
(`/usr/local/etc/xray/xvei-state.json`). Небольшой движок на Python (только
стандартная библиотека, без сторонних пакетов) заново собирает `config.json`,
проверяет его через `xray -test` и только после этого подменяет боевой конфиг и
перезапускает сервисы. Если проверка не прошла — рабочий конфиг не трогается.

Каждая команда, меняющая состояние, сама выполняет сборку → `xray -test` →
подмену → перезапуск.
