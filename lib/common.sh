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

# older versions wrote client links/configs here; now they are generated on
# the fly (xvei links / qr / client-config), `xvei remove` deletes the folder
if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ]; then
    LEGACY_CLIENT_DIR="$(getent passwd "$SUDO_USER" | cut -d: -f6)/xray_eis"
else
    LEGACY_CLIENT_DIR="${HOME}/xray_eis"
fi

# XVEI_ROOT is exported by xvei.sh before sourcing this file.
PYENGINE="${XVEI_ROOT}/pyengine"

# --- terminal output ------------------------------------------------------
# Colors only on a terminal and never with NO_COLOR; box-drawing symbols only
# with a UTF-8 locale (XVEI_ASCII tells pyengine/util.py the same).
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ] && [ "${TERM:-}" != dumb ]; then
    _c_info=$'\033[96m'; _c_ok=$'\033[92m'; _c_warn=$'\033[93m'; _c_err=$'\033[91m'
    _c_bold=$'\033[1m'; _c_dim=$'\033[2m'; _c_head=$'\033[1;96m'; _c_group=$'\033[1;93m'
    _c_off=$'\033[0m'
else
    _c_info=""; _c_ok=""; _c_warn=""; _c_err=""; _c_bold=""; _c_dim=""; _c_head=""
    _c_group=""; _c_off=""
fi
case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in
    *[Uu][Tt][Ff]-8*|*[Uu][Tt][Ff]8*)
        _s_rule="─"; _s_info="›"; _s_ok="✓"; _s_err="✗"; _s_sep="·"; _s_on="●"; _s_off="○"; _s_bullet="•"
        unset XVEI_ASCII ;;
    *)
        _s_rule="-"; _s_info=">"; _s_ok="+"; _s_err="x"; _s_sep="|"; _s_on="*"; _s_off="o"; _s_bullet="*"
        export XVEI_ASCII=1 ;;
esac

log()   { echo -e "${_c_info}${_s_info}${_c_off} $*"; }
ok()    { echo -e "${_c_ok}${_s_ok}${_c_off} $*"; }
warn()  { echo -e "${_c_warn}!${_c_off} $*" >&2; }
err()   { echo -e "${_c_err}${_s_err} $*${_c_off}" >&2; }
die()   { err "$*"; exit 1; }

# ui_header <title>: a blank line, then `── Title ─────`
ui_header() {
    local t="$1" line="$_s_rule$_s_rule $1 " i
    for ((i = ${#t} + 4; i < 60; i++)); do line+="$_s_rule"; done
    printf '\n%s%s%s\n' "$_c_head" "$line" "$_c_off"
}
ui_group() { printf '%s  %s%s\n' "$_c_group" "$1" "$_c_off"; }
# ui_opt <number> <label> [hint]: one menu line, hints dimmed and aligned
ui_opt() {
    printf '  %s%3s)%s %-20s %s%s%s\n' "$_c_info" "$1" "$_c_off" "$2" "$_c_dim" "${3:-}" "$_c_off"
}
ui_back() { printf '  %s%3s) %s%s\n' "$_c_dim" 0 "${1:-Back}" "$_c_off"; }
ui_dim()  { printf '%s%s%s\n' "$_c_dim" "$*" "$_c_off"; }
ui_li()   { printf '    %s %s\n' "$_s_bullet" "$*"; }

# --- python engine bridge ------------------------------------------------
# The engine needs Python >= 3.7. A plain `python3` is not always that: EL8 and
# openSUSE Leap 15 ship 3.6 under that name, and `python` may be Python 2.
find_python() {
    local c
    for c in python3 python3.13 python3.12 python3.11 python3.10 python3.9 python3.8 python3.7 python; do
        command -v "$c" >/dev/null 2>&1 || continue
        if "$c" -c 'import sys; sys.exit(sys.version_info < (3, 7))' 2>/dev/null; then
            command -v "$c"
            return 0
        fi
    done
    return 1
}

_PYBIN=""
py() {
    [ -n "$_PYBIN" ] || _PYBIN="$(find_python)" \
        || die "Python >= 3.7 not found; run: xvei install (it sets up dependencies)"
    "$_PYBIN" "$PYENGINE" "$@"
}

# --- misc ----------------------------------------------------------------
require_root() {
    [ "$(id -u)" -eq 0 ] || die "run as root"
}

# true when an interactive terminal is available for prompts
have_tty() { { : < /dev/tty; } 2>/dev/null; }

confirm() {
    local prompt="$1" def="${2:-y}" ans
    local hint="Y/n"; [ "$def" = "n" ] && hint="y/N"
    read -r -p "$(echo -e "${_c_info}?${_c_off} ${prompt} ${_c_dim}(${hint})${_c_off}: ")" ans < /dev/tty
    ans="${ans:-$def}"
    case "${ans,,}" in y|yes|d|да) return 0 ;; *) return 1 ;; esac
}

read_value() {
    local prompt="$1" def="${2:-}" out
    read -r -p "$(echo -e "${_c_info}?${_c_off} ${prompt}${def:+ ${_c_dim}[$def]${_c_off}}: ")" out < /dev/tty
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
