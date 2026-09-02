# shellcheck shell=bash
# Xray-core install / removal / validation / geo data.

XRAY_INSTALL_URL="https://github.com/XTLS/Xray-install/raw/main/install-release.sh"

xray_installed() { command -v xray >/dev/null 2>&1; }

xray_install() {
    if xray_installed; then
        log "xray already installed ($(xray version 2>/dev/null | head -1))"
        return 0
    fi
    curl -fsSL --head "$XRAY_INSTALL_URL" >/dev/null \
        || die "cannot reach $XRAY_INSTALL_URL"
    log "installing xray-core via XTLS/Xray-install"
    bash -c "$(curl -fsSL "$XRAY_INSTALL_URL")" @ install -u root
    xray_installed || die "xray install failed"
}

xray_remove_pkg() {
    xray_installed || return 0
    log "removing xray-core"
    bash -c "$(curl -fsSL "$XRAY_INSTALL_URL")" @ remove --purge || true
}

# The XTLS installer already ships geoip.dat / geosite.dat and puts them in the
# right asset dir. This is an explicit opt-in refresh to the latest release.
xray_update_geo() {
    log "refreshing geoip.dat / geosite.dat via XTLS/Xray-install"
    bash -c "$(curl -fsSL "$XRAY_INSTALL_URL")" @ install-geodata
}

# xray_test <config-file>   (file must end in .json - xray infers format from it)
xray_test() {
    local out
    out="$(xray run -test -config "$1" 2>&1)" && return 0
    out="$(xray -test -config "$1" 2>&1)" && return 0
    echo "$out" >&2
    return 1
}

xray_restart() {
    systemctl restart xray.service
    systemctl enable xray.service >/dev/null 2>&1 || true
}
