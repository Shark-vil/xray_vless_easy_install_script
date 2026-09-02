# shellcheck shell=bash
# TLS certificates: Let's Encrypt (standalone) with a self-signed fallback.

cert_issue() {
    local domain email
    domain="$(state_get domain)"
    email="$(state_get email)"
    [ -n "$domain" ] || die "no domain in state; run: xvei set-meta --domain <d> --email <e>"

    local fullchain="/etc/letsencrypt/live/$domain/fullchain.pem"
    local privkey="/etc/letsencrypt/live/$domain/privkey.pem"

    if [ -e "$fullchain" ] && [ -e "$privkey" ]; then
        log "certificate for $domain already present"
    else
        ensure_bin certbot
        log "requesting Let's Encrypt certificate for $domain"
        systemctl stop nginx 2>/dev/null || true
        systemctl stop xray 2>/dev/null || true
        if certbot certonly --standalone --non-interactive --agree-tos \
            --email "$email" -d "$domain"; then
            py set-meta --cert-mode letsencrypt \
                --cert-fullchain "$fullchain" --cert-privkey "$privkey" >/dev/null
        else
            warn "certbot failed; falling back to a self-signed certificate"
            cert_selfsigned "$domain"
        fi
    fi
    _cert_install_deploy_hook "$domain"
}

cert_selfsigned() {
    local domain="${1:-$(state_get domain)}"
    local dir="/etc/hysteria"
    mkdir -p "$dir"
    openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 \
        -keyout "$dir/self.key" -out "$dir/self.crt" -days 3650 -nodes \
        -subj "/CN=${domain:-localhost}" >/dev/null 2>&1
    py set-meta --cert-mode selfsigned \
        --cert-fullchain "$dir/self.crt" --cert-privkey "$dir/self.key" >/dev/null
}

# Certbot runs every executable in renewal-hooks/deploy/ after ANY certificate
# it manages is (re)issued - no per-domain wiring, survives cert re-creation.
_cert_install_deploy_hook() {
    # make sure `xvei` is callable by an absolute path from the hook
    local bin="/usr/local/bin/xvei"
    [ -e "$bin" ] || ln -sf "$XVEI_ROOT/xvei.sh" "$bin"

    local dir="/etc/letsencrypt/renewal-hooks/deploy"
    mkdir -p "$dir"
    cat > "$dir/xvei-restart.sh" <<EOF
#!/bin/sh
# Installed by xvei: after a Let's Encrypt renewal, refresh services that
# hold the certificate open (xray, nginx, hysteria2).
exec "$bin" _renew-hook
EOF
    chmod +x "$dir/xvei-restart.sh"

    # Older certbot builds only honour the per-domain renew_hook line.
    local conf="/etc/letsencrypt/renewal/${1}.conf"
    if [ -f "$conf" ] && ! grep -qE '^\s*renew_hook' "$conf"; then
        echo "renew_hook = $bin _renew-hook" >> "$conf"
    fi
}

cert_hook_teardown() {
    rm -f /etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh
}

# called by certbot after a successful renewal (see xvei.sh `_renew-hook`)
cert_renew_hook_run() {
    log "Let's Encrypt certificate renewed - restarting services"
    if command -v hysteria >/dev/null 2>&1 && [ -f "$HY2_CONFIG" ]; then
        hy2_sync_cert
    fi
    systemctl restart xray.service 2>/dev/null || true
    command -v nginx >/dev/null 2>&1 && systemctl restart nginx.service 2>/dev/null || true
    systemctl is-enabled "$HY2_SERVICE" >/dev/null 2>&1 \
        && systemctl restart "$HY2_SERVICE" 2>/dev/null || true
    check_service xray || true
}
