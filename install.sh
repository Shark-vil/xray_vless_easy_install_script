#!/bin/bash

XRAY_GIT_SCRIPT="https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
ROOT_GIT_REPO="https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master"
REPO_XRAY_CONFIG="$ROOT_GIT_REPO/config/xray/config.json"
REPO_NGINX_CONFIG="$ROOT_GIT_REPO/config/nginx/default"
REPO_XRAY_CONFIG_VLESS="$ROOT_GIT_REPO/config/xray/user/vless.json"
REPO_XRAY_CONFIG_VLESS_WS="$ROOT_GIT_REPO/config/xray/user/vless_ws.json"
NGINX_DEFAULT_CONFIG_SRC="/etc/nginx/sites-available/default"
NGINX_DEFAULT_CONFIG_LINK="/etc/nginx/sites-enabled/default"
NGINX_NEW_CONFIG="/etc/nginx/sites-enabled/default.conf"
XRAY_USER_CONFIG_DEST="/root/vless.json"
XRAY_USER_SHADOWSOCKS_PASS="/root/shadowsocks.pass"
XRAY_CONFIG_PATH="/usr/local/etc/xray/config.json"

print_log() {
  local message="$1"
  local prefix_color="\033[96m"
  local reset_color="\033[0m"
  local prefix="[Xray|INFO] "
  echo -e "${prefix_color}${prefix}${reset_color}${message}"
}

print_error() {
  local message="$1"
  local prefix_color="\033[91m"
  local reset_color="\033[0m"
  local prefix="[Xray|ERROR] "
  echo -e "${prefix_color}${prefix}${reset_color}${message}"
}

check_service() {
    if systemctl is-active --quiet $1; then
        print_log "The '$1' service is working correctly!"
    else
        print_error "The '$1' service is running with errors!"
    fi
}

apt_update() {
    print_log "Update packages"
    apt-get update
}

apt_install() {
    print_log "Insstall '$1' package"
    apt-get install -y $1
}

confirm_changes() {
    local prompt="$1"
    local response

    while true; do
        local green="\033[32m"
        local red="\033[31m"
        local reset="\033[0m"
        print_log "${prompt} (${green}Yes${reset}/${red}No${reset}): "
        read CONFIRM_RESPONSE < /dev/tty

        CONFIRM_RESPONSE=$(echo "$CONFIRM_RESPONSE" | tr '[:upper:]' '[:lower:]')

        case "$CONFIRM_RESPONSE" in
            d | y | yes)
                return 0
                ;;
            n | no)
                return 1
                ;;
            *)
                ;;
        esac
    done
}

is_number() {
    local value="$1"
    if [[ "$value" =~ ^-?[0-9]+$ ]]; then
        return 0;
    else
        return 1;
    fi
}

replace_text_in_file() {
    sed -i "s|%$1%|$2|g" "$3"
    print_log "SET $1=$2 IN $3"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --remove)
            systemctl stop nginx.service
            systemctl stop xray.service
            if [ -e $NGINX_NEW_CONFIG ]; then
                rm -f $NGINX_NEW_CONFIG
                print_log "Remove: '$NGINX_NEW_CONFIG'"
            fi
            if [ -e $XRAY_USER_SHADOWSOCKS_PASS ]; then
                rm -f $XRAY_USER_SHADOWSOCKS_PASS
                print_log "Remove: '$XRAY_USER_SHADOWSOCKS_PASS'"
            fi
            if [ -e $NGINX_DEFAULT_CONFIG_SRC ] && [ ! -e $NGINX_DEFAULT_CONFIG_LINK ]; then
                ln -s $NGINX_DEFAULT_CONFIG_SRC $NGINX_DEFAULT_CONFIG_LINK
                print_log "Link: '$NGINX_DEFAULT_CONFIG_LINK'"
            fi
            if [ -e $XRAY_USER_CONFIG_DEST ]; then
                rm -f $XRAY_USER_CONFIG_DEST
                print_log "Remove: '$XRAY_USER_CONFIG_DEST'"
            fi
            if [ -e $XRAY_CONFIG_PATH ]; then
                rm -f $XRAY_CONFIG_PATH
                print_log "Remove: '$XRAY_CONFIG_PATH'"
            fi
            print_log "Remove git script '$XRAY_GIT_SCRIPT'"
            bash -c "$(curl -L $XRAY_GIT_SCRIPT)" @ remove --purge
            systemctl start nginx.service
            print_log "Start nginx service"
            check_service "nginx"
            exit 0
            ;;
        *)
            exit 1
            ;;
    esac
    shift
done

apt_update
apt_install "curl"

if ! curl --head --silent --fail "$XRAY_GIT_SCRIPT" > /dev/null; then
  echo "File $XRAY_GIT_SCRIPT not found :("
  return 0
fi

apt_install "ca-certificates"
apt_install "wget"
apt_install "git"
apt_install "nginx"
apt_install "certbot"

print_log "Run git script '$XRAY_GIT_SCRIPT'"
bash -c "$(curl -L $XRAY_GIT_SCRIPT)" @ install -u root

systemctl stop nginx.service
systemctl stop xray.service

while true; do
    print_log "Print your REAL domain name (example: mysite.com):"
    read YOUR_DOMAIN < /dev/tty

    if confirm_changes "Is this the correct domain?"; then
        break
    fi

    print_error "$YOUR_DOMAIN domain not correct. Try again."
done

while true; do
    print_log "Print your REAL email (example: mymail@gmail.com):"
    read YOUR_EMAIL < /dev/tty

    if confirm_changes "Is this the correct mail?"; then
        break
    fi

    print_error "Mail not correct. Try again."
done

LETSENCRYPT_FULLCHAIN="/etc/letsencrypt/live/$YOUR_DOMAIN/fullchain.pem"
LETSENCRYPT_PRIVKEY="/etc/letsencrypt/live/$YOUR_DOMAIN/privkey.pem"

if [ -e $LETSENCRYPT_FULLCHAIN ] && [ -e $LETSENCRYPT_PRIVKEY ]; then
    print_log "SSL certificates are already installed"
else
    print_log "Installing SSL certificates"
    certbot certonly --standalone --non-interactive --agree-tos --email $YOUR_EMAIL -d $YOUR_DOMAIN
fi

LETSENCRYPT_DOMAIN_CONF="/etc/letsencrypt/renewal/$YOUR_DOMAIN.conf"
LETSENCRYPT_ADD_LINE="renew_hook = systemctl reload xray"

if ! grep -Fxq "$LETSENCRYPT_ADD_LINE" "$LETSENCRYPT_DOMAIN_CONF"; then
    echo "$LETSENCRYPT_ADD_LINE" >> "$LETSENCRYPT_DOMAIN_CONF"
fi

wget -O $XRAY_CONFIG_PATH $REPO_XRAY_CONFIG

while true; do
    print_log "Print shadowsocks port (default: 2121):"
    read XRAY_SHADOWSOCS_PORT < /dev/tty
    if ! is_number $XRAY_SHADOWSOCS_PORT; then
        XRAY_SHADOWSOCS_PORT="2121"
    fi
    if ss -tuln | grep -q ":$XRAY_SHADOWSOCS_PORT"; then
        print_error "The port $XRAY_SHADOWSOCS_PORT is already in use"
        XRAY_SHADOWSOCS_PORT="2121"
    fi
    if confirm_changes "Port: $XRAY_SHADOWSOCS_PORT. Is this the correct port?"; then
        break
    fi
done

XRAY_USER_PASSWORD="$(tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 18)"
XRAY_USER_PASSWORD_BASE64=$(echo -n "$XRAY_USER_PASSWORD" | base64)
XRAY_USER_UUID=$(cat /proc/sys/kernel/random/uuid)
XRAY_WS_PATH="$(tr -dc 'a-z' < /dev/urandom | head -c 24)"

replace_text_in_file "LETSENCRYPT_FULLCHAIN" $LETSENCRYPT_FULLCHAIN $XRAY_CONFIG_PATH
replace_text_in_file "LETSENCRYPT_PRIVKEY" $LETSENCRYPT_PRIVKEY $XRAY_CONFIG_PATH
replace_text_in_file "SHADOWSOCKS_PORT" $XRAY_SHADOWSOCS_PORT $XRAY_CONFIG_PATH
replace_text_in_file "PASSWORD" $XRAY_USER_PASSWORD_BASE64 $XRAY_CONFIG_PATH
replace_text_in_file "CLIENT_UUID" $XRAY_USER_UUID $XRAY_CONFIG_PATH
replace_text_in_file "CLIENT_MAIL" $YOUR_EMAIL $XRAY_CONFIG_PATH
replace_text_in_file "WEBSOCKET_PATH" $XRAY_WS_PATH $XRAY_CONFIG_PATH

print_log "Replace default nginx config"
if [ -e $NGINX_DEFAULT_CONFIG_LINK ]; then
    rm -f $NGINX_DEFAULT_CONFIG_LINK
fi
wget -O $NGINX_NEW_CONFIG $REPO_NGINX_CONFIG

print_log "Select VLESS type:"
print_log "1: Standard - direct connection to the server by domain"
print_log "2: WebSocket - connect to the server by domain, BUT using Cloudflare proxy"
while true; do
    read XRAY_SELECT_VLESS_TYPE_NUMBER < /dev/tty
    case "$XRAY_SELECT_VLESS_TYPE_NUMBER" in
        1)
            XRAY_SELECT_VLESS_TYPE="def"
            break
            ;;
        2)
            XRAY_SELECT_VLESS_TYPE="ws"
            break
            ;;
        *)
            ;;
    esac
done

if [ "$XRAY_SELECT_VLESS_TYPE" = "ws" ]; then
    XRAY_SELECT_USER_CONFIG=$REPO_XRAY_CONFIG_VLESS_WS
else
    XRAY_SELECT_USER_CONFIG=$REPO_XRAY_CONFIG_VLESS
fi

print_log "Select config: $XRAY_SELECT_USER_CONFIG"

wget -O $XRAY_USER_CONFIG_DEST $XRAY_SELECT_USER_CONFIG
replace_text_in_file "CLIENT_UUID" $XRAY_USER_UUID $XRAY_USER_CONFIG_DEST
replace_text_in_file "WEBSOCKET_PATH" $XRAY_WS_PATH $XRAY_USER_CONFIG_DEST
replace_text_in_file "DOMAIN_NAME" $YOUR_DOMAIN $XRAY_USER_CONFIG_DEST

journalctl --vacuum-time=1s -u xray
systemctl restart systemd-journald

systemctl start nginx.service
systemctl start xray.service
#rm -rf /var/log/journal/*

check_service "nginx"
check_service "xray"

if [ ! -e $XRAY_USER_SHADOWSOCKS_PASS ]; then
    touch $XRAY_USER_SHADOWSOCKS_PASS
fi
echo "$XRAY_USER_PASSWORD" > "$XRAY_USER_SHADOWSOCKS_PASS"

print_log "Your user vless config:"
print_log "---------------------"
print_log "> ! SAVE PASSWORD ! <"
print_log $XRAY_USER_PASSWORD
print_log "---------------------"
echo ""
cat $XRAY_USER_CONFIG_DEST
echo ""
print_log "---------------------"
print_log "Config path: $XRAY_USER_CONFIG_DEST"
print_log "If you need get info, print: cat $XRAY_USER_CONFIG_DEST"
print_log "---------------------"
print_log "Shadowsocks password path: $XRAY_USER_SHADOWSOCKS_PASS"
print_log "If you need get shadowsocks password, print: cat $XRAY_USER_SHADOWSOCKS_PASS"
print_log "---------------------"
print_log "@+@+@+@+@+@+@+@+@+@+@"
print_log "Allow installed!"
print_log "@+@+@+@+@+@+@+@+@+@+@"