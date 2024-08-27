# XRay Vless Easy Install Script

## [Documentation in English](./README.md)

## Этот скрипт использует внутри себя другой скрипт:
### [XTLS/Xray-install](https://github.com/XTLS/Xray-install/raw/main/install-release.sh)

## Чем этот скрипт отличается?
Он автоматически установит "Nginx" и настроит конфигурационный файл для "**Shadowsocks + Vless + WebSocket Vless**"..

## Внимание!
**Вы должны купить или найти бесплатное ДОМЕННОЕ ИМЯ (example.com)**

P.s. [dnsexit](https://dnsexit.com/domains/free-second-level-domains/) - Похоже, этот сайт дает возможность зарегистрировать домен бесплатно. Правда, бесплатный период использования составляет 1 год.

## Аргументы:
* --help - Вывести справочную информацию
* --install - Установка Xray
* --install-expert - Режим установки для продвинутых пользователей. Позволяет настроить Shadowsocks и установить прокси WARP / TOR.
* --remove - Удаление Xray
* --reinstall - Переустановка всех конфигураций и сервисов
* --renew - Переустановка ТОЛЬКО конфигурационных файлов, без переустановки сервисов
* --vless-qr - Выводит QR-код Vless в терминал
* --shadowsocks-qr - Выводит QR-код Shadowsocks в терминал

## Как использовать?

### Выполните эти строки до запуска скриптов!
```bash
apt-get update
apt-get install curl
```

### Используйте удаленный скрипт
#### Строка для установки
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --install
```

#### Строка для продвинутой установки
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --install-expert
```

#### Строка для удаления
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --remove
```

#### Строка для переустановки
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --reinstall
```

#### Строка для обновления конфигурации
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --renew
```

#### Строка для получения QR-кода vless
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --vless-qr
```

#### Строка для получения QR-кода shadowsocks
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --shadowsocks-qr
```

### ИЛИ Скачайте скрипт
```bash
apy-get update
apt-get install wget
wget https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh
chmod +x xvei.sh
./xvei.sh
```

## Где хранятся файлы?

### XRay конфиг
```
/usr/local/etc/xray/config.json
```

#### Печать содержимого файла
```bash
cat /usr/local/etc/xray/config.json
```
```bash
echo $(cat /usr/local/etc/xray/config.json)
```

### Vless клиент-конфиг
```
/$HOME/xray_eis/vless_client_config.json
```

#### Печать содержимого файла
```bash
cat /$HOME/xray_eis/vless_client_config.json
```
```bash
echo $(cat /$HOME/xray_eis/vless_client_config.json)
```

### Vless клиентская строка подключения
```
/$HOME/xray_eis/vless_client_link.txt
```

#### Печать содержимого файла
```bash
cat /$HOME/xray_eis/vless_client_link.txt
```
```bash
echo $(cat /$HOME/xray_eis/vless_client_link.txt)
```

### Shadowsocks клиентская строка подключения
```
/$HOME/xray_eis/shadowsocks_client_link.txt
```

#### Печать содержимого файла
```bash
cat /$HOME/xray_eis/shadowsocks_client_link.txt
```
```bash
echo $(cat /$HOME/xray_eis/shadowsocks_client_link.txt)
```

### Пароль клиента shadowsocks
```
/$HOME/xray_eis/shadowsocks_password.txt
```

#### Печать содержимого файла
```bash
cat /$HOME/xray_eis/shadowsocks_password.txt
```
```bash
echo $(cat /$HOME/xray_eis/shadowsocks_password.txt)
```

## FAQ
* Я не могу подключиться к сессии.
* * Убедитесь, что ваш сервер не закрыт CDN (Например, Сloudflare Proxied). В этом случае вам придется использовать только Vless WebSocket или Shadowsocks соединение. Если домен возвращает реальный IP вашего сервера - вы можете использовать любой тип соединения.
---
* Я вставляю текст для подключения в приложение, но ничего не получается.
* * Некоторые приложения могут не поддерживать ссылки **vless://** и **ss://**. В этом случае необходимо использовать **полный конфигурационный файл**. Вы можете получить его, вызвав команду в терминале после установки:
```bash
echo $(cat /$HOME/xray_eis/vless_client_config.json)
```

## Какое приложение я могу использовать?
* [Nekoray (GitHub)](https://github.com/MatsuriDayo/nekoray/releases/latest) *I recommend it*
* [Qv2ray (GitHub)](https://github.com/Qv2ray/Qv2ray/releases/latest)
* [Hiddify](https://hiddify.com/) - Configuration files only! **vless://** & **ss://** may not process completely!
* * [Android](https://play.google.com/store/apps/details?id=app.hiddify.com)
* * [Windows](https://apps.microsoft.com/detail/9pdfnl3qv2s5)
* * [Other](https://app.hiddify.com/)
* [v2rayNG (GitHub)](https://github.com/2dust/v2rayNG/releases/latest) *I recommend it*
* * [Android](https://play.google.com/store/apps/details?id=com.v2ray.ang)

*P.s. Лично у меня возникают проблемы с **Hiddify** на моем устройстве **Android**. Я рекомендую использовать **v2rayNG**. На **Windows** - **Hiddify** работает отлично!*