# shellcheck shell=bash
# OS detection, package-manager abstraction and dependency installation.
#
# Supported (tested) targets: Ubuntu 20.04+, Debian 11+, CentOS Stream 9.
# Anything else runs on a best-effort basis after a warning.

OS_ID=""; OS_VER=""; OS_LIKE=""; OS_NAME=""
detect_os() {
    [ -n "$OS_ID" ] && return 0
    eval "$(
        # shellcheck disable=SC1091
        . /etc/os-release 2>/dev/null
        printf 'OS_ID=%q OS_VER=%q OS_LIKE=%q OS_NAME=%q\n' \
            "${ID:-unknown}" "${VERSION_ID:-}" "${ID_LIKE:-}" "${PRETTY_NAME:-${ID:-unknown}}"
    )"
}

# CentOS / RHEL / Alma / Rocky / Oracle - but not Fedora
os_is_rhel_family() {
    detect_os
    [ "$OS_ID" = fedora ] && return 1
    case " $OS_ID $OS_LIKE " in
        *" rhel "*|*" centos "*) return 0 ;;
    esac
    return 1
}

os_supported() {
    detect_os
    local major="${OS_VER%%.*}"
    [[ "$major" =~ ^[0-9]+$ ]] || return 1
    case "$OS_ID" in
        ubuntu) [ "$major" -ge 20 ] ;;
        debian) [ "$major" -ge 11 ] ;;
        centos) [ "$major" -eq 9 ] ;;
        *)      return 1 ;;
    esac
}

os_check_supported() {
    if os_supported; then
        log "OS: $OS_NAME (supported)"
        return 0
    fi
    warn "OS: $OS_NAME is not on the supported list (Ubuntu 20.04+, Debian 11+, CentOS Stream 9)."
    warn "xvei may partly work here, but nothing is guaranteed."
    confirm "Continue anyway?" n || exit 1
}

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

# Packages xvei installed itself (not ones that were already there), so that
# `xvei remove` can offer to remove them again.
XVEI_PKG_LIST="/var/lib/xvei/packages"
record_pkg() {
    mkdir -p "${XVEI_PKG_LIST%/*}"
    grep -qxF "$1" "$XVEI_PKG_LIST" 2>/dev/null || echo "$1" >> "$XVEI_PKG_LIST"
}

# ensure_bin <binary> [package]
ensure_bin() {
    local bin="$1" pkg="${2:-$1}"
    command -v "$bin" >/dev/null 2>&1 && return 0
    pkg_install "$pkg"
    command -v "$bin" >/dev/null 2>&1 || die "failed to install '$bin'"
    record_pkg "$pkg"
}

pkg_remove() {
    detect_pkg
    log "removing $*"
    case "$_PKG" in
        apt-get) DEBIAN_FRONTEND=noninteractive apt-get purge -y -qq "$@" ;;
        dnf|yum) "$_PKG" remove -y "$@" ;;
        zypper)  zypper --non-interactive remove "$@" ;;
        pacman)  pacman -Rns --noconfirm "$@" ;;
    esac
}

# certbot, tor and qrencode are not in the base RHEL-family repos, only in EPEL.
ensure_epel() {
    os_is_rhel_family || return 0
    detect_pkg
    rpm -q epel-release >/dev/null 2>&1 && return 0
    log "enabling EPEL (certbot / tor / qrencode live there on RHEL-family systems)"
    # some EPEL packages depend on CRB; harmless if it is already on or absent
    "$_PKG" config-manager --set-enabled crb >/dev/null 2>&1 || true
    "$_PKG" install -y epel-release >/dev/null 2>&1 \
        || "$_PKG" install -y "https://dl.fedoraproject.org/pub/epel/epel-release-latest-$(rpm -E %rhel).noarch.rpm" \
        || warn "could not enable EPEL; certbot / tor may fail to install"
}

ensure_python() {
    find_python >/dev/null && return 0
    pkg_install python3 || true
    find_python >/dev/null && return 0
    # EL8 / openSUSE Leap ship 3.6 as "python3"; newer builds are separate packages
    case "$_PKG" in
        dnf|yum) pkg_install python39 || pkg_install python3.11 || true ;;
        zypper)  pkg_install python311 || true ;;
    esac
    find_python >/dev/null || die "Python >= 3.7 is required and could not be installed"
}

ensure_core_deps() {
    detect_os
    ensure_epel
    pkg_update
    ensure_bin curl
    ensure_bin qrencode
    ensure_bin openssl
    ensure_bin tar
    ensure_python
}
