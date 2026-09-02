# shellcheck shell=bash
# Cloudflare WARP as a local SOCKS5 (127.0.0.1:1080) via a docker container.

WARP_CONTAINER="warp-xray"
WARP_DATA="/var/lib/xvei/warp"

_docker_install() {
    command -v docker >/dev/null 2>&1 && return 0
    log "installing docker"
    curl -fsSL https://get.docker.com | sh || die "docker install failed"
    systemctl enable --now docker
}

warp_up() {
    _docker_install
    if docker ps -a --format '{{.Names}}' | grep -qx "$WARP_CONTAINER"; then
        docker start "$WARP_CONTAINER" >/dev/null 2>&1 || true
        return 0
    fi
    mkdir -p "$WARP_DATA"
    log "starting WARP container (SOCKS5 127.0.0.1:1080)"
    docker run -d \
        --name "$WARP_CONTAINER" \
        --restart always \
        -p 127.0.0.1:1080:1080 \
        -e WARP_SLEEP=2 \
        --cap-add NET_ADMIN \
        --sysctl net.ipv6.conf.all.disable_ipv6=0 \
        --sysctl net.ipv4.conf.all.src_valid_mark=1 \
        -v "$WARP_DATA:/var/lib/cloudflare-warp" \
        caomingjun/warp
}

warp_down() {
    command -v docker >/dev/null 2>&1 || return 0
    docker rm -f "$WARP_CONTAINER" >/dev/null 2>&1 || true
    rm -rf "$WARP_DATA"
    ok "WARP container removed"
}
