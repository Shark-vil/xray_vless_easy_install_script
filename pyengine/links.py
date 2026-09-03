"""Generate client share links + full client configs from state."""
from __future__ import annotations

import base64
import json
import os
from urllib.parse import quote, urlencode

import routing
import state as st
import util

CLIENT_DIR_DEFAULT = os.path.expanduser("~/xray_eis")


def _endpoint_host(data: dict, ib: dict) -> str:
    # REALITY has no cert -> connect by IP; everything else by domain when present.
    if ib["type"] == "vless-xhttp-reality" or not data.get("domain"):
        return data.get("server_ip") or data.get("domain") or "SERVER_IP"
    return data["domain"]


def share_link(data: dict, ib: dict) -> str:
    label = quote(f"{ib['tag']}@{data.get('domain') or data.get('server_ip') or 'xvei'}")
    host = _endpoint_host(data, ib)
    domain = data.get("domain") or host
    t = ib["type"]

    if t == "vless-tls":
        q = {"encryption": "none", "security": "tls", "sni": domain, "fp": "chrome",
             "type": "tcp", "flow": "xtls-rprx-vision"}
        return f"vless://{ib['uuid']}@{host}:{ib.get('port', 443)}?{urlencode(q)}#{label}"

    if t == "vless-ws":
        q = {"encryption": "none", "security": "tls", "sni": domain, "fp": "chrome",
             "type": "ws", "host": domain, "path": "/" + ib["ws_path"]}
        return f"vless://{ib['uuid']}@{host}:443?{urlencode(q)}#{label}"

    if t == "vless-xhttp-reality":
        q = {"encryption": "none", "security": "reality", "sni": ib["server_names"][0],
             "fp": "chrome", "pbk": ib["public_key"], "sid": ib["short_ids"][0],
             "type": "xhttp", "path": "/" + ib["xhttp_path"], "mode": "auto"}
        return f"vless://{ib['uuid']}@{host}:{ib['port']}?{urlencode(q)}#{label}"

    if t == "vless-xhttp-tls":
        port = ib.get("port", 443) if ib.get("standalone") else 443
        q = {"encryption": "none", "security": "tls", "sni": domain, "fp": "chrome",
             "type": "xhttp", "host": domain, "path": "/" + ib["xhttp_path"], "mode": "auto"}
        return f"vless://{ib['uuid']}@{host}:{port}?{urlencode(q)}#{label}"

    if t == "shadowsocks":
        userinfo = base64.urlsafe_b64encode(
            f"{ib['method']}:{ib['password']}".encode()).decode().rstrip("=")
        return f"ss://{userinfo}@{host}:{ib['port']}#{label}"

    if t == "hysteria2":
        q = {"sni": domain}
        if data.get("cert", {}).get("mode") != "letsencrypt":
            q["insecure"] = "1"
        return f"hysteria2://{quote(ib['password'])}@{host}:{ib.get('port', 443)}/?{urlencode(q)}#{label}"

    return ""


# ---- full client config (Xray core format) ------------------------------

def _client_outbound(data: dict, ib: dict) -> dict:
    host = _endpoint_host(data, ib)
    domain = data.get("domain") or host
    t = ib["type"]
    if t == "shadowsocks":
        return {"protocol": "shadowsocks", "tag": "proxy",
                "settings": {"servers": [{"address": host, "port": ib["port"],
                                          "method": ib["method"], "password": ib["password"]}]}}
    # vless family
    user = {"id": ib["uuid"], "encryption": "none"}
    stream: dict = {}
    if t == "vless-tls":
        user["flow"] = "xtls-rprx-vision"
        stream = {"network": "tcp", "security": "tls",
                  "tlsSettings": {"serverName": domain, "fingerprint": "chrome"}}
    elif t == "vless-ws":
        stream = {"network": "ws", "security": "tls",
                  "tlsSettings": {"serverName": domain, "fingerprint": "chrome"},
                  "wsSettings": {"path": "/" + ib["ws_path"], "headers": {"Host": domain}}}
    elif t == "vless-xhttp-reality":
        stream = {"network": "xhttp", "security": "reality",
                  "realitySettings": {"serverName": ib["server_names"][0], "fingerprint": "chrome",
                                      "publicKey": ib["public_key"], "shortId": ib["short_ids"][0]},
                  "xhttpSettings": {"path": "/" + ib["xhttp_path"], "mode": "auto"}}
    elif t == "vless-xhttp-tls":
        stream = {"network": "xhttp", "security": "tls",
                  "tlsSettings": {"serverName": domain, "fingerprint": "chrome"},
                  "xhttpSettings": {"path": "/" + ib["xhttp_path"], "host": domain, "mode": "auto"}}
    port = ib["port"] if t == "vless-xhttp-reality" or ib.get("standalone") else 443
    return {"protocol": "vless", "tag": "proxy",
            "settings": {"vnext": [{"address": host, "port": port, "users": [user]}]},
            "streamSettings": stream}


def full_config(data: dict, ib: dict) -> dict:
    # Local split-tunneling on the CLIENT's own device: "direct" here means
    # "use my own ISP connection, skip the VPS" -- it never touches the
    # server, so it carries none of the server-side IP-exposure risk that
    # `routing.build()` guards against for the country templates.
    rules: list[dict] = [
        {"type": "field", "outboundTag": "direct", "ip": ["geoip:private"]},
    ]
    template = data["routing"].get("template") or "none"
    if template in routing.COUNTRY_MATCHERS:
        dom, ips = routing.COUNTRY_MATCHERS[template]
        if dom:
            rules.append({"type": "field", "outboundTag": "direct", "domain": dom})
        if ips:
            rules.append({"type": "field", "outboundTag": "direct", "ip": ips})
    elif template == "popular":
        rules.append({"type": "field", "outboundTag": "direct",
                      "domain": list(routing.POPULAR_DOMAINS)})
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {"tag": "socks", "port": 10808, "listen": "127.0.0.1", "protocol": "socks",
             "settings": {"udp": True}},
            {"tag": "http", "port": 10809, "listen": "127.0.0.1", "protocol": "http"},
        ],
        "outbounds": [
            _client_outbound(data, ib),
            {"protocol": "freedom", "tag": "direct"},
            {"protocol": "blackhole", "tag": "block"},
        ],
        "routing": {"domainStrategy": "IPIfNonMatch", "rules": rules},
    }


def write_all(data: dict, out_dir: str | None = None) -> list[str]:
    out_dir = out_dir or os.environ.get("XVEI_CLIENT_DIR", CLIENT_DIR_DEFAULT)
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []
    for ib in data["inbounds"]:
        link = share_link(data, ib)
        if link:
            p = os.path.join(out_dir, f"{ib['tag']}.link")
            util.atomic_write(p, link + "\n", 0o600)
            written.append(p)
        if ib["type"] != "hysteria2":
            p = os.path.join(out_dir, f"{ib['tag']}.json")
            util.atomic_write(p, json.dumps(full_config(data, ib), indent=2) + "\n", 0o600)
            written.append(p)
    return written


def print_links(data: dict, tag: str | None = None) -> None:
    for ib in data["inbounds"]:
        if tag and ib["tag"] != tag:
            continue
        link = share_link(data, ib)
        print(f"\n=== {ib['tag']} ({ib['type']}) ===")
        print(link)
