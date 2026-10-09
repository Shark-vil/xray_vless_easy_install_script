# shellcheck shell=bash
# Adopting an Xray setup that existed before xvei, and ownership markers.
#
# Adopting changes nothing: no packages besides Python, no config rewrite, no
# restart. The existing config.json becomes the "base" in the state; later
# edits made through xvei are merged into it (see pyengine/xrayconf.py).

XVEI_MARKERS="/var/lib/xvei/managed"

is_adopted() { [ "$(state_get adopted)" = "True" ]; }

# xvei set this component (warp / tor / hysteria2) up itself
mark_managed()   { mkdir -p "$XVEI_MARKERS" && touch "$XVEI_MARKERS/$1"; }
unmark_managed() { rm -f "$XVEI_MARKERS/$1"; }

# xvei_owns <component>: may xvei stop / remove it? On a regular install xvei
# owns everything it manages; on an adopted one only what it started itself.
xvei_owns() {
    [ -e "$XVEI_MARKERS/$1" ] && return 0
    ! is_adopted
}

# Refuse setups xvei cannot take over safely - nothing is changed either way.
adopt_preflight() {
    local unit
    for unit in x-ui 3x-ui; do
        if systemctl cat "$unit.service" >/dev/null 2>&1; then
            die "Xray here is managed by a panel ($unit), which rewrites its config; xvei will not take it over. Nothing was changed."
        fi
    done
    local exec cfg
    exec="$(systemctl show -p ExecStart --value xray.service 2>/dev/null)"
    if [[ "$exec" == *"-confdir"* ]]; then
        die "xray.service uses -confdir (a split config); xvei supports a single config file. Nothing was changed."
    fi
    cfg="$(grep -oE -- '(-config|-c)[= ]+[^ ;]+' <<<"$exec" | head -1 | sed -E 's/^(-config|-c)[= ]+//')"
    if [ -n "$cfg" ] && [ "$cfg" != "$XRAY_CONFIG" ]; then
        die "xray.service reads $cfg, xvei works with $XRAY_CONFIG. Nothing was changed."
    fi
}

adopt_existing() {
    log "found an existing Xray setup without xvei state: $XRAY_CONFIG"
    if ! find_python >/dev/null; then
        pkg_update
        ensure_python
    fi
    py adopt --config "$XRAY_CONFIG" || die "could not read $XRAY_CONFIG; nothing was changed"
    py set-meta --server-ip "$(server_ip)" >/dev/null 2>&1 || true
    [ -e /usr/local/bin/xvei ] || ln -sf "$XVEI_ROOT/xvei.sh" /usr/local/bin/xvei
    echo
    py summary
    echo
    ok "adopted: nothing was installed, rewritten or restarted"
    log "edits made through xvei are merged into this config; before the first"
    log "write the original is saved as $XRAY_CONFIG.xvei-orig"
}

# `xvei remove` on an adopted setup: undo only what xvei added
remove_adopted() {
    log "this Xray setup was adopted: removing only what xvei added"
    xvei_owns hysteria2 && hy2_remove_pkg
    turnable_down
    warp_down
    tor_down
    nginx_teardown
    cert_hook_teardown
    if [ -f "$XRAY_CONFIG.xvei-orig" ] \
        && confirm "Restore the original config.json (as it was before xvei)?" y; then
        cp -f "$XRAY_CONFIG.xvei-orig" "$XRAY_CONFIG"
        xray_restart
        check_service xray || true
    fi
    rm -f "$XVEI_STATE" "$XVEI_STATE.bak"
    rm -rf "$CLIENT_DIR" "$XVEI_MARKERS"
    ok "xvei removed; Xray itself stays installed"
}
