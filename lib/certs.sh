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
    _cert_renew_hook "$domain"
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

_cert_renew_hook() {
    local domain="$1"
    local conf="/etc/letsencrypt/renewal/$domain.conf"
    [ -f "$conf" ] || return 0
    local line="renew_hook = /usr/local/bin/xvei _renew-hook"
    if grep -qE '^\s*renew_hook' "$conf"; then
        sed -i "s|^\s*renew_hook.*|$line|" "$conf"
    else
        echo "$line" >> "$conf"
    fi
}

# called by certbot after a successful renewal (see xvei.sh dispatch)
cert_renew_hook_run() {
    systemctl reload xray 2>/dev/null || systemctl restart xray 2>/dev/null || true
    if command -v hysteria >/dev/null 2>&1 && [ -f "$HY2_CONFIG" ]; then
        hy2_sync_cert
        systemctl restart "$HY2_SERVICE" 2>/dev/null || true
    fi
}
