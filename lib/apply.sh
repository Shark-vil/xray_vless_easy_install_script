# shellcheck shell=bash
# Regenerate every runtime config from state.json, validate, swap in, restart.
# This is what makes edits work without a full reinstall.

apply_all() {
    require_root
    state_exists || die "not installed yet (no $XVEI_STATE); run: xvei install"

    # config.json edited by hand since xvei last wrote it (or adopted it)?
    # Those edits would be lost - ask first.
    local want; want="$(state_get applied_sha256)"
    if [ -n "$want" ] && [ -f "$XRAY_CONFIG" ] \
        && [ "$(sha256sum "$XRAY_CONFIG" | awk '{print $1}')" != "$want" ]; then
        warn "$XRAY_CONFIG was changed outside xvei since xvei last wrote it;"
        warn "applying replaces it (the current file is kept as $XRAY_CONFIG.bak)"
        if ! { have_tty && confirm "Overwrite it?" n; }; then
            err "not applied (the xvei state is saved; run 'xvei apply' to apply it)"
            return 1
        fi
    fi

    local needs; needs="$(py needs)"
    log "state requires: ${needs:-nothing extra}"

    # 0. an active firewall would silently break certbot (:80) and clients;
    #    offer to open what is missing (additive only, never enables one)
    fw_check

    # 1. provision external resources to match desired state.
    #    cert_issue may stop nginx/xray for a standalone challenge; nginx_setup
    #    then rewrites the fallback vhost and brings nginx back up.
    if [[ " $needs " == *" cert "* ]]; then
        cert_issue
        nginx_setup
    fi

    if [[ " $needs " == *" warp "* ]]; then warp_up; else warp_down; fi
    if [[ " $needs " == *" tor "*  ]]; then tor_up;  else tor_down;  fi

    # 2. render new configs to staging files. Xray infers the config format from
    #    the file extension, so the staging file MUST end in .json.
    local xnew="$XRAY_DIR/.xvei-config.new.json" hnew="$XRAY_DIR/.xvei-hy2.new.yaml"
    rm -f "$xnew" "$hnew"
    mkdir -p "$XRAY_DIR"
    py build --xray-out "$xnew" --hy2-out "$hnew" || die "config generation failed"

    # 3. validate xray config before touching the live one
    xray_installed || die "xray is not installed"
    if ! xray_test "$xnew"; then
        err "generated xray config failed validation; live config untouched"
        err "state was saved but not applied. Revert with:"
        err "  cp $XVEI_STATE.bak $XVEI_STATE && xvei edit"
        rm -f "$xnew" "$hnew"
        return 1
    fi

    # 4. swap in + restart. An adopted config is saved once, as it was before
    #    xvei ever wrote it (comments included - the rebuilt one has none).
    if is_adopted && [ -f "$XRAY_CONFIG" ] && [ ! -e "$XRAY_CONFIG.xvei-orig" ]; then
        cp -p "$XRAY_CONFIG" "$XRAY_CONFIG.xvei-orig"
        log "original config saved as $XRAY_CONFIG.xvei-orig"
    fi
    [ -f "$XRAY_CONFIG" ] && cp -f "$XRAY_CONFIG" "$XRAY_CONFIG.bak"
    mv "$xnew" "$XRAY_CONFIG"
    chmod 600 "$XRAY_CONFIG"
    xray_restart
    if ! check_service xray; then
        warn "xray did not come up; rolling back to previous config"
        [ -f "$XRAY_CONFIG.bak" ] && cp -f "$XRAY_CONFIG.bak" "$XRAY_CONFIG"
        xray_restart
        return 1
    fi
    py set-meta --applied-sha "$(sha256sum "$XRAY_CONFIG" | awk '{print $1}')" >/dev/null || true

    # 5. hysteria2 follows the same state
    if [ -s "$hnew" ]; then hy2_apply "$hnew"; else hy2_apply ""; fi
    rm -f "$hnew"

    # 6. nginx only matters when a fallback inbound exists
    case " $needs " in
        *" cert "*) systemctl reload nginx 2>/dev/null || true ;;
        *) nginx_teardown ;;
    esac

    # 7. refresh client links/configs
    mkdir -p "$CLIENT_DIR"
    py set-meta --server-ip "$(server_ip)" >/dev/null || true
    py links >/dev/null || warn "client link generation reported an issue"

    ok "applied. Xray config: $XRAY_CONFIG"
}
