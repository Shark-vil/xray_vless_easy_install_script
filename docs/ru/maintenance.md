# Обновления, файрвол, файлы

[🇬🇧 English version](../en/maintenance.md) · [← Главная](index.md)

## Обновления

`xvei check-updates` (в меню: `10) Check for updates`) показывает установленную
и последнюю версию каждого компонента и предлагает установить доступные
обновления:

| компонент | установлено | сравнивается с |
|---|---|---|
| xvei | установленный коммит | последний коммит `master` |
| xray | `xray version` | последний релиз [XTLS/Xray-core](https://github.com/XTLS/Xray-core/releases) |
| hysteria2 | `hysteria version` | последний релиз [apernet/hysteria](https://github.com/apernet/hysteria/releases) |
| geoip.dat / geosite.dat | sha256 файла | контрольные суммы последнего релиза [Loyalsoldier/v2ray-rules-dat](https://github.com/Loyalsoldier/v2ray-rules-dat/releases) |

Неустановленные компоненты пропускаются. Если обновлений несколько, можно
поставить все (`all`, по умолчанию), ни одного (`none`) или только часть —
перечислить имена из списка, например `geo` или `xray geo`. xvei обновляется
последним, после этого запустите `xvei` заново. В git-клоне xvei обновляется через `git pull`.

## Файрвол

xvei **никогда сам не включает, не сбрасывает и не ужесточает файрвол**:
неправильный default-deny может отрезать доступ по SSH (особенно если sshd
висит на нестандартном порту).

* Если **ufw** или **firewalld** уже включён и закрывает порты, нужные текущему
  конфигу (порты inbounds и `80/tcp` для Let's Encrypt), при каждом применении
  xvei покажет их и спросит, открыть ли. Это только *добавляет* разрешающие
  правила. Без терминала — просто предупреждение.
* `xvei firewall status` — какой файрвол активен, найденные SSH-порты и какие
  нужные порты открыты/закрыты.
* `xvei firewall open` — добавить разрешения для нужных портов (только если
  файрвол уже включён).
* `xvei firewall setup` — **опциональная** полная настройка: запретить все
  входящие, кроме SSH и портов xvei. SSH-порт определяется по `sshd -T`, по
  тому, что слушает sshd, и по текущей SSH-сессии. Сначала показывается весь
  план, можно добавить свои порты (например `2222/tcp 27015/udp`), и без явного
  «да» ничего не применяется. На Debian/Ubuntu — ufw (старые правила
  сохраняются, если не выбрать `ufw reset`), на CentOS — firewalld.

То же самое есть в меню: `xvei` → `9) Firewall`.

## Продление сертификата

Вместе с сертификатом ставится deploy-hook certbot
(`/etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh`): после каждого
продления Let's Encrypt он обновляет копию сертификата для Hysteria2 и
перезапускает `xray`, `nginx` и `hysteria2`. Pre/post-хуки
(`renewal-hooks/{pre,post}/xvei-free-port80.sh`) останавливают nginx на время
проверки, только если он занимает `:80`, и затем запускают его обратно.

## Удаление xvei без Xray

**Адаптированная установка** (Xray стоял до xvei): `xvei remove` (меню:
`11) Uninstall xvei`) Xray не трогает. Он удаляет только то, что xvei поставил
сам (WARP, TOR, Hysteria2, Turnable, свой vhost nginx, хуки certbot),
спрашивает, вернуть ли `config.json.xvei-orig`, и удаляет state xvei. Xray,
его сервис и сертификаты остаются. Затем удалите команду и код:

```bash
sed -i '/_renew-hook/d' /etc/letsencrypt/renewal/*.conf
rm -f /usr/local/bin/xvei
rm -rf /usr/local/lib/xvei      # или папка вашего git clone
```

**Обычная установка** (Xray ставил xvei): `xvei remove` удалит и Xray. Чтобы
удалить только xvei и оставить всё работающим как сейчас (Xray с текущим
`config.json`, nginx, WARP, TOR, Hysteria2), удалите файлы xvei вручную:

```bash
rm -f /usr/local/etc/xray/xvei-state.json /usr/local/etc/xray/xvei-state.json.bak
rm -rf /var/lib/xvei
rm -f /etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh
rm -f /etc/letsencrypt/renewal-hooks/{pre,post}/xvei-free-port80.sh
sed -i '/_renew-hook/d' /etc/letsencrypt/renewal/*.conf
rm -f /usr/local/bin/xvei
rm -rf /usr/local/lib/xvei      # или папка вашего git clone
rm -rf ~/xray_eis               # осталась от старых версий xvei, если есть
```

Без хуков certbot после продления сертификата перезапускайте Xray сами
(`systemctl restart xray`) или добавьте свой deploy-hook.

## Где что лежит

| путь | содержимое |
|---|---|
| `/usr/local/etc/xray/xvei-state.json` | источник правды (root, `0600`) |
| `/usr/local/etc/xray/config.json` | сгенерированный конфиг Xray (`.bak` сохраняется) |
| `/usr/local/etc/xray/config.json.xvei-orig` | принятая настройка: конфиг до xvei |
| `/etc/hysteria/config.yaml` | сгенерированный конфиг Hysteria2 |
| `/etc/nginx/sites-enabled/xvei.conf` (Debian/Ubuntu) или `/etc/nginx/conf.d/xvei.conf` (CentOS), `/var/www/xvei-site` | vhost фолбэка + сайт-прикрытие |
| `/etc/turnable/config.json`, `/usr/local/bin/turnable` | конфиг и программа сервера Turnable |

## Структура репозитория

```
xvei.sh            точка входа + bootstrap + разбор подкоманд
lib/*.sh           системная часть: пакеты, xray, nginx, сертификаты, hysteria2, warp, tor, apply, menu
pyengine/*.py      движок конфигурации (только stdlib): state, inbounds, outbounds, routing, sites, links, editor
assets/sites/*     автономные сайты-прикрытия (без внешних запросов)
```
