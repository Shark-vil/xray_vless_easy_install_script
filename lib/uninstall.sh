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
        echo "  - xvei code: $INSTALL_DIR"
    else
        echo "  - (the git clone $XVEI_ROOT stays; delete it yourself if you like)"
    fi
    echo "  - command: /usr/local/bin/xvei"
}

_plan_self() {
    echo "Remove only xvei:"
    echo "  - xvei state: $XVEI_STATE"
    echo "  - xvei markers and package list: /var/lib/xvei/{managed,packages}"
    [ -d "$LEGACY_CLIENT_DIR" ] && echo "  - client files of older versions: $LEGACY_CLIENT_DIR"
    [ -e /etc/letsencrypt/renewal-hooks/deploy/xvei-restart.sh ] \
        && echo "  - certbot hook that calls xvei (replaced by a standalone restart-xray.sh)"
    _xvei_code_note
    echo "Kept and still running as now: Xray and $XRAY_CONFIG, nginx and the"
    echo "site, WARP, TOR, Hysteria2, Turnable, certificates, firewall rules."
}

_plan_all() {
    echo "Remove xvei and what it set up:"
    if state_exists && is_adopted; then
        echo "  - only what xvei added to this adopted setup: its WARP / TOR /"
        echo "    Hysteria2 / Turnable (if xvei started them), its nginx site,"
        echo "    certbot hooks"
        echo "  - xvei state; you are asked whether to restore $XRAY_CONFIG.xvei-orig"
        echo "  Xray itself and its config stay."
    else
        echo "  - Xray (package, service, $XRAY_DIR including config.json)"
        echo "  - Hysteria2, Turnable, WARP container, TOR - whichever xvei set up"
        echo "  - xvei's nginx site, certbot hooks"
    fi
    _xvei_code_note
    echo "Kept: certificates in /etc/letsencrypt, firewall rules."
    local pk; pk="$(_removable_pkgs | xargs)"
    [ -n "$pk" ] && echo "Packages xvei installed (removed only if you agree, or with --packages): $pk"
    return 0
}

# the xvei files both modes remove; the code goes last
_remove_xvei_files() {
    rm -f "$XVEI_STATE" "$XVEI_STATE.bak"
    rm -rf "$XVEI_MARKERS" "$XVEI_PKG_LIST" "$LEGACY_CLIENT_DIR"
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
    echo
    if [ "$mode" = self ]; then
        _plan_self
        echo "(to remove xvei together with Xray and everything it set up: xvei remove --all)"
    else
        _plan_all
    fi
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
