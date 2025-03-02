#!/bin/bash

# SCRIPT
XRAY_GIT_SCRIPT="https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
ROOT_GIT_REPO="https://raw.githubusercontent.com/Shark-vil/xray_vless_easy_install_script/master"
# --------------

# REPO CONFIG
# XRAY
REPO_XRAY_GEOIP="$ROOT_GIT_REPO/v2ray_geo/geoip.dat"
REPO_XRAY_GEOSITE="$ROOT_GIT_REPO/v2ray_geo/geosite.dat"
REPO_XRAY_CONFIG_VLESS="$ROOT_GIT_REPO/config/xray/user/vless.json"
REPO_XRAY_CONFIG_VLESS_LINK="$ROOT_GIT_REPO/config/xray/user/vless_link.txt"
REPO_XRAY_CONFIG_VLESS_WS="$ROOT_GIT_REPO/config/xray/user/vless_ws.json"
REPO_XRAY_CONFIG_VLESS_WS_LINK="$ROOT_GIT_REPO/config/xray/user/vless_ws_link.txt"
REPO_XRAY_CONFIG_SHADOWSOCKS="$ROOT_GIT_REPO/config/xray/user/shadowsocks.txt"
REPO_XRAY_CONFIG_SHADOWSOCKS_LINK="$ROOT_GIT_REPO/config/xray/user/shadowsocks_link.txt"
# NGINX
REPO_NGINX_CONFIG="$ROOT_GIT_REPO/config/nginx/default"
# --------------

# NGINX CONFIG
NGINX_DEFAULT_CONFIG_SRC="/etc/nginx/sites-available/default"
NGINX_DEFAULT_CONFIG_LINK="/etc/nginx/sites-enabled/default"
NGINX_NEW_CONFIG="/etc/nginx/sites-enabled/default.conf"
# --------------

# PATH
CONFIG_DIST_PATH="$HOME/xray_eis"
CONFIG_VLESS_PATH="$CONFIG_DIST_PATH/vless_config.json"
CONFIG_VLESS_LINK_PATH="$CONFIG_DIST_PATH/vless_link.txt"
CONFIG_VLESS_WS_PATH="$CONFIG_DIST_PATH/vless_ws_config.json"
CONFIG_VLESS_WS_LINK_PATH="$CONFIG_DIST_PATH/vless_ws_link.txt"
CONFIG_VLESS_SHADOWSOCKS_PATH="$CONFIG_DIST_PATH/shadowsocks_config.json"
CONFIG_VLESS_SHADOWSOCKS_LINK_PATH="$CONFIG_DIST_PATH/shadowsocks_link.txt"
CONFIG_XRAY_DIR_PATH="/usr/local/etc/xray"
CONFIG_XRAY_PATH="$CONFIG_XRAY_DIR_PATH/config.json"
CONFIG_XRAY_TMP_PATH="$CONFIG_XRAY_DIR_PATH/config.tmp.json"
# --------------

# VALUE
XRAY_SHADOWSOCKS_PORT_DEFAULT="5465"
PARAM_RENEW_CONFIG="0"
VALUE_ENCRYPTION_METHOD="2022-blake3-aes-128-gcm"
VALUE_XRAY_SHADOWSOCKS_PORT="$XRAY_SHADOWSOCKS_PORT_DEFAULT"
VALUE_OUTBOUNDS_PROXY=""
VALUE_INBOUNDS_VLESS_WS="0"
VALUE_INBOUNDS_VLESS_TLS="0"
VALUE_INBOUNDS_SHADOWSOCKS="0"
# --------------

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

jq_builder() {
    jq "$1" "$CONFIG_XRAY_PATH" > "$CONFIG_XRAY_TMP_PATH" && mv "$CONFIG_XRAY_TMP_PATH" "$CONFIG_XRAY_PATH"
    # print_log "JSON Builder: $(cat "$CONFIG_XRAY_PATH")"
}

jq_add_to_array() {
    key="$1"
    value="$2"
    jq "$key += [$value]" "$CONFIG_XRAY_PATH" > "$CONFIG_XRAY_TMP_PATH" && mv "$CONFIG_XRAY_TMP_PATH" "$CONFIG_XRAY_PATH"
    # print_log "JSON Builder: $(cat "$CONFIG_XRAY_PATH")"
}

jq_add_to_object() {
    key="$1"
    subkey="$2"
    value="$3"
    jq "$key.$subkey = $value" "$CONFIG_XRAY_PATH" > "$CONFIG_XRAY_TMP_PATH" && mv "$CONFIG_XRAY_TMP_PATH" "$CONFIG_XRAY_PATH"
    # print_log "JSON Builder: $(cat "$CONFIG_XRAY_PATH")"
}

write_text_in_file() {
    local file_path=$1
    local write_content=$2

    if [ ! -e $file_path ]; then
        touch $file_path
    fi
    echo "$write_content" > "$file_path"
}

check_service() {
    if systemctl is-active --quiet $1; then
        print_log "The '$1' service is working correctly!"
    else
        print_error "The '$1' service is running with errors!"
    fi
}

apt_update() {
    print_log "Updating package lists"
    if command -v apt-get &>/dev/null; then
        apt-get update
    elif command -v dnf &>/dev/null; then
        dnf check-update
    elif command -v yum &>/dev/null; then
        yum check-update
    elif command -v zypper &>/dev/null; then
        zypper refresh
    elif command -v pacman &>/dev/null; then
        pacman -Sy
    else
        print_log "Unsupported package manager"
        return 1
    fi
}

apt_install() {
    print_log "Installing package '$1'"
    if command -v apt-get &>/dev/null; then
        apt-get install -y "$1"
    elif command -v dnf &>/dev/null; then
        dnf install -y "$1"
    elif command -v yum &>/dev/null; then
        yum install -y "$1"
    elif command -v zypper &>/dev/null; then
        zypper install -y "$1"
    elif command -v pacman &>/dev/null; then
        pacman -S --noconfirm "$1"
    else
        print_log "Unsupported package manager"
        return 1
    fi
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

install_tor_network() {
    apt_update
    apt_install "tor"
}

install_warp_docker() {
    docker run -d \
        --name warp-xray \
        --restart always \
        -p 1080:1080 \
        -e WARP_SLEEP=2 \
        --cap-add NET_ADMIN \
        --sysctl net.ipv6.conf.all.disable_ipv6=0 \
        --sysctl net.ipv4.conf.all.src_valid_mark=1 \
        -v $HOME/warp-xray/data:/var/lib/cloudflare-warp \
        caomingjun/warp
}

install_docker() {
    DISTRO=$(lsb_release -is | tr '[:upper:]' '[:lower:]')
    
    if [ "$DISTRO" == "debian" ] || [ "$DISTRO" == "ubuntu" ]; then
        apt-get update
        apt-get install -y ca-certificates curl lsb-release
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
        chmod a+r /etc/apt/keyrings/docker.asc

        echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
        $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update

        apt-get install -y docker-ce \
            docker-ce-cli \
            containerd.io \
            docker-buildx-plugin \
            docker-compose-plugin
    elif [ "$DISTRO" == "centos" ] || [ "$DISTRO" == "rhel" ] || [ "$DISTRO" == "fedora" ]; then
        yum install -y dnf-utils
        dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

        dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

        systemctl start docker
        systemctl enable docker
    else
        echo "Support for this distribution is not implemented."
        return 1
    fi
}

set_encryption_method() {
    local select_type_number
    while true; do
        print_log "Choise shadowsocks encryption method (Default: 2022-blake3-aes-128-gcm, Press \"Enter\" to skip):"
        print_log "1. 2022-blake3-aes-128-gcm"
        print_log "2. 2022-blake3-aes-256-gcm"
        print_log "3. 2022-blake3-chacha20-poly1305"
        print_log "4. aes-128-gcm"
        print_log "5. aes-256-gcm"
        print_log "6. chacha20-poly1305"
        print_log "7. chacha20-ietf-poly1305"
        print_log "8. xchacha20-poly1305"
        print_log "9. xchacha20-ietf-poly1305"
        read -r select_type_number < /dev/tty
        case "$select_type_number" in
            1)
                VALUE_ENCRYPTION_METHOD="2022-blake3-aes-128-gcm"
                ;;
            2)
                VALUE_ENCRYPTION_METHOD="2022-blake3-aes-256-gcm"
                ;;
            3)
                VALUE_ENCRYPTION_METHOD="2022-blake3-chacha20-poly1305"
                ;;
            4)
                VALUE_ENCRYPTION_METHOD="aes-128-gcm"
                ;;
            5)
                VALUE_ENCRYPTION_METHOD="aes-256-gcm"
                ;;
            6)
                VALUE_ENCRYPTION_METHOD="chacha20-poly1305"
                ;;
            7)
                VALUE_ENCRYPTION_METHOD="chacha20-ietf-poly1305"
                ;;
            8)
                VALUE_ENCRYPTION_METHOD="xchacha20-poly1305"
                ;;
            9)
                VALUE_ENCRYPTION_METHOD="xchacha20-ietf-poly1305"
                ;;
            *)
                VALUE_ENCRYPTION_METHOD="2022-blake3-aes-128-gcm"
                ;;
        esac
        if confirm_changes "'$VALUE_ENCRYPTION_METHOD' - Is this the correct method?"; then
            break
        fi
        print_error "Method not correct. Try again."
    done
}

read_domain() {
    while true; do
        print_log "Print your REAL domain name (example: mysite.com):"
        read -r VALUE_YOUR_DOMAIN < /dev/tty
        if confirm_changes "'$VALUE_YOUR_DOMAIN' - Is this the correct domain?"; then
            break
        fi
        print_error "Domain not correct. Try again."
    done
}

read_mail() {
    while true; do
        print_log "Print your REAL email (example: mymail@gmail.com):"
        read -r VALUE_YOUR_EMAIL < /dev/tty
        if confirm_changes "'$VALUE_YOUR_EMAIL' - Is this the correct domain?"; then
            break
        fi
        print_error "Mail not correct. Try again."
    done
}

set_shadowsocks_port() {
    while true; do
        print_log "Print shadowsocks port (default: $XRAY_SHADOWSOCKS_PORT_DEFAULT, Press \"Enter\" to skip):"
        read VALUE_XRAY_SHADOWSOCKS_PORT < /dev/tty
        if ! is_number $VALUE_XRAY_SHADOWSOCKS_PORT; then
            VALUE_XRAY_SHADOWSOCKS_PORT="$XRAY_SHADOWSOCKS_PORT_DEFAULT"
        fi
        if ss -tuln | grep -q ":$VALUE_XRAY_SHADOWSOCKS_PORT"; then
            print_error "The port $VALUE_XRAY_SHADOWSOCKS_PORT is already in use"
            VALUE_XRAY_SHADOWSOCKS_PORT="$XRAY_SHADOWSOCKS_PORT_DEFAULT"
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

nginx_update_default_config() {
    print_log "Replace default nginx config"
    if [ -e $NGINX_DEFAULT_CONFIG_LINK ]; then
        rm -f $NGINX_DEFAULT_CONFIG_LINK
    fi
    wget -q --show-progress -O $NGINX_NEW_CONFIG $REPO_NGINX_CONFIG
}

xray_update_config_template() {
    local user_password_base64=$(openssl rand -base64 16)
    local user_uuid=$(cat /proc/sys/kernel/random/uuid)
    local ws_path="$(tr -dc 'a-z' < /dev/urandom | head -c 24)"

    if [ -f "$CONFIG_XRAY_PATH" ]; then
        rm "$CONFIG_XRAY_PATH"
    fi

    if [ -f "$CONFIG_XRAY_TMP_PATH" ]; then
        rm "$CONFIG_XRAY_TMP_PATH"
    fi

    echo "{}" > "$CONFIG_XRAY_PATH"

    jq_builder '.log = { "loglevel": "info" }'
    jq_builder '.routing.rules = []'
    jq_builder '.routing.rules += [
    { "type": "field", "outboundTag": "block", "port": "135, 137, 138, 139" },
    { "type": "field", "outboundTag": "block", "protocol": ["bittorrent"] },
    { "type": "field", "outboundTag": "block", "ip": ["geoip:private"] },
    { "type": "field", "outboundTag": "direct", "network": "tcp,udp", "ip": ["0.0.0.0/0", "::/0"] }
    ]'
    jq_add_to_object ".routing" "domainStrategy" "\"AsIs\""
    jq_builder '.inbounds = []'
    if [ "$VALUE_INBOUNDS_SHADOWSOCKS" = "1" ]; then
        jq_builder '.inbounds += [
        {
            "port": '"$VALUE_XRAY_SHADOWSOCKS_PORT"',
            "tag": "ss",
            "protocol": "shadowsocks",
            "settings": {
            "method": '"\"$VALUE_ENCRYPTION_METHOD\""',
            "password": '"\"$user_password_base64\""',
                "network": "tcp,udp"
            }
        }
        ]'
    fi
    if [ "$VALUE_INBOUNDS_VLESS_TLS" = "1" ]; then
        jq_builder '.inbounds += [
        {
            "port": 443,
            "protocol": "vless",
            "tag": "vless_tls",
            "settings": {
                "clients": [
                    {
                        "id": '"\"$user_uuid\""',
                        "email": '"\"$VALUE_YOUR_EMAIL\""',
                        "flow": "xtls-rprx-vision"
                    }
                ],
                "decryption": "none",
                "fallbacks": [
                    {
                        "dest": "8080"
                    }
                ]
            },
            "streamSettings": {
                "network": "tcp",
                "security": "tls",
                "tlsSettings": {
                "alpn": [
                    "http/1.1",
                    "h2"
                ],
                "certificates": [
                    {
                        "certificateFile": '"\"$VALUE_LETSENCRYPT_FULLCHAIN\""',
                        "keyFile": '"\"$VALUE_LETSENCRYPT_PRIVKEY\""'
                    }
                ]
                }
            },
            "sniffing": {
                "enabled": true,
                "destOverride": [
                    "http",
                    "tls"
                ]
            }
        }
        ]'

        if [ "$VALUE_INBOUNDS_VLESS_WS" = "1" ]; then
            jq_builder '.inbounds |= map(if .tag == "vless_tls" then .settings.fallbacks += [{"path": '"\"/$ws_path\""', "dest": "@vless-ws"}] else . end)'
        fi
    fi
    if [ "$VALUE_INBOUNDS_VLESS_WS" = "1" ]; then
        jq_builder '.inbounds += [
        {
            "listen": "@vless-ws",
            "protocol": "vless",
            "tag": "vless_ws",
            "settings": {
                "clients": [
                    {
                        "id": '"\"$user_uuid\""',
                        "email": '"\"$VALUE_YOUR_EMAIL\""'
                    }
                ],
                "decryption": "none"
            },
            "streamSettings": {
                "network": "ws",
                "security": "none",
                "wsSettings": {
                    "path": '"\"/$ws_path\""'
                }
            }
        }
        ]'
    fi
    jq_builder '.outbounds = []'
    jq_builder '.outbounds += [
    { "protocol": "freedom", "tag": "direct" },
    { "protocol": "blackhole", "tag": "block" }
    ]'
    case "$VALUE_OUTBOUNDS_PROXY" in
        "tor")
            jq_builder '.outbounds += [
            {
                "protocol": "socks",
                "tag": "tor_proxy",
                "settings": {
                    "servers": [
                    {
                        "address": "127.0.0.1",
                        "port": 9050
                    }
                    ]
                }
            }
            ]'
            ;;
        "warp")
            jq_builder '.outbounds += [
            {
                "protocol": "socks",
                "tag": "warp_proxy",
                "settings": {
                    "servers": [
                    {
                        "address": "127.0.0.1",
                        "port": 1080
                    }
                    ]
                }
            }
            ]'
            ;;
        *)
            ;;
    esac

    wget -q --show-progress -nc -P $CONFIG_XRAY_DIR_PATH $REPO_XRAY_GEOIP
    wget -q --show-progress -nc -P $CONFIG_XRAY_DIR_PATH $REPO_XRAY_GEOSITE

    if [ "$VALUE_INBOUNDS_VLESS_TLS" = "1" ]; then
        wget -q --show-progress -O $CONFIG_VLESS_PATH $REPO_XRAY_CONFIG_VLESS
        wget -q --show-progress -O $CONFIG_VLESS_LINK_PATH $REPO_XRAY_CONFIG_VLESS_LINK
    fi

    if [ "$VALUE_INBOUNDS_VLESS_WS" = "1" ]; then
        wget -q --show-progress -O $CONFIG_VLESS_WS_PATH $REPO_XRAY_CONFIG_VLESS_WS
        wget -q --show-progress -O $CONFIG_VLESS_WS_LINK_PATH $REPO_XRAY_CONFIG_VLESS_WS_LINK
    fi

    if [ "$VALUE_INBOUNDS_SHADOWSOCKS" = "1" ]; then
        wget -q --show-progress -O $CONFIG_VLESS_SHADOWSOCKS_PATH $REPO_XRAY_CONFIG_SHADOWSOCKS
        wget -q --show-progress -O $CONFIG_VLESS_SHADOWSOCKS_LINK_PATH $REPO_XRAY_CONFIG_SHADOWSOCKS_LINK
    fi

    for path in "$CONFIG_VLESS_PATH" "$CONFIG_VLESS_LINK_PATH" "$CONFIG_VLESS_WS_PATH" "$CONFIG_VLESS_WS_LINK_PATH" "$CONFIG_VLESS_SHADOWSOCKS_PATH" "$CONFIG_VLESS_SHADOWSOCKS_LINK_PATH"; do
        if [ ! -f "$path" ]; then
            continue
        fi
        replace_text_in_file "CLIENT_UUID" $user_uuid $path
        replace_text_in_file "CLIENT_MAIL" $VALUE_YOUR_EMAIL $path
        replace_text_in_file "WEBSOCKET_PATH" $ws_path $path
        replace_text_in_file "DOMAIN_NAME" $VALUE_YOUR_DOMAIN $path
        replace_text_in_file "PASSWORD" $user_password_base64 $path
        replace_text_in_file "SERVER_IP" $(curl -s ifconfig.me) $path
        replace_text_in_file "SHADOWSOCKS_PORT" $VALUE_XRAY_SHADOWSOCKS_PORT $path
        replace_text_in_file "ENCRYPTION_METHOD" $VALUE_ENCRYPTION_METHOD $path
        replace_text_in_file "LETSENCRYPT_FULLCHAIN" $VALUE_LETSENCRYPT_FULLCHAIN $path
        replace_text_in_file "LETSENCRYPT_PRIVKEY" $VALUE_LETSENCRYPT_PRIVKEY $path
    done
}

print_result_install() {
    print_log "Your user config:"
    if [ "$VALUE_INBOUNDS_VLESS_TLS" = "1" ]; then
        print_log "---------------------"
        print_log "> VLESS CONNECT LUNK <"
        print_log $(cat $CONFIG_VLESS_LINK_PATH)
        print_log "---------------------"
    fi
    if [ "$VALUE_INBOUNDS_VLESS_WS" = "1" ]; then
        print_log "---------------------"
        print_log "> VLESS WEBSOCKET CONNECT LUNK <"
        print_log $(cat $CONFIG_VLESS_WS_LINK_PATH)
        print_log "---------------------"
    fi
    if [ "$VALUE_INBOUNDS_SHADOWSOCKS" = "1" ]; then
        print_log "---------------------"
        print_log "> SHADOWSOCKS CONNECT LUNK <"
        print_log $(cat $CONFIG_VLESS_SHADOWSOCKS_LINK_PATH)
        print_log "---------------------"
    fi
    if [ "$VALUE_INBOUNDS_VLESS_TLS" = "1" ]; then
        print_log "---------------------"
        print_log "Vless link path: $CONFIG_VLESS_LINK_PATH"
        print_log "Vless config path: $CONFIG_VLESS_PATH"
        print_log "---------------------"
    fi
    if [ "$VALUE_INBOUNDS_VLESS_WS" = "1" ]; then
        print_log "---------------------"
        print_log "Vless WebSocket link path: $CONFIG_VLESS_WS_LINK_PATH"
        print_log "Vless WebSocket config path: $CONFIG_VLESS_WS_PATH"
        print_log "---------------------"
    fi
    if [ "$VALUE_INBOUNDS_SHADOWSOCKS" = "1" ]; then
        print_log "---------------------"
        print_log "Shadowsocks link path: $CONFIG_VLESS_SHADOWSOCKS_LINK_PATH"
        print_log "Shadowsocks config path: $CONFIG_VLESS_SHADOWSOCKS_PATH"
        print_log "---------------------" 
    fi
    print_log "@+@+@+@+@+@+@+@+@+@+@"
    print_log "Allow installed!"
    print_log "@+@+@+@+@+@+@+@+@+@+@"
}

remove_xray() {
    docker rm -f waro-xray
    systemctl stop nginx.service
    systemctl stop xray.service
    if [ -e $CONFIG_DIST_PATH ]; then
        rm -rf $CONFIG_DIST_PATH
        print_log "Remove: '$CONFIG_DIST_PATH'"
    fi
    if [ -e "$HOME/warp-xray" ]; then
        rm -rf "$HOME/warp-xray"
        print_log "Remove: '$HOME/warp-xray'"
    fi
    if [ -e $NGINX_NEW_CONFIG ]; then
        rm -f $NGINX_NEW_CONFIG
        print_log "Remove: '$NGINX_NEW_CONFIG'"
    fi
    if [ -e $NGINX_DEFAULT_CONFIG_SRC ] && [ ! -e $NGINX_DEFAULT_CONFIG_LINK ]; then
        ln -s $NGINX_DEFAULT_CONFIG_SRC $NGINX_DEFAULT_CONFIG_LINK
        print_log "Link: '$NGINX_DEFAULT_CONFIG_LINK'"
    fi
    if [ -e $CONFIG_XRAY_PATH ]; then
        rm -f $CONFIG_XRAY_PATH
        print_log "Remove: '$CONFIG_XRAY_PATH'"
    fi
    print_log "Remove git script '$XRAY_GIT_SCRIPT'"
    bash -c "$(curl -L $XRAY_GIT_SCRIPT)" @ remove --purge
    systemctl start nginx.service
    print_log "Start nginx service"
    check_service "nginx"
}

set_outbounds_proxy() {
    if ! confirm_changes "Do you want to hide the server IP to the outside world? (WARNING: Connection speed via double proxy will be lower!)"; then
        return
    fi

    local select_type_number
    while true; do
        print_log "Select the type of proxy (Default: WARP):"
        print_log "1. WARP (Cloudflare)"
        print_log "2. TOR (Tor network)"
        read -r select_type_number < /dev/tty
        case "$select_type_number" in
            1)
                VALUE_OUTBOUNDS_PROXY="warp"
                ;;
            2)
                VALUE_OUTBOUNDS_PROXY="tor"
                ;;
            *)
                VALUE_OUTBOUNDS_PROXY="warp"
                ;;
        esac
        if confirm_changes "'$VALUE_OUTBOUNDS_PROXY' - Is this the correct method?"; then
            break
        fi
        print_error "Method not correct. Try again."
    done
}

set_xray_inbounds() {
    local select_type_number
    while true; do
        print_log "Choose how you want to configure XRay:"
        if [ "$VALUE_INBOUNDS_VLESS_TLS" = "0" ]; then
            print_log "1. Vless TLS (Not selected)"
        else
            print_log "1. Vless TLS (Selected)"
        fi
        if [ "$VALUE_INBOUNDS_VLESS_WS" = "0" ]; then
            print_log "2. Vless WebSocket (Not selected)"
        else
            print_log "2. Vless WebSocket (Selected)"
        fi
        if [ "$VALUE_INBOUNDS_SHADOWSOCKS" = "0" ]; then
            print_log "3. Shadowsocks (Not selected)"
        else
            print_log "3. Shadowsocks (Selected)"
        fi
        print_log "0. Complete selection and continue"
        read -r select_type_number < /dev/tty
        case "$select_type_number" in
            0)
                if [ "$VALUE_INBOUNDS_VLESS_TLS" = "0" ] && [ "$VALUE_INBOUNDS_VLESS_WS" = "0" ] && [ "$VALUE_INBOUNDS_SHADOWSOCKS" = "0" ]; then
                    print_error "At least one item must be selected!"
                elif confirm_changes "Complete selection?"; then
                    break
                fi
                ;;
            1)
                if [ "$VALUE_INBOUNDS_VLESS_TLS" = "0" ]; then
                    VALUE_INBOUNDS_VLESS_TLS="1"
                else
                    VALUE_INBOUNDS_VLESS_TLS="0"
                fi
                ;;
            2)
                if [ "$VALUE_INBOUNDS_VLESS_WS" = "0" ]; then
                    VALUE_INBOUNDS_VLESS_WS="1"
                else
                    VALUE_INBOUNDS_VLESS_WS="0"
                fi
                ;;
            3)
                if [ "$VALUE_INBOUNDS_SHADOWSOCKS" = "0" ]; then
                    VALUE_INBOUNDS_SHADOWSOCKS="1"
                else
                    VALUE_INBOUNDS_SHADOWSOCKS="0"
                fi
                ;;
            *)
                print_error "Method not correct. Try again."
                ;;
        esac
    done
}

install_xray() {
    if [ "$PARAM_RENEW_CONFIG" = "0" ]; then
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
        apt_install "jq"

        print_log "Run git script '$XRAY_GIT_SCRIPT'"
        bash -c "$(curl -L $XRAY_GIT_SCRIPT)" @ install -u root
    fi

    systemctl stop nginx.service
    systemctl stop xray.service

    set_xray_inbounds

    if [ "$VALUE_INBOUNDS_VLESS_TLS" = "1" ] || [ "$VALUE_INBOUNDS_VLESS_WS" = "1" ]; then
        read_domain
        read_mail
        letsencrypt_install_cert_from_domain $VALUE_YOUR_DOMAIN $VALUE_YOUR_EMAIL
    fi

    if [ -d "$CONFIG_DIST_PATH" ]; then
        rm -r "$CONFIG_DIST_PATH"
    fi

    mkdir "$CONFIG_DIST_PATH"

    if [ "$VALUE_INBOUNDS_SHADOWSOCKS" = "1" ]; then
        set_shadowsocks_port
        set_encryption_method
    fi

    set_outbounds_proxy

    case "$VALUE_OUTBOUNDS_PROXY" in
        "tor")
            install_tor_network
            ;;
        "warp")
            install_docker
            install_warp_docker
            ;;
        *)
            ;;
    esac

    xray_update_config_template
    nginx_update_default_config

    journalctl --vacuum-time=1s -u xray
    systemctl restart systemd-journald
    systemctl start nginx.service
    systemctl start xray.service

    check_service "nginx"
    check_service "xray"

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
    print_log "--vless-ws-qr - Outputs the Vless WebSocket connection code to the terminal"
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
            PARAM_RENEW_CONFIG="1"
            install_xray
            exit 0
            ;;
        --vless-qr)
            if [ -e $CONFIG_VLESS_LINK_PATH ]; then
                qrencode -t ASCII "$(cat $CONFIG_VLESS_LINK_PATH)"
            else
                print_error "File $CONFIG_VLESS_LINK_PATH not found!"
            fi
            exit 0
            ;;
        --vless-ws-qr)
            if [ -e $CONFIG_VLESS_WS_LINK_PATH ]; then
                qrencode -t ASCII "$(cat $CONFIG_VLESS_WS_LINK_PATH)"
            else
                print_error "File $CONFIG_VLESS_WS_LINK_PATH not found!"
            fi
            exit 0
            ;;
        --shadowsocks-qr)
            if [ -e $CONFIG_VLESS_SHADOWSOCKS_LINK_PATH ]; then
                qrencode -t ASCII "$(cat $CONFIG_VLESS_SHADOWSOCKS_LINK_PATH)"
            else
                print_error "File $CONFIG_VLESS_SHADOWSOCKS_LINK_PATH not found!"
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