"""Build the Xray inbound objects xvei adds to config.json.

`ib` is the record editor.add_inbound puts together (tag, uuid, paths, keys...);
`data` is the xvei state (for the certificate). Once written, the object in
config.json is what counts - nothing here is consulted again.
"""
from __future__ import annotations

WS_SOCKET = "@vless-ws"
XHTTP_SOCKET = "@vless-xhttp"
TROJAN_TCP_SOCKET = "@trojan-tcp"
TROJAN_WS_SOCKET = "@trojan-ws"
VMESS_WS_SOCKET = "@vmess-ws"
SNIFF = {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": False}

# the local socket each fallback-carried type listens on by default
SOCKETS = {
    "vless-ws": WS_SOCKET,
    "vless-xhttp-tls": XHTTP_SOCKET,
    "trojan-tcp": TROJAN_TCP_SOCKET,
    "trojan-ws": TROJAN_WS_SOCKET,
    "vmess-ws": VMESS_WS_SOCKET,
}


def _clients(ib: dict, *, flow: str | None = None) -> list[dict]:
    c: dict = {"id": ib["uuid"]}
    if ib.get("email"):
        c["email"] = ib["email"]
    if flow:
        c["flow"] = flow
    return [c]


def _vless_tls(ib: dict, data: dict) -> dict:
    cert = data["cert"]
    # The inbounds added later behind this one get a "path" entry each in
    # front (editor.add_inbound). h2c goes to its own nginx listener; see
    # pyengine/sites.py for why. Anything else that is not VLESS goes to the
    # site - or to Trojan once it is added, which then falls back to the site
    # itself (so Trojan clients must negotiate http/1.1).
    fallbacks: list[dict] = [{"alpn": "h2", "dest": "8081", "xver": 0},
                             {"dest": "8080", "xver": 0}]
    return {
        "listen": "0.0.0.0",
        "port": ib.get("port", 443),
        "protocol": "vless",
        "tag": ib["tag"],
        "settings": {
            "clients": _clients(ib, flow="xtls-rprx-vision"),
            "decryption": "none",
            "fallbacks": fallbacks,
        },
        "streamSettings": {
            "network": "tcp",
            "security": "tls",
            "tlsSettings": {
                "alpn": ["h2", "http/1.1"],
                "minVersion": "1.2",
                "certificates": [
                    {"certificateFile": cert["fullchain"], "keyFile": cert["privkey"]}
                ],
            },
        },
        "sniffing": SNIFF,
    }


def _vless_ws(ib: dict, data: dict) -> dict:
    return {
        "listen": WS_SOCKET,
        "protocol": "vless",
        "tag": ib["tag"],
        "settings": {"clients": _clients(ib), "decryption": "none"},
        "streamSettings": {
            "network": "ws",
            "security": "none",
            "wsSettings": {"path": "/" + ib["ws_path"]},
        },
        "sniffing": SNIFF,
    }


def _vless_xhttp_reality(ib: dict, data: dict) -> dict:
    return {
        "listen": "0.0.0.0",
        "port": ib["port"],
        "protocol": "vless",
        "tag": ib["tag"],
        "settings": {"clients": _clients(ib), "decryption": "none"},
        "streamSettings": {
            "network": "xhttp",
            "security": "reality",
            "realitySettings": {
                "show": False,
                "dest": ib["dest"],
                "serverNames": ib["server_names"],
                "privateKey": ib["private_key"],
                "shortIds": ib["short_ids"],
            },
            "xhttpSettings": {"path": "/" + ib["xhttp_path"], "mode": "auto"},
        },
        "sniffing": SNIFF,
    }


def _vless_xhttp_tls(ib: dict, data: dict) -> dict:
    if ib.get("standalone"):
        cert = data["cert"]
        return {
            "listen": "0.0.0.0",
            "port": ib.get("port", 443),
            "protocol": "vless",
            "tag": ib["tag"],
            "settings": {"clients": _clients(ib), "decryption": "none"},
            "streamSettings": {
                "network": "xhttp",
                "security": "tls",
                "tlsSettings": {
                    "alpn": ["h2", "http/1.1"],
                    "minVersion": "1.2",
                    "certificates": [
                        {"certificateFile": cert["fullchain"], "keyFile": cert["privkey"]}
                    ],
                },
                "xhttpSettings": {"path": "/" + ib["xhttp_path"], "mode": "auto"},
            },
            "sniffing": SNIFF,
        }
    return {
        "listen": XHTTP_SOCKET,
        "protocol": "vless",
        "tag": ib["tag"],
        "settings": {"clients": _clients(ib), "decryption": "none"},
        "streamSettings": {
            "network": "xhttp",
            "security": "none",
            "xhttpSettings": {"path": "/" + ib["xhttp_path"], "mode": "auto"},
        },
        "sniffing": SNIFF,
    }


def _ws_stream(ib: dict) -> dict:
    return {"network": "ws", "security": "none", "wsSettings": {"path": "/" + ib["ws_path"]}}


def _trojan_clients(ib: dict) -> list[dict]:
    c: dict = {"password": ib["password"]}
    if ib.get("email"):
        c["email"] = ib["email"]
    return [c]


# Trojan / VMess sit on local sockets behind vless-tls: TLS is terminated there,
# so plaintext here never leaves the machine.
def _trojan_tcp(ib: dict, data: dict) -> dict:
    return {
        "listen": TROJAN_TCP_SOCKET,
        "protocol": "trojan",
        "tag": ib["tag"],
        "settings": {"clients": _trojan_clients(ib),
                     "fallbacks": [{"dest": "8080", "xver": 0}]},
        "streamSettings": {"network": "tcp", "security": "none"},
        "sniffing": SNIFF,
    }


def _trojan_ws(ib: dict, data: dict) -> dict:
    return {
        "listen": TROJAN_WS_SOCKET,
        "protocol": "trojan",
        "tag": ib["tag"],
        "settings": {"clients": _trojan_clients(ib)},
        "streamSettings": _ws_stream(ib),
        "sniffing": SNIFF,
    }


def _vmess_ws(ib: dict, data: dict) -> dict:
    return {
        "listen": VMESS_WS_SOCKET,
        "protocol": "vmess",
        "tag": ib["tag"],
        "settings": {"clients": _clients(ib)},
        "streamSettings": _ws_stream(ib),
        "sniffing": SNIFF,
    }


def _turnable_local(ib: dict, data: dict) -> dict:
    """Plain VLESS on loopback that the Turnable server forwards into. Turnable
    authenticates users and encrypts the tunnel; Xray does the routing."""
    return {
        "listen": "127.0.0.1",
        "port": ib["local_port"],
        "protocol": "vless",
        "tag": ib["tag"],
        "settings": {"clients": _clients(ib), "decryption": "none"},
        "streamSettings": {"network": "tcp", "security": "none"},
        "sniffing": SNIFF,
    }


def _shadowsocks(ib: dict, data: dict) -> dict:
    return {
        "listen": "0.0.0.0",
        "port": ib["port"],
        "protocol": "shadowsocks",
        "tag": ib["tag"],
        "settings": {
            "method": ib["method"],
            "password": ib["password"],
            "network": "tcp,udp",
        },
        "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
    }


def _hysteria2_socks(ib: dict, data: dict) -> dict:
    """The local SOCKS5 that the Hysteria2 service forwards all traffic into."""
    return {
        "listen": "127.0.0.1",
        "port": ib["socks_port"],
        "protocol": "socks",
        "tag": ib["tag"],
        "settings": {"auth": "noauth", "udp": True},
        "sniffing": SNIFF,
    }


_BUILDERS = {
    "vless-tls": _vless_tls,
    "vless-ws": _vless_ws,
    "vless-xhttp-reality": _vless_xhttp_reality,
    "vless-xhttp-tls": _vless_xhttp_tls,
    "trojan-tcp": _trojan_tcp,
    "trojan-ws": _trojan_ws,
    "vmess-ws": _vmess_ws,
    "shadowsocks": _shadowsocks,
    "hysteria2": _hysteria2_socks,
    "turnable": _turnable_local,
}


def build(ib: dict, data: dict) -> dict:
    """The Xray inbound object for a new inbound record."""
    return _BUILDERS[ib["type"]](ib, data)


# ---- defaults for new inbounds (used by editor) --------------------------

SS_METHODS = [
    "2022-blake3-aes-128-gcm",
    "2022-blake3-aes-256-gcm",
    "2022-blake3-chacha20-poly1305",
    "aes-128-gcm",
    "aes-256-gcm",
    "chacha20-ietf-poly1305",
]


def default_tag(itype: str) -> str:
    return {
        "vless-tls": "vless_tls",
        "vless-ws": "vless_ws",
        "vless-xhttp-reality": "vless_reality",
        "vless-xhttp-tls": "vless_xhttp",
        "trojan-tcp": "trojan",
        "trojan-ws": "trojan_ws",
        "vmess-ws": "vmess_ws",
        "shadowsocks": "ss",
        "hysteria2": "hy2",
        "turnable": "turnable",
    }[itype]
