# shellcheck shell=bash
# `xvei remove`: uninstall only xvei itself (the default), or with --all xvei
# together with what it set up. Always shows the plan and asks first.
#
#   (default)   only xvei: its code, command, state and markers. Xray and
#               everything else keep running with the current config.
#   --all       xvei and what it set up (on an adopted setup only what xvei
#               added - Xray itself stays), optionally the packages it installed
#   --yes       do not ask (needed without a terminal)
#   --packages  with --all --yes: also remove the packages xvei installed

# never removed, even if xvei installed them: the system needs them, or
# removing them would drop the firewall
_KEEP_PKGS=" curl tar openssl python3 python39 python3.11 python311 ufw firewalld epel-release policycoreutils-python-utils "
_DOCKER_PKGS="docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras"

# packages xvei installed that are still installed and may go
_removable_pkgs() {
    local p
    [ -f "$XVEI_PKG_LIST" ] || return 0
    while read -r p; do
        [ -n "$p" ] || continue
        [[ "$_KEEP_PKGS" == *" $p "* ]] && continue
        if [ "$p" = docker ]; then
            command -v docker >/dev/null 2>&1 && echo docker
        elif command -v "$p" >/dev/null 2>&1; then
            echo "$p"
        fi
    done < "$XVEI_PKG_LIST"
}

_remove_pkgs() {
    local p
    for p in "$@"; do
        if [ "$p" = docker ]; then
            if [ -n "$(docker ps -aq 2>/dev/null)" ]; then
                warn "docker still has containers that xvei did not create; docker kept"
                continue
            fi
            # shellcheck disable=SC2086
            pkg_remove $_DOCKER_PKGS || warn "could not remove docker"
        else
            pkg_remove "$p" || warn "could not remove $p"
        fi
    done
}

_xvei_code_note() {
    if [ "$XVEI_ROOT" = "$INSTALL_DIR" ]; then
        ui_li "xvei code: $INSTALL_DIR"
    fi
    ui_li "the xvei command: /usr/local/bin/xvei"
}

_plan_self() {
    ui_header "Uninstall xvei"
    ui_group "Removed"
    ui_li "xvei state: $XVEI_STATE"
    ui_li "xvei markers and package list: /var/lib/xvei/{managed,packages}"
    [ -d "$XRAY_DIR/xvei-backups" ] && ui_li "xvei's backups: $XRAY_DIR/xvei-backups"
    [ -d "$LEGACY_CLIENT_DIR" ] && ui_li "client files of older versions: $LEGACY_CLIENT_DIR"
    [ -e /etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh ] \
        && ui_li "certbot hook that calls xvei (replaced by a standalone restart-xray.sh)"
    _xvei_code_note
    ui_group "Kept and still running as now"
    ui_li "Xray and $XRAY_CONFIG"
    ui_li "nginx and the site, WARP, TOR, Hysteria2, Turnable"
    ui_li "certificates, firewall rules"
    [ "$XVEI_ROOT" = "$INSTALL_DIR" ] || ui_li "the git clone $XVEI_ROOT (delete it yourself if you like)"
    echo
    ui_dim "To remove xvei together with Xray and everything it set up: xvei remove --all"
}

_plan_all() {
    ui_header "Uninstall xvei and everything it set up"
    ui_group "Removed"
    if state_exists && is_adopted; then
        ui_li "what xvei added to this adopted setup: WARP / TOR / Hysteria2 /"
        ui_li "Turnable (only if xvei started them), its nginx site, certbot hooks"
        ui_li "xvei state (you are asked whether to restore $XRAY_CONFIG.xvei-orig)"
    else
        ui_li "Xray (package, service, $XRAY_DIR including config.json)"
        ui_li "Hysteria2, Turnable, the WARP container, TOR (whichever xvei set up)"
        ui_li "xvei's nginx site, certbot hooks"
    fi
    _xvei_code_note
    ui_group "Kept"
    is_adopted 2>/dev/null && ui_li "Xray itself and its config"
    ui_li "certificates in /etc/letsencrypt, firewall rules"
    [ "$XVEI_ROOT" = "$INSTALL_DIR" ] || ui_li "the git clone $XVEI_ROOT (delete it yourself if you like)"
    local pk; pk="$(_removable_pkgs | xargs)"
    if [ -n "$pk" ]; then
        ui_group "Packages xvei installed (asked separately, or --packages)"
        ui_li "$pk"
    fi
    return 0
}

# the xvei files both modes remove; the code goes last
_remove_xvei_files() {
    rm -f "$XVEI_STATE" "$XVEI_STATE.bak"
    rm -rf "$XVEI_MARKERS" "$XVEI_PKG_LIST" "$LEGACY_CLIENT_DIR" "$XRAY_DIR/xvei-backups"
    rmdir /var/lib/xvei 2>/dev/null || true
    if [ "$(readlink -f /usr/local/bin/xvei 2>/dev/null)" = "$(readlink -f "$XVEI_ROOT/xvei.sh")" ]; then
        rm -f /usr/local/bin/xvei
    fi
    # bash already holds this script open, so deleting the tree is safe
    [ "$XVEI_ROOT" = "$INSTALL_DIR" ] && rm -rf "$INSTALL_DIR"
    return 0
}

_remove_all() {
    local packages="$1" assume_yes="$2" pk
    # read before the teardown: the package list goes with the xvei files
    pk="$(_removable_pkgs | xargs)"
    if state_exists && is_adopted; then
        remove_adopted
    else
        log "stopping services"
        systemctl disable --now xray.service 2>/dev/null || true
        hy2_remove_pkg
        turnable_down
        warp_down
        tor_down
        xray_remove_pkg
        nginx_teardown
        cert_hook_teardown
        rm -rf "$XRAY_DIR" "$HY2_DIR"
    fi
    rm -rf "$WARP_DATA"
    if [ -n "$pk" ]; then
        if [ "$packages" = 1 ] || { [ "$assume_yes" = 0 ] && have_tty \
                && confirm "Also remove the packages xvei installed ($pk)?" n; }; then
            # shellcheck disable=SC2086
            _remove_pkgs $pk
        else
            log "packages kept: $pk"
        fi
    fi
}

xvei_remove() {
    require_root
    local mode=self assume_yes=0 packages=0 arg
    for arg in "$@"; do
        case "$arg" in
            --all)      mode=all ;;
            --yes|-y)   assume_yes=1 ;;
            --packages) packages=1 ;;
            *) die "unknown option: $arg (use [--all [--packages]] [--yes])" ;;
        esac
    done
    [ "$packages" = 1 ] && [ "$mode" != all ] && die "--packages only goes with --all"
    if [ "$mode" = self ]; then _plan_self; else _plan_all; fi
    echo
    if [ "$assume_yes" = 0 ]; then
        have_tty || die "nothing removed: confirm with --yes when there is no terminal"
        confirm "Proceed? This cannot be undone" n || { log "cancelled, nothing removed"; return 1; }
    fi

    if [ "$mode" = self ]; then
        cert_hook_standalone
    else
        _remove_all "$packages" "$assume_yes"
    fi
    _remove_xvei_files
    ok "xvei removed$([ "$mode" = all ] && echo " with everything it set up")"
}
