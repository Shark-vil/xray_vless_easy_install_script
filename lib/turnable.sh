# shellcheck shell=bash
# Turnable (github.com/TheAirBlow/Turnable): carries client traffic through the
# TURN relays of VK calls to this server, which forwards it into a local plain
# VLESS inbound of Xray. Unstable (VK can break it at any time) and not
# anonymous (VK sees this server's IP). Config rendered by pyengine/turnconf.py.
#
# The release is pinned to a version whose source was reviewed and is checked
# against these sha256 sums (as published for the GitHub release assets).

TURNABLE_VERSION="0.6.4"
TURNABLE_BIN="/usr/local/bin/turnable"
TURNABLE_DIR="/etc/turnable"
TURNABLE_CONFIG="$TURNABLE_DIR/config.json"
TURNABLE_SERVICE="turnable"
TURNABLE_UNIT="/etc/systemd/system/$TURNABLE_SERVICE.service"

_turnable_sha256() {
    case "$1" in
        amd64) echo 62dc1185a8f30eba1600e4836999f25b474fbfc3ec475591d2f1cceb9da47f11 ;;
        arm64) echo 555f1faa61051f09910c87118597ae9296bbf524ce5b7e18048efc94e14c88ba ;;
    esac
}

turnable_install() {
    if [ -x "$TURNABLE_BIN" ] && [ "$(cat "$TURNABLE_DIR/.version" 2>/dev/null)" = "$TURNABLE_VERSION" ]; then
        return 0
    fi
    local arch tmp
    case "$(uname -m)" in
        x86_64)        arch=amd64 ;;
        aarch64|arm64) arch=arm64 ;;
        *) die "Turnable: unsupported architecture $(uname -m) (amd64 / arm64 only)" ;;
    esac
    log "installing Turnable $TURNABLE_VERSION ($arch)"
    tmp="$(mktemp)"
    if ! curl -fsSL -o "$tmp" \
        "https://github.com/TheAirBlow/Turnable/releases/download/$TURNABLE_VERSION/turnable-linux-$arch"; then
        rm -f "$tmp"
        die "Turnable download failed"
    fi
    if [ "$(sha256sum "$tmp" | awk '{print $1}')" != "$(_turnable_sha256 "$arch")" ]; then
        rm -f "$tmp"
        die "Turnable binary checksum mismatch; not installed"
    fi
    install -m 755 "$tmp" "$TURNABLE_BIN"
    rm -f "$tmp"
    mkdir -p "$TURNABLE_DIR"
    echo "$TURNABLE_VERSION" > "$TURNABLE_DIR/.version"
}

# ML-KEM key pair for the server, generated once and kept in the state
turnable_ensure_keys() {
    [ -n "$(py turnable-info pub_key 2>/dev/null)" ] && return 0
    local out priv pub
    out="$("$TURNABLE_BIN" config keygen)" || die "turnable keygen failed"
    priv="$(sed -n 's/^priv_key=//p' <<<"$out")"
    pub="$(sed -n 's/^pub_key=//p' <<<"$out")"
    [ -n "$priv" ] && [ -n "$pub" ] || die "turnable keygen: unexpected output"
    py turnable-keys --priv "$priv" --pub "$pub" || die "could not store Turnable keys"
}

# turnable_apply <rendered-config-file|"">  -- called by apply.sh
turnable_apply() {
    local newcfg="$1"
    if [ -z "$newcfg" ] || [ ! -s "$newcfg" ]; then
        turnable_down
        return 0
    fi
    local grp; grp="$(id -gn nobody 2>/dev/null || echo nogroup)"
    mkdir -p "$TURNABLE_DIR"
    install -m 640 -g "$grp" "$newcfg" "$TURNABLE_CONFIG"
    cat > "$TURNABLE_UNIT" <<EOF
[Unit]
Description=Turnable tunnel server (managed by xvei)
After=network-online.target
Wants=network-online.target

[Service]
User=nobody
Group=$grp
StateDirectory=turnable
WorkingDirectory=/var/lib/turnable
ExecStart=$TURNABLE_BIN server -c $TURNABLE_CONFIG
Restart=on-failure
RestartSec=5
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    mark_managed turnable
    systemctl enable "$TURNABLE_SERVICE" >/dev/null 2>&1 || true
    systemctl restart "$TURNABLE_SERVICE"
    if ! check_service "$TURNABLE_SERVICE"; then
        warn "Turnable failed to start; check: journalctl -u $TURNABLE_SERVICE -n40"
    fi
    turnable_check_link
}

# the turnable:// link is generated on the fly (pyengine/links.py); make sure
# Turnable can produce it
turnable_check_link() {
    local tag; tag="$(py turnable-info tag)" || return 0
    py link "$tag" >/dev/null 2>&1 || warn "could not generate the Turnable client link"
}

turnable_down() {
    [ -f "$TURNABLE_UNIT" ] || return 0
    xvei_owns turnable || return 0
    systemctl disable --now "$TURNABLE_SERVICE" 2>/dev/null || true
    rm -f "$TURNABLE_UNIT"
    systemctl daemon-reload
    rm -rf "$TURNABLE_DIR" "$TURNABLE_BIN"
    unmark_managed turnable
    ok "Turnable removed"
}
