# shellcheck shell=bash
# Apply a change: provision what the config needs, validate the staged
# config.json, swap it in, restart. config.json itself is the source of truth;
# pyengine stages changed copies in $XRAY_PENDING and never edits it in place.

XRAY_PENDING="$XRAY_DIR/.xvei-config.new.json"

apply_all() {
    require_root
    state_exists || die "not installed yet (no $XVEI_STATE); run: xvei install"

    local needs; needs="$(py needs)"
    [ -n "$needs" ] && log "needs: $needs"

    # 0. an active firewall would silently break certbot (:80) and clients;
    #    offer to open what is missing (additive only, never enables one)
    fw_check

    # 1. provision external resources.
    #    cert_issue may stop nginx/xray for a standalone challenge; nginx_setup
    #    then rewrites the fallback vhost and brings nginx back up.
    if [[ " $needs " == *" cert "* ]]; then
        cert_issue
        # a self-signed fallback or another domain moves the certificate
        py sync-cert >/dev/null || true
        nginx_setup
    fi

    if [[ " $needs " == *" warp "* ]]; then warp_up; else warp_down; fi
    if [[ " $needs " == *" tor "*  ]]; then tor_up;  else tor_down;  fi
    if [[ " $needs " == *" turnable "* ]]; then
        turnable_install
        turnable_ensure_keys
    fi

    # 2. the staged config.json: validate before touching the live one
    if [ -f "$XRAY_PENDING" ]; then
        xray_installed || die "xray is not installed"
        if ! xray_test "$XRAY_PENDING"; then
            err "the changed config failed validation; $XRAY_CONFIG was not touched"
            rm -f "$XRAY_PENDING" "$XRAY_PENDING.bak"
            # the change also updated the xvei state; take that back too
            [ -f "$XVEI_STATE.bak" ] && cp -f "$XVEI_STATE.bak" "$XVEI_STATE"
            return 1
        fi
        # a config xvei did not create is saved once, as it was before xvei
        # first wrote it (comments included - the rewritten one has none)
        if is_adopted && [ -f "$XRAY_CONFIG" ] && [ ! -e "$XRAY_CONFIG.xvei-orig" ]; then
            cp -p "$XRAY_CONFIG" "$XRAY_CONFIG.xvei-orig"
            log "original config saved as $XRAY_CONFIG.xvei-orig"
        fi
        [ -f "$XRAY_CONFIG" ] && cp -f "$XRAY_CONFIG" "$XRAY_CONFIG.bak"
        mv "$XRAY_PENDING" "$XRAY_CONFIG"
        rm -f "$XRAY_PENDING.bak"
        chmod 600 "$XRAY_CONFIG"
        xray_restart
        if ! check_service xray; then
            warn "xray did not come up; rolling back to the previous config"
            [ -f "$XRAY_CONFIG.bak" ] && cp -f "$XRAY_CONFIG.bak" "$XRAY_CONFIG"
            xray_restart
            return 1
        fi
    fi

    # 3. Hysteria2 / Turnable run from their own configs
    local hnew="$XRAY_DIR/.xvei-hy2.new.yaml" tnew="$XRAY_DIR/.xvei-turnable.new.json"
    rm -f "$hnew" "$tnew"
    py build --hy2-out "$hnew" --turnable-out "$tnew" >/dev/null || die "config generation failed"
    if [ -s "$hnew" ]; then hy2_apply "$hnew"; else hy2_apply ""; fi
    if [ -s "$tnew" ]; then turnable_apply "$tnew"; else turnable_apply ""; fi
    rm -f "$hnew" "$tnew"

    # 4. nginx only matters while xvei has a TLS inbound
    case " $needs " in
        *" cert "*) systemctl reload nginx 2>/dev/null || true ;;
        *) nginx_teardown ;;
    esac

    # 5. server IP for the client links (REALITY / no domain)
    py set-meta --server-ip "$(server_ip)" >/dev/null 2>&1 || true

    ok "applied. Xray config: $XRAY_CONFIG"
}
