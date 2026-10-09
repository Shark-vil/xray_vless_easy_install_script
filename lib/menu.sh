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

# qr_show <title> <link>: a titled QR code with the link under it
qr_show() {
    ui_header "QR $_s_sep $1"
    if command -v qrencode >/dev/null 2>&1; then
        if [ -n "${XVEI_ASCII:-}" ]; then
            qrencode -t ANSI "$2"
        else
            qrencode -t ANSIUTF8 "$2"
        fi
    else
        warn "qrencode is not installed; only the link is shown"
    fi
    echo "$2"
}

menu_links() {
    py show-links
    local picked
    # pick an inbound (and a client) for a QR code until Back
    while picked="$(py qr-pick)" && [ -n "$picked" ]; do
        qr_show "${picked%%$'\t'*}" "${picked#*$'\t'}"
    done
}

# _svc_line <label> <unit>: one service with its state, if it is installed
_svc_line() {
    systemctl cat "$2" >/dev/null 2>&1 || return 0
    if systemctl is-active --quiet "$2"; then
        printf '  %s%s%s %-12s %sactive%s\n' "$_c_ok" "$_s_on" "$_c_off" "$1" "$_c_ok" "$_c_off"
    else
        printf '  %s%s%s %-12s %sinactive%s\n' "$_c_err" "$_s_off" "$_c_off" "$1" "$_c_err" "$_c_off"
    fi
}

menu_status() {
    py summary
    ui_header "Services"
    _svc_line xray xray.service
    _svc_line hysteria2 "$HY2_SERVICE.service"
    _svc_line turnable "$TURNABLE_SERVICE.service"
    _svc_line nginx nginx.service
    _svc_line tor tor.service
    if command -v docker >/dev/null 2>&1 \
        && docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$WARP_CONTAINER"; then
        if docker ps --format '{{.Names}}' | grep -qx "$WARP_CONTAINER"; then
            printf '  %s%s%s %-12s %srunning%s\n' "$_c_ok" "$_s_on" "$_c_off" warp "$_c_ok" "$_c_off"
        else
            printf '  %s%s%s %-12s %sstopped%s\n' "$_c_err" "$_s_off" "$_c_off" warp "$_c_err" "$_c_off"
        fi
    fi
}

main_menu() {
    require_root
    if ! state_exists; then
        if xray_installed && [ -f "$XRAY_CONFIG" ]; then
            confirm "An existing Xray setup was found. Adopt it? (nothing is changed)" \
                && { wizard_install; return; }
        else
            confirm "xvei is not installed here. Run the installer now?" && { wizard_install; return; }
        fi
        return 0
    fi
    # a change staged by a run that never got to apply it is stale
    rm -f "$XRAY_PENDING" "$XRAY_PENDING.bak"
    while true; do
        local domain; domain="$(state_get domain)"
        ui_header "XVEI${domain:+ $_s_sep $domain}"
        ui_group "Configure"
        ui_opt 1 "Inbounds" "add / remove / list"
        ui_opt 2 "Outbounds" "WARP / TOR / share links"
        ui_opt 3 "Routing rules" "block / direct / tunnels"
        ui_opt 4 "Routing template" "country / popular, exit mode"
        ui_opt 5 "Camouflage site" "auth / static preset / reverse proxy"
        ui_group "View"
        ui_opt 6 "Links / QR codes"
        ui_opt 7 "Status" "summary and services"
        ui_opt 8 "config.json"
        ui_group "Maintenance"
        ui_opt 9 "Firewall" "open ports / lockdown (optional)"
        ui_opt 10 "Updates" "xvei / xray / hysteria2 / geo data"
        ui_opt 11 "Backups" "view / compare / roll back / back up now"
        ui_opt 12 "Uninstall xvei"
        ui_back Exit
        local c; c="$(read_value "Choose" 0)"
        case "$c" in
            1) py menu inbounds;  _menu_apply_if_changed $? ;;
            2) py menu outbounds; _menu_apply_if_changed $? ;;
            3) py menu rules;     _menu_apply_if_changed $? ;;
            4) py menu template;  _menu_apply_if_changed $? ;;
            5) py menu site;      _menu_apply_if_changed $? ;;
            6) menu_links ;;
            7) menu_status ;;
            8) show_config ;;
            9) menu_firewall ;;
            10) check_updates ;;
            11) py menu backups;  _menu_apply_if_changed $? ;;
            12) xvei_remove && exit 0 ;;
            0|"") return 0 ;;
            *) warn "unknown choice" ;;
        esac
    done
}
