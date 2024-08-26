# XRay Vless Easy Install Script

## This script uses another script internally:
### [XTLS/Xray-install](https://github.com/XTLS/Xray-install/raw/main/install-release.sh)

## How is this script different?
It will automatically install “Nginx”, and set up a configuration file for “**Shadowsocks + Vless + WebSocket Vless**”.

## Attention!
**You must buy, or find a free DOMAIN NAME (example.com)**

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

### Vless clinet config
```
/root/xray_eis/vless_client_config.json
/$HOME/xray_eis/vless_client_config.json
```

### Vless client connect string
```
/root/xray_eis/vless_client_link.txt
/$HOME/xray_eis/vless_client_link.txt
```

### Shadowsocks client connect string
```
/root/xray_eis/shadowsocks_client_link.txt
/$HOME/xray_eis/shadowsocks_client_link.txt
```

### Client shadowsocks password
```
/root/xray_eis/shadowsocks_password.txt
/$HOME/xray_eis/shadowsocks_password.txt
```

### FAQ
#### WebSocket does not work on the phone
Try using the normal config ( *Cloudflare proxy needs to be turned off!* )

#### What application can I use?
* [Nekoray](https://github.com/MatsuriDayo/nekoray)
* [Hiddify](https://hiddify.com/)
* * [Android](https://play.google.com/store/apps/details?id=app.hiddify.com)
* * [Windows](https://apps.microsoft.com/detail/9pdfnl3qv2s5)
* * [Other](https://app.hiddify.com/)
* [v2rayNG (GitHub)](https://github.com/2dust/v2rayNG)
* * [Android](https://play.google.com/store/apps/details?id=com.v2ray.ang)

**P.s. Personally, I'm having trouble with Hiddify on my Android device. I recommend using “v2rayNG”. On Windows - Hiddify works fine!**