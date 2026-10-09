# shellcheck shell=bash
# Tor as a local SOCKS5 (127.0.0.1:9050).

tor_up() {
    ensure_bin tor
    # a tor that was already running is not ours to stop later
    systemctl is-active --quiet tor || systemctl is-active --quiet tor@default \
        || mark_managed tor
    systemctl enable --now tor 2>/dev/null || systemctl enable --now tor@default 2>/dev/null || true
    ok "tor running (SOCKS5 127.0.0.1:9050)"
}

tor_down() {
    command -v tor >/dev/null 2>&1 || return 0
    xvei_owns tor || return 0
    systemctl is-active --quiet tor || systemctl is-active --quiet tor@default || return 0
    systemctl disable --now tor 2>/dev/null || true
    systemctl disable --now tor@default 2>/dev/null || true
    unmark_managed tor
    ok "tor stopped"
}
