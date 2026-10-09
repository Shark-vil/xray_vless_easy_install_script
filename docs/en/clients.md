# Clients

[🇷🇺 Русская версия](../ru/clients.md) · [← Home](index.md)

[v2rayNG](https://github.com/2dust/v2rayNG/releases/latest),
[NekoBox / nekoray](https://github.com/MatsuriDayo/nekoray/releases/latest),
[Hiddify](https://hiddify.com/). REALITY and XHTTP need a reasonably recent
client build; the `hysteria2` inbound needs a Hysteria2-capable client
(Hiddify, NekoBox, the official `hysteria` client).

[Turnable](https://github.com/TheAirBlow/Turnable/releases/latest) — client for the `turnable` inbound (Linux,
Windows, macOS, Android via Termux).

> [!CAUTION]
> A client app sees all of your traffic. Use only apps you trust, download
> them from their official pages, and keep in mind that every executable you
> install is your own decision and your own risk.

`xvei links` prints the share URIs; `xvei qr <tag>` shows a scannable code.
Apps that cannot import a `vless://` / `ss://` link can load the full config
from `~/xray_eis/<tag>.json`.

## Client-side routing tip

This is about local split tunnelling on the **client device** (its own ISP
instead of the VPN) — it has nothing to do with the server and does not expose
its IP. The template already puts such "in-country / popular → direct" rules
into `~/xray_eis/<tag>.json`. If an app imports only the `vless://` link, add
direct rules on the client by hand, for example for Russia:

**IP:** `geoip:private`, `geoip:ru`
**Domains:** `geosite:private`, `geosite:category-ru`, `geosite:category-gov-ru`

### NekoBox step by step

The screenshots show NekoBox with the Russian interface.

1. Open **Settings → Routing settings**.

   ![Routing settings](../img/nekoray_route_1.png)

2. Open the **Basic routes** tab.

   ![Basic routes](../img/nekoray_route_2.png)

3. In the **Direct** column put the IP and domain lists from above (more
   services of your country can be added the same way).

   ![Direct lists](../img/nekoray_route_3.png)

4. Keep **Default outbound** set to `proxy` and press **OK**.

   ![Default outbound](../img/nekoray_route_4.png)
