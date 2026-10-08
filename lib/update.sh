# shellcheck shell=bash
# `xvei check-updates`: compare the installed xvei / xray / hysteria2 / geo
# data with the latest upstream versions and offer to update what is behind.
#
#   xvei      - installed commit (.commit, or HEAD of a git clone) vs branch head
#   xray      - `xray version` vs the latest XTLS/Xray-core release
#   hysteria2 - `hysteria version` vs the latest apernet/hysteria release
#   geo data  - sha256 of geoip.dat / geosite.dat vs the published checksums of
#               Loyalsoldier/v2ray-rules-dat (the source `update-geo` installs)

GEO_DIRS="/usr/local/share/xray /usr/share/xray"
GEO_REPO="Loyalsoldier/v2ray-rules-dat"

_UPD=()  # components with an update available

# Tag of the latest GitHub release, read from the /releases/latest redirect
# (not the API, so no rate limit).
_gh_latest_tag() {
    curl -fsSLI -o /dev/null -w '%{url_effective}' --max-time 10 \
        "https://github.com/$1/releases/latest" 2>/dev/null \
        | sed -n 's#.*/releases/tag/##p' | sed 's#%2[Ff]#/#g'
}

# _ver_lt A B : true when version A is older than B
_ver_lt() {
    [ "$1" != "$2" ] && [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -1)" = "$1" ]
}

_upd_row() {  # component installed latest status
    printf '  %-12s %-12s %-14s %s\n' "$1" "${2:--}" "${3:--}" "$4"
}

# _upd_cmp <component> <installed> <latest>
_upd_cmp() {
    local st
    if [ -z "$2" ] || [ -z "$3" ]; then st="unknown"
    elif _ver_lt "$2" "$3"; then st="update available"; _UPD+=("$1")
    else st="up to date"; fi
    _upd_row "$1" "$2" "$3" "$st"
}

_check_xvei() {
    local cur="" latest st
    latest="$(xvei_remote_sha)"
    if [ -d "$XVEI_ROOT/.git" ]; then
        cur="$(git -C "$XVEI_ROOT" rev-parse HEAD 2>/dev/null)"
        if [ -z "$latest" ] || [ -z "$cur" ]; then st="unknown"
        elif [ "$cur" = "$latest" ] \
            || git -C "$XVEI_ROOT" merge-base --is-ancestor "$latest" HEAD 2>/dev/null; then
            st="up to date"
        else st="update available (git clone: run git pull)"; fi
    else
        [ -f "$XVEI_ROOT/.commit" ] && cur="$(cat "$XVEI_ROOT/.commit")"
        if [ -z "$latest" ]; then st="unknown"
        elif [ -z "$cur" ]; then st="unknown installed commit, update to track it"; _UPD+=(xvei)
        elif [ "$cur" = "$latest" ]; then st="up to date"
        else st="update available"; _UPD+=(xvei); fi
    fi
    _upd_row xvei "${cur:0:7}" "${latest:0:7}" "$st"
}

_check_xray() {
    if ! xray_installed; then _upd_row xray "" "" "not installed"; return; fi
    local cur latest
    cur="$(xray version 2>/dev/null | awk 'NR==1{print $2}')"
    latest="$(_gh_latest_tag XTLS/Xray-core)"
    _upd_cmp xray "${cur#v}" "${latest##*v}"
}

_check_hy2() {
    if ! hy2_installed; then _upd_row hysteria2 "" "" "not installed"; return; fi
    local cur latest
    cur="$(hysteria version 2>/dev/null | awk '/^Version/{print $2}')"
    latest="$(_gh_latest_tag apernet/hysteria)"  # tags look like app/v2.6.1
    _upd_cmp hysteria2 "${cur#v}" "${latest##*v}"
}

_geo_file() {
    local d
    for d in $GEO_DIRS; do
        [ -f "$d/$1" ] && { echo "$d/$1"; return 0; }
    done
    return 1
}

# _check_geo <file> <latest release tag>
_check_geo() {
    local f sum st
    if ! f="$(_geo_file "$1")"; then _upd_row "$1" "" "" "not installed"; return; fi
    sum="$(curl -fsSL --max-time 10 \
        "https://github.com/$GEO_REPO/releases/latest/download/$1.sha256sum" 2>/dev/null \
        | awk '{print $1}' | grep -E '^[0-9a-f]{64}$')"
    if [ -z "$sum" ]; then st="unknown"
    elif [ "$(sha256sum "$f" | awk '{print $1}')" = "$sum" ]; then st="up to date"
    else st="update available"; _UPD+=(geo); fi
    _upd_row "$1" "$(date -r "$f" +%F)" "$2" "$st"
}

_update_xray() {
    log "updating xray-core"
    bash -c "$(curl -fsSL "$XRAY_INSTALL_URL")" @ install -u root || { err "xray update failed"; return 1; }
    if [ -f "$XRAY_CONFIG" ] && ! xray_test "$XRAY_CONFIG"; then
        warn "the new xray rejects the current config; check: xvei apply"
    fi
    xray_restart
    check_service xray || true
}

_update_hy2() {
    log "updating hysteria2"
    bash -c "$(curl -fsSL "$HY2_INSTALL_URL")" || { err "hysteria2 update failed"; return 1; }
    if systemctl is-enabled --quiet "$HY2_SERVICE" 2>/dev/null; then
        systemctl restart "$HY2_SERVICE"
        check_service "$HY2_SERVICE" || true
    fi
}

_apply_updates() {
    local c
    for c in "${_UPD[@]}"; do
        case "$c" in
            xray)      _update_xray ;;
            hysteria2) _update_hy2 ;;
            geo)       xray_update_geo && xray_restart && ok "geo data updated" ;;
        esac
    done
    # xvei last: it replaces the script files this process is running from
    if [[ " ${_UPD[*]} " == *" xvei "* ]]; then
        self_update
        ok "run xvei again to use the new version"
        exit 0
    fi
}

check_updates() {
    require_root
    _UPD=()
    log "checking for updates"
    echo
    _upd_row component installed latest status
    _check_xvei
    _check_xray
    _check_hy2
    local geo_tag; geo_tag="$(_gh_latest_tag "$GEO_REPO")"
    _check_geo geoip.dat "$geo_tag"
    _check_geo geosite.dat "$geo_tag"
    echo

    mapfile -t _UPD < <(printf '%s\n' "${_UPD[@]}" | awk 'NF && !seen[$0]++')
    if [ "${#_UPD[@]}" -eq 0 ]; then
        ok "nothing to update"
        return 0
    fi
    if have_tty && confirm "Install updates (${_UPD[*]})?" y; then
        _apply_updates
    else
        log "updates available: ${_UPD[*]}"
    fi
}
