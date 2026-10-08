# shellcheck shell=bash
# nginx fallback target for the vless-tls fallbacks: HTTP/1.1 on 127.0.0.1:8080,
# cleartext HTTP/2 (h2c) on 127.0.0.1:8081. Xray splits the two by ALPN.
# The vhost + optional static "camouflage" site come from the python engine
# (see pyengine/sites.py).

WEBROOT="/var/www/xvei-site"

# Debian/Ubuntu include sites-enabled/; RHEL/CentOS/Fedora have no such
# directory and only include conf.d/*.conf.
_nginx_site_path() {
    if [ -d /etc/nginx/sites-enabled ]; then
        echo "/etc/nginx/sites-enabled/xvei.conf"
    else
        echo "/etc/nginx/conf.d/xvei.conf"
    fi
}

_nginx_deploy_site() {
    local src; src="$(py site-assets 2>/dev/null)"
    if [ -n "$src" ] && [ -d "$src" ]; then
        log "deploying camouflage site from $(basename "$src")"
        rm -rf "$WEBROOT"
        mkdir -p "$WEBROOT"
        cp -rT "$src" "$WEBROOT"
        local u
        for u in www-data nginx http; do
            if id "$u" >/dev/null 2>&1; then chown -R "$u:" "$WEBROOT" 2>/dev/null; break; fi
        done
        find "$WEBROOT" -type f -exec chmod 644 {} + 2>/dev/null || true
        find "$WEBROOT" -type d -exec chmod 755 {} + 2>/dev/null || true
    fi
}

# SELinux (CentOS/RHEL/Fedora): nginx may only bind ports labelled http_port_t
# (8081 is transproxy_port_t out of the box) and may not open outbound
# connections - which the reverse-proxy site needs - unless
# httpd_can_network_connect is on.
_nginx_selinux() {
    command -v getenforce >/dev/null 2>&1 || return 0
    [ "$(getenforce 2>/dev/null)" = "Enforcing" ] || return 0
    command -v semanage >/dev/null 2>&1 || pkg_install policycoreutils-python-utils || true
    if command -v semanage >/dev/null 2>&1; then
        local labelled p
        labelled="$(semanage port -l 2>/dev/null | awk '$1=="http_port_t" && $2=="tcp"')"
        for p in 8080 8081; do
            grep -qE "[ ,]$p(,|$)" <<<"$labelled" && continue
            log "SELinux: allowing nginx to listen on $p"
            semanage port -a -t http_port_t -p tcp "$p" 2>/dev/null \
                || semanage port -m -t http_port_t -p tcp "$p" 2>/dev/null || true
        done
    else
        warn "SELinux is enforcing but semanage is missing; nginx may fail to bind 8080/8081"
    fi
    if [ "$(state_get site.type)" = "proxy" ]; then
        setsebool -P httpd_can_network_connect 1 2>/dev/null || true
    fi
    [ -d "$WEBROOT" ] && restorecon -R "$WEBROOT" 2>/dev/null || true
}

nginx_setup() {
    ensure_bin nginx
    local site; site="$(_nginx_site_path)"
    log "writing nginx fallback vhost -> $site"
    [ -e "$NGINX_SITE_ENABLED" ] && rm -f "$NGINX_SITE_ENABLED"
    _nginx_deploy_site
    if ! py nginx-conf > "$site"; then
        err "failed to render nginx vhost"; return 1
    fi
    _nginx_selinux
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
    rm -f /etc/nginx/sites-enabled/xvei.conf /etc/nginx/conf.d/xvei.conf
    rm -rf "$WEBROOT"
    if [ -e "$NGINX_SITE_AVAILABLE" ] && [ ! -e "$NGINX_SITE_ENABLED" ]; then
        ln -s "$NGINX_SITE_AVAILABLE" "$NGINX_SITE_ENABLED"
    fi
    systemctl restart nginx 2>/dev/null || true
}
