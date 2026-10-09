# Решение проблем

## С чего начать

```bash
xvei status          # сводка и какие сервисы работают
xvei show-config     # конфиг Xray
xvei firewall status # какие порты закрыты
```

Если изменение что-то сломало, откатите его: `xvei backup restore 1`.

## Логи

| что | команда |
|---|---|
| Xray | `journalctl -u xray -n 50` |
| nginx (сайт-прикрытие) | `journalctl -u nginx -n 50` |
| Hysteria2 | `journalctl -u hysteria-server -n 50` |
| Turnable | `journalctl -u turnable -n 50` |
| TOR | `journalctl -u tor -n 50` |
| WARP | `docker logs warp-xray --tail 50` |
| сертификат | `/var/log/letsencrypt/letsencrypt.log` |

## Клиент не подключается

1. **Порты** — `xvei firewall status` и файрвол в панели провайдера (его xvei
   не видит).
2. **Старая ссылка** — после повторного добавления inbound ссылка меняется.
   Возьмите свежую: `xvei links`.
3. **Старое приложение** — для REALITY и XHTTP нужна свежая версия.
4. **Только VMess** — часы сервера должны быть точными:
   `timedatectl set-ntp true`.
5. **Только Trojan TCP** — в ссылке должен быть `alpn=http/1.1` (в ссылках от
   xvei он есть).

## «certbot failed; falling back to a self-signed certificate»

Let's Encrypt не смог проверить домен, а временный сертификат клиенты не
примут.

1. Домен должен указывать на этот сервер: `dig +short ваш.домен`.
2. Порт `80/tcp` должен быть открыт, в том числе в панели провайдера.
3. Затем выполните `xvei apply`.

## «the changed config failed validation»

Изменение не прошло проверку и не применено; Xray работает с прежним
конфигом. Причина выведена выше. Если вы правили `config.json` вручную,
ошибка может быть там:
`xray run -test -config /usr/local/etc/xray/config.json`.

## «xray did not come up; rolling back»

Конфиг верный, но Xray не запустился — обычно порт занят другой программой:
`journalctl -u xray -n 50`, `ss -tulpn`.

## Turnable

- **Капча** — откройте локальный адрес, который выводит клиент.
- **Перестал работать** — возможно, VK что-то поменял; `xvei check-updates`
  покажет новую версию Turnable.
- **Медленно** — VK ограничивает соединение примерно 250 КБ/с.

## Начать заново

```bash
xvei remove --all
```

Затем установите заново, как в разделе [первая установка](getting-started.md).
