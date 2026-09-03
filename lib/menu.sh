# shellcheck shell=bash
# Interactive editor. Each section delegates state mutation to the python engine
# and runs apply_all() whenever something changed.

_menu_apply_if_changed() {
    local rc=$1
    case $rc in
        0) apply_all ;;
        2) log "no changes" ;;
        *) err "operation failed" ;;
    esac
}

menu_links() {
    mapfile -t tags < <(py list-inbounds | cut -f1)
    if [ "${#tags[@]}" -eq 0 ]; then warn "no inbounds"; return; fi
    py show-links
    echo
    local t; t="$(read_value "QR for which tag (empty to skip)")"
    [ -n "$t" ] || return 0
    local link_file="$CLIENT_DIR/$t.link"
    if [ -f "$link_file" ]; then
        qrencode -t ANSIUTF8 "$(cat "$link_file")"
    else
        warn "no link file $link_file"
    fi
}

menu_status() {
    py summary
    echo
    systemctl is-active --quiet xray && ok "xray: active" || err "xray: inactive"
    if command -v hysteria >/dev/null 2>&1; then
        systemctl is-active --quiet "$HY2_SERVICE" && ok "hysteria2: active" || warn "hysteria2: inactive"
    fi
    if command -v nginx >/dev/null 2>&1; then
        systemctl is-active --quiet nginx && ok "nginx: active" || warn "nginx: inactive"
    fi
}

main_menu() {
    require_root
    if ! state_exists; then
        confirm "xvei is not installed here. Run the installer now?" && { wizard_install; return; }
        return 0
    fi
    while true; do
        echo
        echo "== XVEI =="
        echo " 1) Inbounds        (add / remove / list)"
        echo " 2) Outbounds       (WARP / TOR)"
        echo " 3) Routing rules   (block / tunnel warp / tunnel tor / direct)"
        echo " 4) Routing template (country / popular direct) & exit mode"
        echo " 5) Camouflage site (auth / static preset / reverse-proxy)"
        echo " 6) Show links / QR"
        echo " 7) Status"
        echo " 8) Update geo data"
        echo " 9) Uninstall xvei"
        echo " 0) Exit"
        local c; c="$(read_value "Choose")"
        case "$c" in
            1) py menu inbounds;  _menu_apply_if_changed $? ;;
            2) py menu outbounds; _menu_apply_if_changed $? ;;
            3) py menu rules;     _menu_apply_if_changed $? ;;
            4) py menu template;  _menu_apply_if_changed $? ;;
            5) py menu site;      _menu_apply_if_changed $? ;;
            6) menu_links ;;
            7) menu_status ;;
            8) xray_update_geo && xray_restart && ok "geo updated" ;;
            9) confirm "Really uninstall xvei and all services?" n && { xvei_remove; return; } ;;
            0|"") return 0 ;;
            *) warn "unknown choice" ;;
        esac
    done
}
