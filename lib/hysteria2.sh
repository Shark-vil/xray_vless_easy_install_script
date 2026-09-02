# shellcheck shell=bash
# Hysteria2 server: installed via the official installer, config rendered by
# the python engine. All egress is forwarded into Xray's local SOCKS5 inbound,
# so Xray owns the routing.

HY2_INSTALL_URL="https://get.hy2.sh/"

hy2_installed() { command -v hysteria >/dev/null 2>&1; }

hy2_install() {
    if hy2_installed; then
        log "hysteria already installed ($(hysteria version 2>/dev/null | awk '/^Version/{print $2}'))"
        return 0
    fi
    log "installing hysteria2 (official installer)"
    bash -c "$(curl -fsSL "$HY2_INSTALL_URL")" || die "hysteria2 install failed"
    hy2_installed || die "hysteria binary missing after install"
}

hy2_remove_pkg() {
    hy2_installed || return 0
    systemctl disable --now "$HY2_SERVICE" 2>/dev/null || true
    log "removing hysteria2"
    bash -c "$(curl -fsSL "$HY2_INSTALL_URL")" hysteria --remove || true
    rm -rf "$HY2_DIR"
}

# Copy the active certificate where the hysteria-server user can read it.
hy2_sync_cert() {
    mkdir -p "$HY2_DIR"
    local mode fc pk
    mode="$(state_get cert.mode)"
    fc="$(state_get cert.fullchain)"
    pk="$(state_get cert.privkey)"
    if [ "$mode" = "letsencrypt" ] && [ -e "$fc" ] && [ -e "$pk" ]; then
        install -m 644 "$fc" "$HY2_DIR/cert.crt"
        install -m 640 "$pk" "$HY2_DIR/cert.key"
    else
        cert_selfsigned
        install -m 644 "$HY2_DIR/self.crt" "$HY2_DIR/cert.crt"
        install -m 640 "$HY2_DIR/self.key" "$HY2_DIR/cert.key"
    fi
    if id hysteria >/dev/null 2>&1; then
        chgrp hysteria "$HY2_DIR/cert.key" 2>/dev/null || true
    else
        chmod 644 "$HY2_DIR/cert.key"
    fi
}

# hy2_apply <rendered-config-file|"">  -- called by apply.sh
hy2_apply() {
    local newcfg="$1"
    if [ -z "$newcfg" ] || [ ! -s "$newcfg" ]; then
        # HY2 no longer configured: stop the service if present
        if hy2_installed; then
            systemctl disable --now "$HY2_SERVICE" 2>/dev/null || true
            ok "hysteria2 stopped (no longer in config)"
        fi
        return 0
    fi
    hy2_install
    mkdir -p "$HY2_DIR"
    hy2_sync_cert
    install -m 644 "$newcfg" "$HY2_CONFIG"
    systemctl enable "$HY2_SERVICE" >/dev/null 2>&1 || true
    systemctl restart "$HY2_SERVICE"
    if ! check_service "$HY2_SERVICE"; then
        warn "hysteria2 failed to start; check: journalctl -u $HY2_SERVICE -n40"
    fi
}
