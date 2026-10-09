# shellcheck shell=bash
# Firewall helpers (ufw / firewalld).
#
# xvei never enables, resets or tightens a firewall on its own - a wrong
# default-deny can cut you off from SSH. It only ever:
#   * fw_check  - when a firewall is ALREADY active and blocks ports the config
#                 needs, offers to add allow rules for them (never removes any);
#   * fw_setup  - `xvei firewall setup`, an explicit opt-in "deny incoming
#                 except SSH + xvei ports", shown in full and confirmed first.

# active backend: ufw | firewalld | none
fw_backend() {
    if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -q '^Status: active'; then
        echo ufw
    elif command -v firewall-cmd >/dev/null 2>&1 && firewall-cmd --state >/dev/null 2>&1; then
        echo firewalld
    else
        echo none
    fi
}

# ports the current config needs reachable from outside, one PORT/proto per line
fw_needed_ports() { py ports 2>/dev/null; }

# SSH port(s) to keep open: sshd's effective config, what sshd listens on, and
# the port of the current session (catches a moved or socket-activated sshd).
fw_ssh_ports() {
    {
        { sshd -T || /usr/sbin/sshd -T; } 2>/dev/null | awk '$1=="port"{print $2}'
        ss -ltnpH 2>/dev/null | awk '/"sshd"/{n=split($4,a,":"); print a[n]}'
        [ -n "${SSH_CONNECTION:-}" ] && echo "$SSH_CONNECTION" | awk '{print $4}'
    } | grep -E '^[0-9]+$' | sort -un
}

# _fw_is_open <backend> <PORT/proto>
_fw_is_open() {
    local port="${2%/*}"
    case "$1" in
        ufw)
            ufw status 2>/dev/null \
                | awk -v p="$port" -v pp="$2" '/ALLOW/ && ($1==p || $1==pp) {f=1} END {exit !f}'
            ;;
        firewalld)
            firewall-cmd --query-port="$2" >/dev/null 2>&1 && return 0
            case "$2" in
                22/tcp)  firewall-cmd --query-service=ssh   >/dev/null 2>&1 ;;
                80/tcp)  firewall-cmd --query-service=http  >/dev/null 2>&1 ;;
                443/tcp) firewall-cmd --query-service=https >/dev/null 2>&1 ;;
                *)       return 1 ;;
            esac
            ;;
        *) return 0 ;;
    esac
}

# _fw_allow <backend> <PORT/proto>...   (additive only)
_fw_allow() {
    local be="$1" p; shift
    case "$be" in
        ufw)
            for p in "$@"; do ufw allow "$p" >/dev/null; done
            ;;
        firewalld)
            for p in "$@"; do firewall-cmd --permanent --add-port="$p" >/dev/null; done
            firewall-cmd --reload >/dev/null
            ;;
    esac
}

_fw_missing() {  # <backend> -> needed ports that are closed, one per line
    local p
    while read -r p; do
        [ -n "$p" ] && ! _fw_is_open "$1" "$p" && echo "$p"
    done < <(fw_needed_ports)
}

# Called by apply_all before provisioning (certbot needs :80 reachable).
fw_check() {
    local be; be="$(fw_backend)"
    [ "$be" = none ] && return 0
    local missing; mapfile -t missing < <(_fw_missing "$be")
    [ "${#missing[@]}" -eq 0 ] && return 0
    warn "$be is active and blocks ports this config needs: ${missing[*]}"
    if have_tty && confirm "Open them in $be now? (only adds allow rules)" y; then
        _fw_allow "$be" "${missing[@]}" && ok "opened: ${missing[*]}"
    else
        warn "clients will not connect until they are open (xvei firewall open)"
    fi
}

fw_status() {
    local be p; be="$(fw_backend)"
    ui_header "Firewall"
    printf '  %s%-14s%s %s\n' "$_c_dim" "Firewall" "$_c_off" "$be"
    printf '  %s%-14s%s %s\n' "$_c_dim" "SSH port(s)" "$_c_off" "$(fw_ssh_ports | xargs)"
    ui_group "Ports xvei needs"
    while read -r p; do
        [ -n "$p" ] || continue
        if [ "$be" = none ]; then printf '    %s\n' "$p"
        elif _fw_is_open "$be" "$p"; then
            printf '    %-12s %sopen%s\n' "$p" "$_c_ok" "$_c_off"
        else
            printf '    %-12s %sCLOSED%s\n' "$p" "$_c_err" "$_c_off"
        fi
    done < <(fw_needed_ports)
}

fw_open() {
    require_root
    local be; be="$(fw_backend)"
    if [ "$be" = none ]; then
        log "no active firewall (ufw / firewalld) - nothing to open"
        return 0
    fi
    local missing; mapfile -t missing < <(_fw_missing "$be")
    if [ "${#missing[@]}" -eq 0 ]; then ok "all needed ports are already open"; return 0; fi
    _fw_allow "$be" "${missing[@]}" && ok "opened in $be: ${missing[*]}"
}

_fw_setup_ufw() {  # <reset 0|1> <PORT/proto>...
    local reset="$1" p; shift
    ensure_bin ufw
    [ "$reset" = 1 ] && ufw --force reset >/dev/null
    # allow rules first, so SSH is never denied even for a moment
    for p in "$@"; do ufw allow "$p" >/dev/null; done
    ufw default deny incoming >/dev/null
    ufw default allow outgoing >/dev/null
    ufw --force enable
    ufw status verbose
}

_fw_setup_firewalld() {  # <PORT/proto>...
    ensure_bin firewall-cmd firewalld
    local p
    if firewall-cmd --state >/dev/null 2>&1; then
        for p in "$@"; do firewall-cmd --permanent --add-port="$p" >/dev/null; done
        firewall-cmd --reload >/dev/null
    else
        # write the rules offline so SSH is allowed the moment firewalld starts
        for p in "$@"; do firewall-offline-cmd --add-port="$p" >/dev/null; done
        systemctl enable --now firewalld
    fi
    firewall-cmd --list-all
}

# Opt-in lockdown: deny incoming except SSH + xvei ports (+ user extras).
fw_setup() {
    require_root
    local be; be="$(fw_backend)"
    if [ "$be" = none ]; then
        if command -v firewall-cmd >/dev/null 2>&1; then be=firewalld
        elif command -v ufw >/dev/null 2>&1; then be=ufw
        elif os_is_rhel_family; then be=firewalld
        else be=ufw; fi
    fi

    local ssh svc allow=() p
    mapfile -t ssh < <(fw_ssh_ports)
    [ "${#ssh[@]}" -gt 0 ] || ssh=(22)
    mapfile -t svc < <(fw_needed_ports)
    for p in "${ssh[@]}"; do allow+=("$p/tcp"); done

    echo
    log "firewall setup via $be: deny all incoming traffic except:"
    echo "  SSH (detected) : ${allow[*]}"
    echo "  xvei services  : ${svc[*]:-(none)}"
    warn "If you reach SSH on any other port, add it below - otherwise you WILL lose access."
    local extra; extra="$(read_value "Extra ports to allow, space separated (e.g. 2222/tcp 27015/udp)")"
    for p in $extra; do
        if [[ "$p" =~ ^[0-9]+/(tcp|udp)$ ]]; then allow+=("$p")
        elif [[ "$p" =~ ^[0-9]+$ ]]; then allow+=("$p/tcp" "$p/udp")
        else warn "skipping invalid port '$p' (use PORT or PORT/tcp|udp)"; fi
    done
    allow+=("${svc[@]}")
    mapfile -t allow < <(printf '%s\n' "${allow[@]}" | awk 'NF && !seen[$0]++')

    echo
    log "will allow: ${allow[*]}"
    local reset=0
    if [ "$be" = ufw ]; then
        warn "existing ufw rules are kept unless you choose to wipe them"
        confirm "Wipe existing ufw rules first (ufw reset)?" n && reset=1
    fi
    confirm "Apply this firewall configuration?" n || { log "cancelled"; return 0; }

    case "$be" in
        ufw)       _fw_setup_ufw "$reset" "${allow[@]}" ;;
        firewalld) _fw_setup_firewalld "${allow[@]}" ;;
    esac
}

menu_firewall() {
    fw_status
    echo
    ui_opt 1 "Open ports" "add allow rules for the ports xvei needs"
    ui_opt 2 "Full setup" "deny incoming, allow SSH + xvei ports (opt-in)"
    ui_back
    case "$(read_value "Choose" 0)" in
        1) fw_open ;;
        2) fw_setup ;;
    esac
}
