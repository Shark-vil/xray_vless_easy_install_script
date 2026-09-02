#!/usr/bin/env bash
# xvei - modular Xray (+ Hysteria2) installer / live editor.
# Repo: https://github.com/Shark-vil/xray_vless_easy_install_script

# No `set -e`: this is an interactive tool and many helpers legitimately return
# non-zero (e.g. the python engine returns 2 for "no change").
set -o pipefail

REPO_SLUG="Shark-vil/xray_vless_easy_install_script"
REPO_BRANCH="master"
INSTALL_DIR="/usr/local/lib/xvei"

# --- resolve our own location -------------------------------------------
_resolve_root() {
    local src="${BASH_SOURCE[0]}"
    while [ -h "$src" ]; do
        local dir; dir="$(cd -P "$(dirname "$src")" && pwd)"
        src="$(readlink "$src")"; [[ $src != /* ]] && src="$dir/$src"
    done
    cd -P "$(dirname "$src")" && pwd
}
XVEI_ROOT="$(_resolve_root)"
export XVEI_ROOT

# --- bootstrap: fetch the modular tree when run via curl|bash ----------
bootstrap() {
    [ "$(id -u)" -eq 0 ] || { echo "run as root" >&2; exit 1; }
    echo "[xvei] fetching $REPO_SLUG@$REPO_BRANCH -> $INSTALL_DIR"
    command -v curl >/dev/null 2>&1 || { echo "curl required" >&2; exit 1; }
    command -v tar  >/dev/null 2>&1 || { echo "tar required"  >&2; exit 1; }
    mkdir -p "$INSTALL_DIR"
    curl -fsSL "https://github.com/$REPO_SLUG/archive/refs/heads/$REPO_BRANCH.tar.gz" \
        | tar -xz -C "$INSTALL_DIR" --strip-components=1
    ln -sf "$INSTALL_DIR/xvei.sh" /usr/local/bin/xvei
    chmod +x "$INSTALL_DIR/xvei.sh"
    exec bash "$INSTALL_DIR/xvei.sh" "$@"
}

if [ ! -f "$XVEI_ROOT/lib/common.sh" ]; then
    bootstrap "$@"
fi

# --- load modules ------------------------------------------------------
# shellcheck source=lib/common.sh
for m in common deps xray nginx certs hysteria2 warp tor apply menu; do
    # shellcheck disable=SC1090
    source "$XVEI_ROOT/lib/$m.sh"
done

# --- high level flows ------------------------------------------------
wizard_install() {
    require_root
    ensure_core_deps
    xray_install
    py init >/dev/null 2>&1 || true
    py wizard
    py set-meta --server-ip "$(server_ip)" >/dev/null || true
    apply_all
    echo
    menu_status
    echo
    py show-links
    echo
    ok "Client files: $CLIENT_DIR"
}

xvei_remove() {
    require_root
    log "stopping services"
    systemctl disable --now xray.service 2>/dev/null || true
    hy2_remove_pkg
    warp_down
    tor_down
    xray_remove_pkg
    nginx_teardown
    cert_hook_teardown
    rm -rf "$XRAY_DIR" "$HY2_DIR" "$CLIENT_DIR"
    ok "xvei removed"
}

self_update() {
    require_root
    [ -d "$INSTALL_DIR" ] || die "not a bootstrapped install ($INSTALL_DIR missing)"
    curl -fsSL "https://github.com/$REPO_SLUG/archive/refs/heads/$REPO_BRANCH.tar.gz" \
        | tar -xz -C "$INSTALL_DIR" --strip-components=1
    ln -sf "$INSTALL_DIR/xvei.sh" /usr/local/bin/xvei
    ok "updated $INSTALL_DIR"
}

_apply_after() {
    # run a py mutation, then apply_all iff it changed state.
    # The engine opens /dev/tty itself for any prompts it needs.
    py "$@"
    local rc=$?
    case $rc in
        0) apply_all ;;
        2) log "no change" ;;
        *) exit "$rc" ;;
    esac
}

print_help() {
    cat <<'EOF'
xvei - Xray + Hysteria2 installer / live editor

  xvei                     open the interactive menu (or offer to install)
  xvei install             guided first-time setup
  xvei edit                interactive menu
  xvei apply               regenerate + validate + restart from the current state

  xvei add-inbound  <type> [--port N] [--dest SNI] [--method M]
       types: vless-tls vless-ws vless-xhttp-reality vless-xhttp-tls
              shadowsocks hysteria2
  xvei remove-inbound <tag>
  xvei add-outbound   <warp|tor>
  xvei remove-outbound <warp|tor>
  xvei rule <add|remove|list> <block|warp|tor|direct> [matcher ...]
  xvei template <russia|iran|china|none> [--tunnel <warp|tor> | --direct]
  xvei site [list | auth | blank | 404 | <preset> | proxy <url|preset>]
       presets: nebula critters game2048 snake notes

  xvei links [tag]         print client share links
  xvei qr <tag>            print a QR code for one inbound
  xvei status              services + active template
  xvei set-meta [--domain D --email E ...]
  xvei update-geo          refresh geoip/geosite
  xvei self-update         re-fetch the script tree
  xvei remove              uninstall everything
EOF
}

# --- dispatch --------------------------------------------------------
cmd="${1:-}"; shift || true
case "$cmd" in
    ""|edit|menu)        main_menu ;;
    install)             wizard_install ;;
    apply)               apply_all ;;
    add-inbound)         _apply_after add-inbound "$@" ;;
    remove-inbound)      _apply_after remove-inbound "$@" ;;
    add-outbound)        _apply_after add-outbound "$@" ;;
    remove-outbound)     _apply_after remove-outbound "$@" ;;
    rule)                _apply_after rule "$@" ;;
    template)            _apply_after template "$@" ;;
    site)                if [ "${1:-list}" = "list" ]; then py site list
                         else _apply_after site "$@"; fi ;;
    set-meta)            _apply_after set-meta "$@" ;;
    links)               py show-links ${1:+--tag "$1"} ;;
    qr)                  [ -n "${1:-}" ] || die "usage: xvei qr <tag>"
                         f="$CLIENT_DIR/$1.link"
                         [ -f "$f" ] || die "no link file: $f"
                         qrencode -t ANSIUTF8 "$(cat "$f")" ;;
    status)              menu_status ;;
    update-geo)          require_root; xray_update_geo; xray_restart; ok "geo updated" ;;
    self-update)         self_update ;;
    remove|uninstall)    xvei_remove ;;
    _renew-hook)         require_root; cert_renew_hook_run ;;
    help|-h|--help)      print_help ;;
    *)                   err "unknown command: $cmd"; print_help; exit 1 ;;
esac
