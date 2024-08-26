#!/bin/bash

XRAY_GIT_SCRIPT="https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
ROOT_GIT_REPO="https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master"
REPO_XRAY_CONFIG="$ROOT_GIT_REPO/config/xray/config.json"
REPO_NGINX_CONFIG="$ROOT_GIT_REPO/config/nginx/default"
REPO_XRAY_CONFIG_VLESS="$ROOT_GIT_REPO/config/xray/user/vless.json"
REPO_XRAY_CONFIG_VLESS_WS="$ROOT_GIT_REPO/config/xray/user/vless_ws.json"
REPO_XRAY_CONFIG_VLESS_LINK="$ROOT_GIT_REPO/config/xray/user/vless_link.txt"
REPO_XRAY_CONFIG_VLESS_LINK_WS="$ROOT_GIT_REPO/config/xray/user/vless_ws_link.txt"
REPO_XRAY_CONFIG_SHADOWSOCKS_LINK="$ROOT_GIT_REPO/config/xray/user/shadowsocks_link.txt"
NGINX_DEFAULT_CONFIG_SRC="/etc/nginx/sites-available/default"
NGINX_DEFAULT_CONFIG_LINK="/etc/nginx/sites-enabled/default"
NGINX_NEW_CONFIG="/etc/nginx/sites-enabled/default.conf"
CONFIG_DIST_PATH="$HOME/xray_eis"
CONFIG_VLESS_CLIENT_PATH="$CONFIG_DIST_PATH/vless_client_config.json"
CONFIG_VLESS_LINK_CLIENT_PATH="$CONFIG_DIST_PATH/vless_client_link.txt"
CONFIG_SHADOWSOCKS_PASSWORD_PATH="$CONFIG_DIST_PATH/shadowsocks_password.txt"
CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH="$CONFIG_DIST_PATH/shadowsocks_client_link.txt"
XRAY_CONFIG_PATH="/usr/local/etc/xray/config.json"
XRAY_RENEW_CONFIG="0"

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
        local confirm_value

        print_log "${prompt} (${green}Yes${reset}/${red}No${reset}): "
        read confirm_value < /dev/tty

        confirm_value=$(echo "$confirm_value" | tr '[:upper:]' '[:lower:]')

        case "$confirm_value" in
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

read_domain() {
    while true; do
        print_log "Print your REAL domain name (example: mysite.com):"
        read -r VALUE_YOUR_DOMAIN < /dev/tty
        if confirm_changes "Is this the correct domain?"; then
            break
        fi
        print_error "Domain not correct. Try again."
    done
}

read_mail() {
    while true; do
        print_log "Print your REAL email (example: mymail@gmail.com):"
        read -r VALUE_YOUR_EMAIL < /dev/tty
        if confirm_changes "Is this the correct domain?"; then
            break
        fi
        print_error "Mail not correct. Try again."
    done
}

set_shadowsocks_port() {
    while true; do
        print_log "Print shadowsocks port (default: 2121):"
        read VALUE_XRAY_SHADOWSOCKS_PORT < /dev/tty
        if ! is_number $VALUE_XRAY_SHADOWSOCKS_PORT; then
            VALUE_XRAY_SHADOWSOCKS_PORT="2121"
        fi
        if ss -tuln | grep -q ":$VALUE_XRAY_SHADOWSOCKS_PORT"; then
            print_error "The port $VALUE_XRAY_SHADOWSOCKS_PORT is already in use"
            VALUE_XRAY_SHADOWSOCKS_PORT="2121"
        fi
        if confirm_changes "Port: $VALUE_XRAY_SHADOWSOCKS_PORT. Is this the correct port?"; then
            break
        fi
    done
}

letsencrypt_install_cert_from_domain() {
    local domain=$1
    local mail=$2

    VALUE_LETSENCRYPT_FULLCHAIN="/etc/letsencrypt/live/$domain/fullchain.pem"
    VALUE_LETSENCRYPT_PRIVKEY="/etc/letsencrypt/live/$domain/privkey.pem"

    if [ -e $VALUE_LETSENCRYPT_FULLCHAIN ] && [ -e $VALUE_LETSENCRYPT_PRIVKEY ]; then
        print_log "SSL certificates are already installed"
    else
        print_log "Installing SSL certificates"
        certbot certonly --standalone --non-interactive --agree-tos --email $mail -d $domain
    fi

    local letsencrypt_domain_conf="/etc/letsencrypt/renewal/$domain.conf"
    local letsencrypt_add_line="renew_hook = systemctl reload xray"

    if ! grep -Fxq "$letsencrypt_add_line" "$letsencrypt_domain_conf"; then
        echo "$letsencrypt_add_line" >> "$letsencrypt_domain_conf"
    fi
}

xray_update_config_template() {
    VALUE_XRAY_USER_PASSWORD="$(tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 18)"
    VALUE_XRAY_USER_PASSWORD_BASE64=$(echo -n "$VALUE_XRAY_USER_PASSWORD" | base64)
    VALUE_XRAY_USER_UUID=$(cat /proc/sys/kernel/random/uuid)
    VALUE_XRAY_WS_PATH="$(tr -dc 'a-z' < /dev/urandom | head -c 24)"

    replace_text_in_file "LETSENCRYPT_FULLCHAIN" $VALUE_LETSENCRYPT_FULLCHAIN $XRAY_CONFIG_PATH
    replace_text_in_file "LETSENCRYPT_PRIVKEY" $VALUE_LETSENCRYPT_PRIVKEY $XRAY_CONFIG_PATH
    replace_text_in_file "SHADOWSOCKS_PORT" $VALUE_XRAY_SHADOWSOCKS_PORT $XRAY_CONFIG_PATH
    replace_text_in_file "PASSWORD" $VALUE_XRAY_USER_PASSWORD_BASE64 $XRAY_CONFIG_PATH
    replace_text_in_file "CLIENT_UUID" $VALUE_XRAY_USER_UUID $XRAY_CONFIG_PATH
    replace_text_in_file "CLIENT_MAIL" $VALUE_YOUR_EMAIL $XRAY_CONFIG_PATH
    replace_text_in_file "WEBSOCKET_PATH" $VALUE_XRAY_WS_PATH $XRAY_CONFIG_PATH
}

nginx_update_default_config() {
    print_log "Replace default nginx config"
    if [ -e $NGINX_DEFAULT_CONFIG_LINK ]; then
        rm -f $NGINX_DEFAULT_CONFIG_LINK
    fi
    wget -O $NGINX_NEW_CONFIG $REPO_NGINX_CONFIG
}

xray_set_vless_config_type() {
    local select_type_number
    local select_type
    
    print_log "Select VLESS type:"
    print_log "1: Standard - direct connection to the server by domain"
    print_log "2: WebSocket - connect to the server by domain, BUT using Cloudflare proxy"
    
    while true; do
        read select_type_number < /dev/tty
        case "$select_type_number" in
            1)
                select_type="def"
                break
                ;;
            2)
                select_type="ws"
                break
                ;;
            *)
                ;;
        esac
    done

    if [ "$select_type" = "ws" ]; then
        VALUE_XRAY_SELECT_USER_CONFIG=$REPO_XRAY_CONFIG_VLESS_WS
        wget -O $CONFIG_VLESS_LINK_CLIENT_PATH $REPO_XRAY_CONFIG_VLESS_LINK
    else
        VALUE_XRAY_SELECT_USER_CONFIG=$REPO_XRAY_CONFIG_VLESS
        wget -O $CONFIG_VLESS_LINK_CLIENT_PATH $REPO_XRAY_CONFIG_VLESS_LINK_WS
    fi

    replace_text_in_file "CLIENT_UUID" $VALUE_XRAY_USER_UUID $CONFIG_VLESS_LINK_CLIENT_PATH
    replace_text_in_file "WEBSOCKET_PATH" $VALUE_XRAY_WS_PATH $CONFIG_VLESS_LINK_CLIENT_PATH
    replace_text_in_file "DOMAIN_NAME" $VALUE_YOUR_DOMAIN $CONFIG_VLESS_LINK_CLIENT_PATH

    wget -O $CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH $REPO_XRAY_CONFIG_SHADOWSOCKS_LINK

    replace_text_in_file "PASSWORD" $VALUE_XRAY_USER_PASSWORD_BASE64 $CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH
    replace_text_in_file "SERVER_IP" $(curl -s ifconfig.me) $CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH
    replace_text_in_file "SHADOWSOCKS_PORT" $VALUE_XRAY_SHADOWSOCKS_PORT $CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH

    VALUE_XRAY_VLESS_CONNECT=$(cat $CONFIG_VLESS_LINK_CLIENT_PATH)
    VALUE_XRAY_SHADOWSOCKS_CONNECT=$(cat $CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH)

    print_log "Select config: $VALUE_XRAY_SELECT_USER_CONFIG"
}

xray_update_user_config_template() {
    wget -O $CONFIG_VLESS_CLIENT_PATH $VALUE_XRAY_SELECT_USER_CONFIG

    replace_text_in_file "CLIENT_UUID" $VALUE_XRAY_USER_UUID $CONFIG_VLESS_CLIENT_PATH
    replace_text_in_file "WEBSOCKET_PATH" $VALUE_XRAY_WS_PATH $CONFIG_VLESS_CLIENT_PATH
    replace_text_in_file "DOMAIN_NAME" $VALUE_YOUR_DOMAIN $CONFIG_VLESS_CLIENT_PATH
}

write_text_in_file() {
    local file_path=$1
    local write_content=$2

    if [ ! -e $file_path ]; then
        touch $file_path
    fi
    echo "$write_content" > "$file_path"
}

print_result_install() {
    print_log "Your user vless config:"
    print_log "---------------------"
    print_log "> ! SAVE PASSWORD ! <"
    print_log $VALUE_XRAY_USER_PASSWORD
    print_log "---------------------"
    echo ""
    echo ""
    cat $CONFIG_VLESS_CLIENT_PATH
    echo ""
    echo ""
    print_log "---------------------"
    print_log "> VLESS CONNECT LUNK <"
    print_log $VALUE_XRAY_VLESS_CONNECT
    print_log "---------------------"
    print_log "> SHADOWSOCKS CONNECT LUNK <"
    print_log $VALUE_XRAY_SHADOWSOCKS_CONNECT
    print_log "---------------------"
    print_log "Config path: $CONFIG_VLESS_CLIENT_PATH"
    print_log "If you need get info, print: cat $CONFIG_VLESS_CLIENT_PATH"
    print_log "---------------------"
    print_log "Vless connect link: $CONFIG_VLESS_LINK_CLIENT_PATH"
    print_log "If you need get vless link, print: cat $CONFIG_VLESS_LINK_CLIENT_PATH"
    print_log "---------------------"
    print_log "Shadowsocks connect link: $CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH"
    print_log "If you need get shadowsocks link, print: cat $CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH"
    print_log "---------------------"
    print_log "Shadowsocks password path: $CONFIG_SHADOWSOCKS_PASSWORD_PATH"
    print_log "If you need get shadowsocks password, print: cat $CONFIG_SHADOWSOCKS_PASSWORD_PATH"
    print_log "---------------------"
    print_log "@+@+@+@+@+@+@+@+@+@+@"
    print_log "Allow installed!"
    print_log "@+@+@+@+@+@+@+@+@+@+@"
}

remove_xray() {
    systemctl stop nginx.service
    systemctl stop xray.service
    if [ -e $CONFIG_DIST_PATH ]; then
        rm -rf $CONFIG_DIST_PATH
        print_log "Remove: '$CONFIG_DIST_PATH'"
    fi
    if [ -e $NGINX_NEW_CONFIG ]; then
        rm -f $NGINX_NEW_CONFIG
        print_log "Remove: '$NGINX_NEW_CONFIG'"
    fi
    if [ -e $NGINX_DEFAULT_CONFIG_SRC ] && [ ! -e $NGINX_DEFAULT_CONFIG_LINK ]; then
        ln -s $NGINX_DEFAULT_CONFIG_SRC $NGINX_DEFAULT_CONFIG_LINK
        print_log "Link: '$NGINX_DEFAULT_CONFIG_LINK'"
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
}

install_xray() {
    if [ "$XRAY_RENEW_CONFIG" = "0" ]; then
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
        apt_install "qrencode"

        print_log "Run git script '$XRAY_GIT_SCRIPT'"
        bash -c "$(curl -L $XRAY_GIT_SCRIPT)" @ install -u root
    fi

    systemctl stop nginx.service
    systemctl stop xray.service

    read_domain
    read_mail

    letsencrypt_install_cert_from_domain $VALUE_YOUR_DOMAIN $VALUE_YOUR_EMAIL
    mkdir $CONFIG_DIST_PATH
    wget -O $XRAY_CONFIG_PATH $REPO_XRAY_CONFIG

    set_shadowsocks_port
    xray_update_config_template
    nginx_update_default_config
    xray_set_vless_config_type
    xray_update_user_config_template

    journalctl --vacuum-time=1s -u xray
    systemctl restart systemd-journald
    systemctl start nginx.service
    systemctl start xray.service

    check_service "nginx"
    check_service "xray"

    write_text_in_file \
        $CONFIG_SHADOWSOCKS_PASSWORD_PATH \
        $VALUE_XRAY_USER_PASSWORD

    print_result_install
}

print_help() {
    print_log "Arguments:"
    print_log "--help - Print help info"
    print_log "--install - Installing Xray"
    print_log "--remove - Deletes Xray"
    print_log "--reinstall - Reinstalls all configs and services"
    print_log "--renew - Reinstalls ONLY configuration files, without reinstalling services"
    print_log "--vless-qr - Outputs the Vless connection code to the terminal"
    print_log "--shadowsocks-qr - Outputs the Shadowsocks connection code to the terminal"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            print_help
            exit 0
            ;;
        --install)
            install_xray
            exit 0
            ;;
        --reinstall)
            remove_xray
            install_xray
            exit 0
            ;;
        --renew)
            XRAY_RENEW_CONFIG="1"
            install_xray
            exit 0
            ;;
        --vless-qr)
            if [ -e $CONFIG_VLESS_LINK_CLIENT_PATH ]; then
                qrencode -t ASCII "$(cat $CONFIG_VLESS_LINK_CLIENT_PATH)"
            else
                print_error "File $CONFIG_VLESS_LINK_CLIENT_PATH not found!"
            fi
            exit 0
            ;;
        --shadowsocks-qr)
            if [ -e $CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH ]; then
                qrencode -t ASCII "$(cat $CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH)"
            else
                print_error "File $CONFIG_SHADOWSOCKS_LINK_CLIENT_PATH not found!"
            fi
            exit 0
            ;;
        --remove)
            remove_xray
            exit 0
            ;;
        *)
            print_error "The unknown argument"
            print_help
            exit 1
            ;;
    esac
    shift
done

print_help