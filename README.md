# XRay Vless Easy Install Script

## This script uses another script internally:
### [XTLS/Xray-install](https://github.com/XTLS/Xray-install/raw/main/install-release.sh)

## How is this script different?
It will automatically install “Nginx”, and set up a configuration file for “**Shadowsocks + Vless + WebSocket Vless**”.

## Attention!
**You must buy, or find a free DOMAIN NAME (example.com)**

## String to install
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/install.sh)
```

## String to remove
```bash
bash <(curl -s https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master/install.sh) --remove
```

## Where are the files stored?

### XRay config
```
/usr/local/etc/xray/config.json
```

### User VLESS config
```
/root/vless.json
```

### User shadowsocks password
```
/root/shadowsocks.pass
```

### FAQ
* WebSocket does not work on the phone
* * Try using the normal config ( *Cloudflare proxy needs to be turned off!* )
* What application can I use?
* * [Nekoray](https://github.com/MatsuriDayo/nekoray), [Hiddify](https://hiddify.com/) and etc.