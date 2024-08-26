# XRay Vless Easy Install Script

## [Документация на русском](./RU.md)

## This script uses another script internally:
### [XTLS/Xray-install](https://github.com/XTLS/Xray-install/raw/main/install-release.sh)

## How is this script different?
It will automatically install “Nginx”, and set up a configuration file for “**Shadowsocks + Vless + WebSocket Vless**”.

## Attention!
**You must buy, or find a free DOMAIN NAME (example.com)**

P.s. [dnsexit](https://dnsexit.com/domains/free-second-level-domains/) - It seems this site gives you the opportunity to register a domain for free. It is true that the free period of use is 1 year.

## Arguments:
* --help - Print help info
* --install - Installing Xray
* --remove - Deletes Xray
* --reinstall - Reinstalls all configs and services
* --renew - Reinstalls ONLY configuration files, without reinstalling services
* --vless-qr - Outputs the Vless connection code to the terminal
* --shadowsocks-qr - Outputs the Shadowsocks connection code to the terminal

## How use?

### Use remote script
#### String to install
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --install
```

#### String to remove
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --remove
```

#### String to reinstall
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --reinstall
```

#### String to renew config
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --renew
```

#### String to get vless QR code
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --vless-qr
```

#### String to get shadowsocks QR code
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh) --shadowsocks-qr
```

### OR Download script
```bash
apy-get update
apt-get install wget
wget https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/xvei.sh
chmod +x xvei.sh
./xvei.sh
```

## Where are the files stored?

### XRay config
```
/usr/local/etc/xray/config.json
```

#### Print file content
```bash
cat /usr/local/etc/xray/config.json
```
```bash
echo $(cat /usr/local/etc/xray/config.json)
```

### Vless clinet config
```
/$HOME/xray_eis/vless_client_config.json
```

#### Print file content
```bash
cat /$HOME/xray_eis/vless_client_config.json
```
```bash
echo $(cat /$HOME/xray_eis/vless_client_config.json)
```

### Vless client connect string
```
/$HOME/xray_eis/vless_client_link.txt
```

#### Print file content
```bash
cat /$HOME/xray_eis/vless_client_link.txt
```
```bash
echo $(cat /$HOME/xray_eis/vless_client_link.txt)
```

### Shadowsocks client connect string
```
/$HOME/xray_eis/shadowsocks_client_link.txt
```

#### Print file content
```bash
cat /$HOME/xray_eis/shadowsocks_client_link.txt
```
```bash
echo $(cat /$HOME/xray_eis/shadowsocks_client_link.txt)
```

### Client shadowsocks password
```
/$HOME/xray_eis/shadowsocks_password.txt
```

#### Print file content
```bash
cat /$HOME/xray_eis/shadowsocks_password.txt
```
```bash
echo $(cat /$HOME/xray_eis/shadowsocks_password.txt)
```

## FAQ
* I can't connect to the session.
* * Make sure your server is not closed by a CDN (For example: Сloudflare Proxied). In this case you will only have to use Vless WebSocket or Shadowsocks connection. If the domain returns the real IP of your server - you can use any type of connection.
---
* I paste the text to connect into the app, but nothing works.
* * Some applications may not support **vless://** and **ss://** references. In this case, you will need to use the **full configuration file**. You can get it by invoking the command in the terminal after installation:
```bash
echo $(cat /$HOME/xray_eis/vless_client_config.json)
```

## What application can I use?
* [Nekoray (GitHub)](https://github.com/MatsuriDayo/nekoray/releases/latest) *I recommend it*
* [Qv2ray (GitHub)](https://github.com/Qv2ray/Qv2ray/releases/latest)
* [Hiddify](https://hiddify.com/) - Configuration files only! **vless://** & **ss://** may not process completely!
* * [Android](https://play.google.com/store/apps/details?id=app.hiddify.com)
* * [Windows](https://apps.microsoft.com/detail/9pdfnl3qv2s5)
* * [Other](https://app.hiddify.com/)
* [v2rayNG (GitHub)](https://github.com/2dust/v2rayNG/releases/latest) *I recommend it*
* * [Android](https://play.google.com/store/apps/details?id=com.v2ray.ang)

*P.s. Personally, I'm having trouble with **Hiddify** on my **Android** device. I recommend using **v2rayNG**. On **Windows** - **Hiddify** works fine!*