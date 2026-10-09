# Как это работает

## Части

```mermaid
flowchart LR
    user([меню / команда xvei]) --> bash[bash: lib/*.sh]
    bash --> engine[Python: pyengine/]
    engine <--> xcfg[(config.json)]
    engine <--> state[(xvei-state.json)]
    engine --> other[конфиги Hysteria2, Turnable, nginx]
    bash --> sys[пакеты, сертификаты, сервисы, файрвол, docker]
```

- **`config.json`** (`/usr/local/etc/xray/`) — конфиг Xray и главный источник
  правды. xvei читает его при каждом запуске, поэтому ручные правки видны
  сразу.
- **`xvei-state.json`** рядом хранит только то, чего нет в `config.json`:
  домен, сертификат, сайт-прикрытие, настройки Hysteria2 / Turnable и то, что
  xvei создал сам (чтобы не трогать чужой nginx или WARP).
- **Часть на Python** (только стандартная библиотека) меняет конфиг.
- **Часть на bash** делает системную работу: пакеты, сертификаты, nginx,
  сервисы, файрвол.

## Как применяется изменение

```mermaid
flowchart TD
    A[меню или команда] --> B[резервная копия config.json]
    B --> C[изменение копии config.json]
    C --> D[сертификат, nginx, WARP, TOR при необходимости]
    D --> E{xray -test для копии}
    E -- ошибка --> F[ничего не меняется]
    E -- успех --> G[замена config.json, перезапуск Xray]
    G --> H{Xray запустился?}
    H -- нет --> I[возврат предыдущего конфига]
    H -- да --> J[обновление Hysteria2, Turnable, nginx]
```

Изменение всегда начинается с `config.json` в том виде, в каком он лежит на
диске, поэтому ручные правки сохраняются.

## Один порт 443 на много inbounds

`vless-tls` занимает порт 443 и отвечает за шифрование. То, что не VLESS, он
передаёт дальше по пути запроса и протоколу:

```mermaid
flowchart LR
    C([клиент :443]) --> V[vless-tls]
    V -- "секретный путь" --> W[vless-ws / trojan-ws / vmess-ws / vless-xhttp-tls]
    V -- "HTTP/2" --> N2[сайт nginx :8081]
    V -- "всё остальное" --> T{trojan-tcp?}
    T -- да --> TR[trojan-tcp] -- не Trojan --> N1[сайт nginx :8080]
    T -- нет --> N1
```

Пути случайные, поэтому браузер всегда попадает на сайт-прикрытие. Внутренние
переходы не выходят за пределы сервера.

## Hysteria2 и Turnable

Это отдельные программы, которые передают трафик в локальный inbound Xray,
поэтому правила маршрутизации Xray действуют и на них:

```mermaid
flowchart LR
    H([клиент Hysteria2]) -- UDP --> HS[hysteria-server] --> S[Xray 127.0.0.1]
    T([клиент Turnable]) -- звонки VK --> TS[turnable] --> S
    S --> R[маршрутизация Xray]
```

Порядок правил маршрутизации описан в [маршрутизации](routing.md#порядок-правил).
