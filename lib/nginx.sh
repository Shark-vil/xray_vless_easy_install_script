# shellcheck shell=bash
# nginx fallback target for the vless-tls fallbacks: HTTP/1.1 on 127.0.0.1:8080,
# cleartext HTTP/2 (h2c) on 127.0.0.1:8081. Xray splits the two by ALPN.
# The vhost + optional static "camouflage" site come from the python engine
# (see pyengine/sites.py).

WEBROOT="/var/www/xvei-site"

nginx_needed() {
    local n; n="$(py needs 2>/dev/null)"
    [[ " $n " == *" cert "* ]]
}

_nginx_deploy_site() {
    local src; src="$(py site-assets 2>/dev/null)"
    if [ -n "$src" ] && [ -d "$src" ]; then
        log "deploying camouflage site from $(basename "$src")"
        rm -rf "$WEBROOT"
        mkdir -p "$WEBROOT"
        cp -rT "$src" "$WEBROOT"
        chown -R www-data:www-data "$WEBROOT" 2>/dev/null || true
        find "$WEBROOT" -type f -exec chmod 644 {} + 2>/dev/null || true
        find "$WEBROOT" -type d -exec chmod 755 {} + 2>/dev/null || true
    fi
}

nginx_setup() {
    ensure_bin nginx
    log "writing nginx fallback vhost -> $NGINX_XVEI_SITE"
    [ -e "$NGINX_SITE_ENABLED" ] && rm -f "$NGINX_SITE_ENABLED"
    _nginx_deploy_site
    if ! py nginx-conf > "$NGINX_XVEI_SITE"; then
        err "failed to render nginx vhost"; return 1
    fi
    if nginx -t 2>/dev/null; then
        systemctl restart nginx
        systemctl enable nginx >/dev/null 2>&1 || true
        check_service nginx || true
    else
        err "nginx config test failed:"; nginx -t || true
        return 1
    fi
}

nginx_teardown() {
    [ -e "$NGINX_XVEI_SITE" ] && rm -f "$NGINX_XVEI_SITE"
    rm -rf "$WEBROOT"
    if [ -e "$NGINX_SITE_AVAILABLE" ] && [ ! -e "$NGINX_SITE_ENABLED" ]; then
        ln -s "$NGINX_SITE_AVAILABLE" "$NGINX_SITE_ENABLED"
    fi
    systemctl restart nginx 2>/dev/null || true
}
