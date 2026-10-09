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
    command -v certbot >/dev/null 2>&1 && _cert_enable_renew_timer
}

# Debian/Ubuntu's certbot enables its renewal timer itself; the Fedora/EPEL
# build ships certbot-renew.timer disabled, so the certificate would silently
# expire after 90 days.
_cert_enable_renew_timer() {
    local t
    for t in certbot.timer certbot-renew.timer snap.certbot.renew.timer; do
        if systemctl cat "$t" >/dev/null 2>&1; then
            systemctl enable --now "$t" >/dev/null 2>&1 || true
            return 0
        fi
    done
    warn "no certbot renewal timer found; schedule 'certbot renew' yourself (cron)"
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

    # Renewal reuses the standalone authenticator, which needs :80. On
    # RHEL-family systems the stock nginx.conf keeps its own server on :80,
    # so stop nginx for the challenge - only if it really holds the port.
    mkdir -p /etc/letsencrypt/renewal-hooks/pre /etc/letsencrypt/renewal-hooks/post
    cat > /etc/letsencrypt/renewal-hooks/pre/xvei-free-port80.sh <<'EOF'
#!/bin/sh
# Installed by xvei: free :80 for the standalone renewal challenge.
if ss -ltnpH 'sport = :80' 2>/dev/null | grep -q nginx; then
    systemctl stop nginx && touch /run/xvei-nginx-stopped
fi
EOF
    cat > /etc/letsencrypt/renewal-hooks/post/xvei-free-port80.sh <<'EOF'
#!/bin/sh
# Installed by xvei: bring nginx back if the pre hook stopped it.
if [ -e /run/xvei-nginx-stopped ]; then
    rm -f /run/xvei-nginx-stopped
    systemctl start nginx
fi
EOF
    chmod +x /etc/letsencrypt/renewal-hooks/pre/xvei-free-port80.sh              /etc/letsencrypt/renewal-hooks/post/xvei-free-port80.sh

    # Older certbot builds only honour the per-domain renew_hook line.
    local conf="/etc/letsencrypt/renewal/${1}.conf"
    if [ -f "$conf" ] && ! grep -qE '^\s*renew_hook' "$conf"; then
        echo "renew_hook = $bin _renew-hook" >> "$conf"
    fi
}

# `xvei remove` (only xvei): certificates keep being renewed, but the deploy hook
# calls xvei - swap it for a standalone one that does the same restarts.
cert_hook_standalone() {
    local old="/etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh"
    [ -e "$old" ] || return 0
    local hy2=""
    if [ -f "$HY2_CONFIG" ] && [ "$(state_get cert.mode)" = "letsencrypt" ]; then
        hy2="install -m 644 \"$(state_get cert.fullchain)\" $HY2_DIR/cert.crt
install -m 640 \"$(state_get cert.privkey)\" $HY2_DIR/cert.key
chgrp hysteria $HY2_DIR/cert.key 2>/dev/null || chmod 644 $HY2_DIR/cert.key"
    fi
    cat > /etc/letsencrypt/renewal-hooks/deploy/restart-xray.sh <<EOF
#!/bin/sh
# Left by xvei on uninstall: after a Let's Encrypt renewal, restart the
# services that hold the certificate open.
$hy2
systemctl restart xray.service 2>/dev/null || true
systemctl is-active --quiet nginx && systemctl restart nginx.service
systemctl is-enabled --quiet $HY2_SERVICE 2>/dev/null && systemctl restart $HY2_SERVICE
exit 0
EOF
    chmod +x /etc/letsencrypt/renewal-hooks/deploy/restart-xray.sh
    rm -f "$old"
    _cert_drop_renew_hook_line
}

# the per-domain line _cert_install_deploy_hook adds for older certbot builds
_cert_drop_renew_hook_line() {
    local f
    for f in /etc/letsencrypt/renewal/*.conf; do
        [ -f "$f" ] && sed -i '/^\s*renew_hook\s*=.*xvei _renew-hook/d' "$f"
    done
    return 0
}

cert_hook_teardown() {
    _cert_drop_renew_hook_line
    rm -f /etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh           /etc/letsencrypt/renewal-hooks/pre/xvei-free-port80.sh           /etc/letsencrypt/renewal-hooks/post/xvei-free-port80.sh
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
