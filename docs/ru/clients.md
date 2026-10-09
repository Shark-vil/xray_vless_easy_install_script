# Клиенты

Приложения для подключения к серверу:
[v2rayNG](https://github.com/2dust/v2rayNG/releases/latest) (Android),
[NekoBox / nekoray](https://github.com/MatsuriDayo/nekoray/releases/latest)
(Windows, Linux),
[Hiddify](https://hiddify.com/) (все платформы). Берите свежую версию: она
нужна для REALITY и XHTTP. Для `hysteria2` — Hiddify, NekoBox или
официальный клиент `hysteria`; для `turnable` — клиент
[Turnable](https://github.com/TheAirBlow/Turnable/releases/latest).

!!! danger
    Клиентское приложение видит весь ваш трафик. Ставьте приложения только с
    их официальных страниц.

## Ссылки и QR-коды

```bash
xvei links                      # все ссылки
xvei qr vless_reality           # QR-код для сканирования телефоном
xvei client-config vless_tls    # полный конфиг Xray для приложений, которым нужен файл
```

У inbound с несколькими клиентами — ссылка на каждого;
`xvei qr <tag> <клиент>` выбирает нужного. Меню: `xvei` → `6) Links / QR codes`.

## Сайты своей страны напрямую с телефона

Местные сайты (банки, госуслуги) через VPN открываются медленно, а иногда
вообще не пускают. Клиентское приложение может отправлять их напрямую через
ваш обычный интернет. Это настраивается на телефоне, а не на сервере.

В конфиге из `xvei client-config` такие правила для выбранного шаблона уже
есть. Если вы импортируете только ссылку, добавьте их в приложении. Для России:

- **IP:** `geoip:private`, `geoip:ru`
- **Домены:** `geosite:private`, `geosite:category-ru`, `geosite:category-gov-ru`

### NekoBox по шагам

1. **Настройки → Настройки маршрутов**.

    ![Настройки маршрутов](../img/nekoray_route_1.png)

2. Вкладка **Базовые маршруты**.

    ![Базовые маршруты](../img/nekoray_route_2.png)

3. Впишите списки выше в столбец **Напрямую**.

    ![Списки Напрямую](../img/nekoray_route_3.png)

4. **Исходящий по умолчанию** оставьте `proxy` и нажмите **OK**.

    ![Исходящий по умолчанию](../img/nekoray_route_4.png)
