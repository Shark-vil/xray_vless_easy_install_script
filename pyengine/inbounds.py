"""Turn state['inbounds'] entries into Xray inbound objects."""
from __future__ import annotations

import state as st
import util

WS_SOCKET = "@vless-ws"
XHTTP_SOCKET = "@vless-xhttp"
SNIFF = {"enabled": True, "destOverride": ["http", "tls", "quic"], "routeOnly": False}


def _clients(ib: dict, *, flow: str | None = None) -> list[dict]:
    c: dict = {"id": ib["uuid"]}
    if ib.get("email"):
        c["email"] = ib["email"]
    if flow:
        c["flow"] = flow
    return [c]


def _vless_tls(ib: dict, data: dict) -> dict:
    cert = data["cert"]
    fallbacks: list[dict] = []
    xhttp = st.get_type(data, "vless-xhttp-tls")
    if xhttp and xhttp.get("standalone") is not True:
        fallbacks.append({"path": "/" + xhttp["xhttp_path"], "dest": XHTTP_SOCKET, "xver": 0})
    ws = st.get_type(data, "vless-ws")
    if ws:
        fallbacks.append({"path": "/" + ws["ws_path"], "dest": WS_SOCKET, "xver": 0})
    fallbacks.append({"dest": "8080", "xver": 0})
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
    "shadowsocks": _shadowsocks,
    "hysteria2": _hysteria2_socks,
}


def build(data: dict) -> list[dict]:
    out: list[dict] = []
    # deterministic, and vless-tls first so it owns :443
    order = {t: i for i, t in enumerate(st.INBOUND_TYPES)}
    for ib in sorted(data["inbounds"], key=lambda x: order.get(x["type"], 99)):
        builder = _BUILDERS.get(ib["type"])
        if builder is None:
            util.warn(f"unknown inbound type {ib['type']!r}, skipped")
            continue
        out.append(builder(ib, data))
    return out


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
        "shadowsocks": "ss",
        "hysteria2": "hy2",
    }[itype]
