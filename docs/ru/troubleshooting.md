# Решение проблем

[🇬🇧 English version](../en/troubleshooting.md) · [← Главная](index.md)

## Первые проверки

Сервисы и активный шаблон:

```bash
xvei status
```

Текущий конфиг Xray в читаемом виде:

```bash
xvei show-config
```

Какие порты закрывает файрвол на сервере:

```bash
xvei firewall status
```

## Логи

| компонент | команда |
|---|---|
| Xray | `journalctl -u xray -n 50` |
| nginx (сайт-прикрытие) | `journalctl -u nginx -n 50` |
| Hysteria2 | `journalctl -u hysteria-server -n 50` |
| Turnable | `journalctl -u turnable -n 50` |
| TOR | `journalctl -u tor -n 50` (на Debian/Ubuntu ещё `tor@default`) |
| WARP | `docker logs warp-xray --tail 50` |
| сертификат | `/var/log/letsencrypt/letsencrypt.log` |

## Клиенты не подключаются

1. **Порты.** Проверьте `xvei firewall status`. Проверьте и файрвол в панели
   облачного провайдера — xvei его не видит и не меняет.
2. **Актуальные ссылки.** Ссылки меняются, когда inbound добавляют заново.
   Выведите их снова через `xvei links` и импортируйте ещё раз.
3. **Версия клиента.** REALITY и XHTTP требуют свежую сборку клиента.
4. **Время на сервере** (только VMess). VMess не работает, если часы сервера
   расходятся больше чем на 120 секунд. Проверьте `timedatectl`; включите
   синхронизацию: `timedatectl set-ntp true`.
5. **Trojan по TCP** (`trojan-tcp`). Клиент должен использовать ALPN
   `http/1.1` — он есть в сгенерированной ссылке; если ссылку набирали вручную,
   добавьте `alpn=http/1.1`.

## «certbot failed; falling back to a self-signed certificate»

Let's Encrypt не смог проверить домен. Самоподписанному сертификату клиенты не
доверяют, поэтому TLS-inbounds не заработают, пока это не исправлено.

1. A-запись домена должна указывать на этот сервер — проверьте через
   `dig +short ваш.домен` или `ping ваш.домен`.
2. Порт `80/tcp` должен быть доступен из интернета на время проверки — в
   файрволе сервера и в панели провайдера.
3. Затем выполните `xvei apply` — сертификат будет запрошен снова.

## «generated xray config failed validation; live config untouched»

Изменение сохранено в состоянии, но не применено; Xray работает со старым
конфигом. Ошибка `xray -test` выведена над этим сообщением. Чтобы вернуться к
предыдущему состоянию:

```bash
cp /usr/local/etc/xray/xvei-state.json.bak /usr/local/etc/xray/xvei-state.json
```

```bash
xvei apply
```

## «xray did not come up; rolling back to previous config»

Новый конфиг прошёл проверку, но Xray не запустился — обычно порт уже занят
другой программой. Смотрите `journalctl -u xray -n 50`; список занятых портов —
`ss -tulpn`.

## «config.json was changed outside xvei»

`config.json` правили вручную после последней записи xvei. Применение заменит
его (текущий файл сохраняется как `config.json.bak`). Чтобы не потерять ручные
изменения, внесите их через xvei (inbounds, outbounds, правила) и примените
снова.

## Turnable

Сначала прочитайте [предупреждения](turnable.md): способ нестабилен по своей
природе.

- **Клиент просит капчу** — откройте локальный адрес, который он выводит, и
  следуйте инструкции.
- **Перестало работать у всех** — возможно, VK изменил доступ к звонкам;
  проверьте, нет ли новой версии Turnable (`xvei check-updates` покажет).
- **Медленно** — VK ограничивает каждое соединение примерно 250 KB/s.

## Начать заново

Удалить всё, что поставил xvei (на принятом сервере — только то, что добавил
xvei):

```bash
xvei remove
```

Затем установите заново, как в разделе [первая установка](getting-started.md).
