# Обновления, файрвол, файлы

[🇬🇧 English version](../en/maintenance.md) · [← Главная](index.md)

## Обновления

`xvei check-updates` (в меню: `10) Updates`) показывает установленную
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

## Резервные копии и откат

Перед каждым изменением через xvei (inbounds, outbounds, правила, шаблон,
сайт, домен) и перед откатом xvei сохраняет `config.json` в точности как есть
(вместе с комментариями) и свой state в `/usr/local/etc/xray/xvei-backups/`.
Копия, совпадающая с последней, повторно не создаётся. Ручная правка
`config.json` попадёт в копию перед следующим изменением через xvei; чтобы
сохранить конфиг до ручной правки, сначала выполните
`xvei backup create "заметка"`.

Меню: `xvei` → `11) Backups` — список по 10 на страницу (`n` / `p` —
листать), новые сверху. Откройте копию, чтобы посмотреть её `config.json`,
увидеть, что изменит откат (разница с текущим конфигом), откатиться или
удалить её; `c` — сделать копию сейчас, `k` — сколько копий хранить.

```bash
xvei backup                 # список (xvei backup list 2 — вторая страница)
xvei backup create "перед тестами"
xvei backup diff 3          # что изменит откат к копии 3
xvei backup restore 3       # спросит подтверждение; текущий конфиг сохраняется перед откатом
xvei backup keep 50         # хранить 50; 0 выключает автоматические копии
```

Откат применяется как любое изменение: сначала `xray -test`, и если проверка
не прошла, рабочий конфиг остаётся как был. Старые копии сверх лимита (по
умолчанию 20) удаляются. С `keep 0` автоматически ничего не сохраняется и не
удаляется; `xvei backup create` при этом работает.

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

## Удаление

`xvei remove` (в меню: `12) Uninstall xvei`) удаляет только xvei; `xvei
remove --all` — вместе со всем, что он настроил. В обоих случаях сначала
показывается полный список, и без подтверждения ничего не удаляется (ответ по
умолчанию — «нет»):

1. **Только xvei** (`xvei remove`, по умолчанию) — сама панель: её код
   (`/usr/local/lib/xvei`), команда `xvei`, state, метки, клиентские файлы
   старых версий (`~/xray_eis`). Xray с текущим `config.json`, nginx и сайт,
   WARP, TOR, Hysteria2, Turnable, сертификаты и правила файрвола продолжают
   работать как есть. Хук certbot, который вызывал xvei, заменяется
   самостоятельным `renewal-hooks/deploy/restart-xray.sh`, так что продлённые
   сертификаты по-прежнему подхватываются.
2. **xvei и всё, что он настроил** (`xvei remove --all`) — при обычной
   установке ещё и Xray (вместе с `/usr/local/etc/xray`), Hysteria2, Turnable,
   контейнер WARP, TOR, сайт xvei в nginx и хуки certbot. При принятой
   (adopted) установке — только то, что добавил xvei; Xray остаётся, и xvei
   спросит, вернуть ли `config.json.xvei-orig`. После этого xvei предлагает
   удалить пакеты, которые ставил сам (nginx, certbot, tor, qrencode, docker —
   docker, только если не осталось чужих контейнеров); `curl`, `tar`,
   `openssl`, Python и файрвол не удаляются никогда. Пакеты учитываются с этой
   версии: то, что ставил более старый xvei, не предлагается.

Сертификаты в `/etc/letsencrypt` остаются в обоих случаях. Без терминала
(в скриптах) подтверждение передаётся опцией:
`xvei remove --yes`, `xvei remove --all --yes [--packages]`. Git-клон
не удаляется — удалите его папку сами.

## Где что лежит

| путь | содержимое |
|---|---|
| `/usr/local/etc/xray/config.json` | конфиг Xray, источник правды; правится вручную или через xvei (`.bak` сохраняется) |
| `/usr/local/etc/xray/xvei-backups/` | резервные копии config.json + state (`xvei backup`) |
| `/usr/local/etc/xray/xvei-state.json` | то, чего нет в config.json: домен, сертификат, сайт, Hysteria2 / Turnable (root, `0600`) |
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
