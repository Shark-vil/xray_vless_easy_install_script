# shellcheck shell=bash
# Shared helpers, paths and the python-engine bridge. Sourced by every module.

set -o pipefail

# --- paths ------------------------------------------------------------------
XRAY_DIR="/usr/local/etc/xray"
XRAY_CONFIG="$XRAY_DIR/config.json"
XVEI_STATE="${XVEI_STATE:-$XRAY_DIR/xvei-state.json}"
export XVEI_STATE

HY2_DIR="/etc/hysteria"
HY2_CONFIG="$HY2_DIR/config.yaml"
HY2_SERVICE="hysteria-server"

NGINX_SITE_AVAILABLE="/etc/nginx/sites-available/default"
NGINX_SITE_ENABLED="/etc/nginx/sites-enabled/default"
NGINX_XVEI_SITE="/etc/nginx/sites-enabled/xvei.conf"

if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    CLIENT_DIR="$(getent passwd "$SUDO_USER" | cut -d: -f6)/xray_eis"
else
    CLIENT_DIR="${HOME}/xray_eis"
fi
export XVEI_CLIENT_DIR="$CLIENT_DIR"

# XVEI_ROOT is exported by xvei.sh before sourcing this file.
PYENGINE="${XVEI_ROOT}/pyengine"

# --- logging --------------------------------------------------------------
_c_info=$'\033[96m'; _c_ok=$'\033[92m'; _c_warn=$'\033[93m'; _c_err=$'\033[91m'; _c_off=$'\033[0m'

log()   { echo -e "${_c_info}[xvei]${_c_off} $*"; }
ok()    { echo -e "${_c_ok}[xvei]${_c_off} $*"; }
warn()  { echo -e "${_c_warn}[xvei]${_c_off} $*" >&2; }
err()   { echo -e "${_c_err}[xvei:error]${_c_off} $*" >&2; }
die()   { err "$*"; exit 1; }

# --- python engine bridge ------------------------------------------------
py() {
    local bin
    bin="$(command -v python3 || command -v python)" || die "python3 not found"
    "$bin" "$PYENGINE" "$@"
}

# py_changed <args...> : returns 0 if state changed, 1 on error, 2 if no change
py_changed() {
    py "$@"
    return $?
}

# --- misc ----------------------------------------------------------------
require_root() {
    [ "$(id -u)" -eq 0 ] || die "run as root"
}

is_number() { [[ "$1" =~ ^[0-9]+$ ]]; }

port_in_use() {
    ss -tulnH 2>/dev/null | grep -qE "[:.]${1}[[:space:]]"
}

confirm() {
    local prompt="$1" def="${2:-y}" ans
    local hint="Y/n"; [ "$def" = "n" ] && hint="y/N"
    read -r -p "$(echo -e "${_c_info}?${_c_off} ${prompt} (${hint}): ")" ans < /dev/tty
    ans="${ans:-$def}"
    case "${ans,,}" in y|yes|d|да) return 0 ;; *) return 1 ;; esac
}

read_value() {
    local prompt="$1" def="${2:-}" out
    read -r -p "$(echo -e "${_c_info}?${_c_off} ${prompt}${def:+ [$def]}: ")" out < /dev/tty
    echo "${out:-$def}"
}

check_service() {
    if systemctl is-active --quiet "$1"; then
        ok "service '$1' is active"
    else
        err "service '$1' is NOT active"
        return 1
    fi
}

server_ip() {
    local ip
    ip="$(curl -fsS4 --max-time 8 https://api.ipify.org 2>/dev/null)" \
        || ip="$(curl -fsS --max-time 8 https://ifconfig.me 2>/dev/null)" \
        || ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    echo "$ip"
}

state_get() { py state-get "$1" 2>/dev/null; }
state_exists() { [ -f "$XVEI_STATE" ]; }
