# shellcheck shell=bash
# Package-manager abstraction and dependency installation.

_PKG=""
detect_pkg() {
    [ -n "$_PKG" ] && return 0
    for p in apt-get dnf yum zypper pacman; do
        if command -v "$p" >/dev/null 2>&1; then _PKG="$p"; return 0; fi
    done
    die "no supported package manager (apt/dnf/yum/zypper/pacman)"
}

pkg_update() {
    detect_pkg
    log "refreshing package lists ($_PKG)"
    case "$_PKG" in
        apt-get) apt-get update -qq ;;
        dnf|yum) "$_PKG" -q check-update || true ;;
        zypper)  zypper --non-interactive refresh ;;
        pacman)  pacman -Sy --noconfirm ;;
    esac
}

pkg_install() {
    detect_pkg
    local pkg="$1"
    log "installing '$pkg'"
    case "$_PKG" in
        apt-get) DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$pkg" ;;
        dnf|yum) "$_PKG" install -y "$pkg" ;;
        zypper)  zypper --non-interactive install "$pkg" ;;
        pacman)  pacman -S --noconfirm --needed "$pkg" ;;
    esac
}

# ensure_bin <binary> [package]
ensure_bin() {
    local bin="$1" pkg="${2:-$1}"
    command -v "$bin" >/dev/null 2>&1 && return 0
    pkg_install "$pkg"
    command -v "$bin" >/dev/null 2>&1 || die "failed to install '$bin'"
}

ensure_core_deps() {
    pkg_update
    ensure_bin curl
    ensure_bin wget
    ensure_bin jq
    ensure_bin qrencode
    ensure_bin openssl
    ensure_bin tar
    if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
        pkg_install python3
    fi
    command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 \
        || die "python3 is required"
}
