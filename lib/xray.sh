# shellcheck shell=bash
# Xray-core install / removal / validation / geo data.

XRAY_INSTALL_URL="https://github.com/XTLS/Xray-install/raw/main/install-release.sh"
GEOIP_URL="https://github.com/v2fly/geoip/releases/latest/download/geoip.dat"
GEOSITE_URL="https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat"

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

xray_update_geo() {
    mkdir -p "$XRAY_DIR"
    log "downloading geoip.dat (v2fly)"
    wget -q -O "$XRAY_DIR/geoip.dat.new" "$GEOIP_URL" \
        && mv "$XRAY_DIR/geoip.dat.new" "$XRAY_DIR/geoip.dat" \
        || warn "geoip.dat download failed (keeping existing)"
    log "downloading geosite.dat (v2fly/domain-list-community)"
    wget -q -O "$XRAY_DIR/geosite.dat.new" "$GEOSITE_URL" \
        && mv "$XRAY_DIR/geosite.dat.new" "$XRAY_DIR/geosite.dat" \
        || warn "geosite.dat download failed (keeping existing)"
}

# xray_test <config-file>
xray_test() {
    xray -test -config "$1" 2>/dev/null || xray run -test -config "$1"
}

xray_restart() {
    systemctl restart xray.service
    systemctl enable xray.service >/dev/null 2>&1 || true
}
