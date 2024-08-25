#!/bin/bash

ROOT_GIT_REPO="https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master"
REPO_XRAY_CONFIG="$ROOT_GIT_REPO/config/xray/config.json"
REPO_NGINX_CONFIG="$ROOT_GIT_REPO/config/nginx/default"
REPO_XRAY_CONFIG_VLESS="$ROOT_GIT_REPO/config/xray/user/vless.json"
REPO_XRAY_CONFIG_VLESS_WS="$ROOT_GIT_REPO/config/xray/user/vless_ws.json"

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
    sed -i "s/%$1%/$2/g" "$3"
    print_log "SET $1=$2 IN $3"
}

check_service() {
    if systemctl list-units --type=service --all | grep -q "$1.service"; then
        return 0
    fi
    return 1
}

apt_update
apt_install "curl"

GIT_SCRIPT="https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
if ! curl --head --silent --fail "$GIT_SCRIPT" > /dev/null; then
  echo "File $GIT_SCRIPT not found :("
  return 0
fi

apt_install "ca-certificates"
apt_install "wget"
apt_install "git"
apt_install "nginx"
apt_install "certbot"

print_log "Run git script '$GIT_SCRIPT'"
bash -c "$(curl -L $GIT_SCRIPT)" @ install -u root

systemctl stop nginx.service
systemctl stop xray.service

XRAY_CONFIG_PATH="/usr/local/etc/xray/config.json"

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

wget -O $XRAY_CONFIG_PATH $REPO_XRAY_CONFIG

while true; do
    print_log "Print shadowsocks port (default: 22):"
    read XRAY_SHADOWSOCS_PORT < /dev/tty
    if ! is_number $XRAY_SHADOWSOCS_PORT; then
        XRAY_SHADOWSOCS_PORT="22"
    fi
    if confirm_changes "Port: $XRAY_SHADOWSOCS_PORT. Is this the correct port?"; then
        break
    fi
done

XRAY_USER_PASSWORD="$(head -c 100 </dev/urandom | tr -dc 'A-Za-z0-9' | head -c 16)"
XRAY_USER_PASSWORD_BASE64=$(echo -n "$XRAY_USER_PASSWORD" | base64)
XRAY_USER_UUID=$(cat /proc/sys/kernel/random/uuid)
XRAY_WS_PATH="$(head -c 100 </dev/urandom | tr -dc 'A-Za-z' | head -c 24)"
NGINX_DEFAULT_CONFIG="/etc/nginx/sites-enabled/default"

replace_text_in_file "SHADOWSOCKS_PORT" $XRAY_SHADOWSOCS_PORT $XRAY_CONFIG_PATH
replace_text_in_file "PASSWORD" $XRAY_USER_PASSWORD_BASE64 $XRAY_CONFIG_PATH
replace_text_in_file "CLIENT_UUID" $XRAY_USER_UUID $XRAY_CONFIG_PATH
replace_text_in_file "CLIENT_MAIL" $YOUR_EMAIL $XRAY_CONFIG_PATH
replace_text_in_file "WEBSOCKET_PATH" $XRAY_WS_PATH $XRAY_CONFIG_PATH

print_log "Replace default nginx config"
if [ -e $NGINX_DEFAULT_CONFIG ]; then
    rm -f $NGINX_DEFAULT_CONFIG
fi
wget -O "$NGINX_DEFAULT_CONFIG.conf" $REPO_NGINX_CONFIG

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
    XRAY_SELECT_USER_CONFIG="$XRAY_SELECT_USER_CONFIG_WS"
else
    XRAY_SELECT_USER_CONFIG="$XRAY_SELECT_USER_CONFIG"
fi

XRAY_USER_CONFIG_DEST="/root/vless.json"
wget -O $XRAY_USER_CONFIG_DEST $XRAY_SELECT_USER_CONFIG
replace_text_in_file "%CLIENT_UUID%" $XRAY_USER_UUID $XRAY_USER_CONFIG_DEST
replace_text_in_file "%WEBSOCKET_PATH%" $XRAY_WS_PATH $XRAY_USER_CONFIG_DEST
replace_text_in_file "%YOUR_DOMAIN%" $YOUR_DOMAIN $XRAY_USER_CONFIG_DEST

systemctl start nginx.service
systemctl start xray.service

print_log "Your user vless config:"
print_log "----------------------"
cat $XRAY_USER_CONFIG_DEST
print_log "----------------------"

print_log "Config path: $XRAY_USER_CONFIG_DEST"
print_log "If you need get info, print: cat $XRAY_USER_CONFIG_DEST"

print_log "@+@+@+@+@+@+@+@+@+@+@"
print_log "Allow installed!"
print_log "@+@+@+@+@+@+@+@+@+@+@"