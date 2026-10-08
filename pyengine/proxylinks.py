"""Parse share links into Xray outbound objects (for custom outbounds).

Supported:
  vless://   tcp / ws / grpc / xhttp / httpupgrade over none / tls / reality
  vmess://   v2rayN base64 JSON or the URL form, same transports
  trojan://  same transports, tls by default
  ss://      SIP002 (base64 or plain userinfo) and the legacy all-base64 form
  socks:// socks5://  plain user:pass or v2rayN's base64 userinfo
  http:// https://
The #fragment is only a display name.
"""
from __future__ import annotations

import base64
import binascii
import json
from urllib.parse import parse_qs, unquote, urlsplit

import util

SUPPORTED = "vless, vmess, trojan, ss, socks5, http"

_NETWORKS = {
    "tcp": "tcp", "raw": "tcp",
    "ws": "ws",
    "grpc": "grpc",
    "xhttp": "xhttp", "splithttp": "xhttp",
    "httpupgrade": "httpupgrade",
}

# Shadowsocks ciphers Xray still implements (stream ciphers were removed)
_SS_METHODS = {
    "aes-128-gcm", "aes-256-gcm",
    "chacha20-poly1305", "chacha20-ietf-poly1305",
    "xchacha20-poly1305", "xchacha20-ietf-poly1305",
    "2022-blake3-aes-128-gcm", "2022-blake3-aes-256-gcm",
    "2022-blake3-chacha20-poly1305",
    "none", "plain",
}


def parse(link: str) -> tuple[dict, str]:
    """Return (outbound object without "tag", display name)."""
    link = (link or "").strip()
    if "://" not in link:
        util.die(f"not a share link (supported: {SUPPORTED})")
    scheme = link.split("://", 1)[0].lower()
    if scheme == "vless":
        return _vless(link)
    if scheme == "vmess":
        return _vmess(link)
    if scheme == "trojan":
        return _trojan(link)
    if scheme == "ss":
        return _ss(link)
    if scheme in ("socks", "socks5", "socks5h"):
        return _socks(link)
    if scheme in ("http", "https"):
        return _http(link, tls=scheme == "https")
    if scheme in ("hysteria2", "hy2"):
        util.die(f"hysteria2 links are not supported as outbounds (supported: {SUPPORTED})")
    util.die(f"unsupported link type {scheme}:// (supported: {SUPPORTED})")


def describe(ob: dict) -> str:
    """Short human summary, e.g. 'vless example.com:443 ws/tls'."""
    proto = ob.get("protocol", "?")
    settings = ob.get("settings", {})
    srv = (settings.get("vnext") or settings.get("servers") or [{}])[0]
    out = f"{proto} {srv.get('address', '?')}:{srv.get('port', '?')}"
    stream = ob.get("streamSettings")
    if stream:
        out += f" {stream.get('network', 'tcp')}/{stream.get('security', 'none')}"
    return out


# ---- helpers ---------------------------------------------------------------

def _b64decode(s: str) -> str | None:
    """Decode standard or url-safe base64 with optional padding, or None."""
    s = s.strip()
    padded = s + "=" * (-len(s) % 4)
    for dec in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return dec(padded).decode()
        except (binascii.Error, ValueError, UnicodeDecodeError):
            continue
    return None


def _endpoint(u) -> tuple[str, int]:
    try:
        port = u.port
    except ValueError:
        port = None
    if not u.hostname or not port:
        util.die("link has no valid host:port")
    return u.hostname, port


def _query(u) -> dict:
    return {k: v[-1] for k, v in parse_qs(u.query, keep_blank_values=True).items()}


def _name(u) -> str:
    return unquote(u.fragment or "")


def _stream(q: dict, host: str, default_security: str = "none") -> dict:
    """streamSettings from link parameters (shared by vless / vmess / trojan)."""
    net_raw = (q.get("type") or "tcp").lower()
    net = _NETWORKS.get(net_raw)
    if not net:
        util.die(f"transport {net_raw!r} is not supported "
                 f"(supported: {', '.join(sorted(set(_NETWORKS)))})")
    sec = (q.get("security") or default_security).lower()
    stream: dict = {"network": net, "security": sec}

    sni = q.get("sni") or q.get("peer") or ""
    fp = q.get("fp") or ""
    if sec == "tls":
        tls: dict = {"serverName": sni or q.get("host") or host}
        if fp:
            tls["fingerprint"] = fp
        if q.get("alpn"):
            tls["alpn"] = [a for a in q["alpn"].split(",") if a]
        if (q.get("allowInsecure") or q.get("insecure") or "").lower() in ("1", "true"):
            # Xray 26 removed allowInsecure (replaced by pinnedPeerCertSha256,
            # which a share link does not carry); the config would not load.
            util.die("links with allowInsecure=1 are not supported: current Xray "
                     "dropped that option. The server needs a valid certificate.")
        stream["tlsSettings"] = tls
    elif sec == "reality":
        if not q.get("pbk"):
            util.die("reality link has no public key (pbk)")
        reality: dict = {"serverName": sni, "fingerprint": fp or "chrome",
                         "publicKey": q["pbk"], "shortId": q.get("sid", "")}
        if q.get("spx"):
            reality["spiderX"] = q["spx"]
        stream["realitySettings"] = reality
    elif sec != "none":
        util.die(f"security {sec!r} is not supported (none, tls, reality)")

    host_hdr, path = q.get("host", ""), q.get("path", "")
    if net in ("ws", "httpupgrade"):
        s: dict = {"path": path or "/"}
        if host_hdr:
            s["host"] = host_hdr
        stream[f"{net}Settings"] = s
    elif net == "xhttp":
        s = {"path": path or "/", "mode": q.get("mode") or "auto"}
        if host_hdr:
            s["host"] = host_hdr
        stream["xhttpSettings"] = s
    elif net == "grpc":
        s = {"serviceName": q.get("serviceName") or path}
        if q.get("mode") == "multi":
            s["multiMode"] = True
        stream["grpcSettings"] = s
    elif q.get("headerType") not in (None, "", "none"):
        util.die(f"tcp headerType {q['headerType']!r} is not supported")
    return stream


# ---- protocols -------------------------------------------------------------

def _vless(link: str) -> tuple[dict, str]:
    u = urlsplit(link)
    host, port = _endpoint(u)
    uid = unquote(u.username or "")
    if not uid:
        util.die("vless link has no user id")
    q = _query(u)
    user: dict = {"id": uid, "encryption": q.get("encryption") or "none"}
    if q.get("flow"):
        user["flow"] = q["flow"]
    ob = {"protocol": "vless",
          "settings": {"vnext": [{"address": host, "port": port, "users": [user]}]},
          "streamSettings": _stream(q, host)}
    return ob, _name(u)


def _vmess_out(host: str, port: int, uid: str, aid: str, scy: str, q: dict) -> dict:
    if not uid:
        util.die("vmess link has no user id")
    if str(aid or "0") not in ("", "0"):
        util.die("legacy VMess (alterId > 0) is not supported by Xray; "
                 "the server must use alterId 0 (VMess AEAD)")
    user = {"id": uid, "security": scy or "auto"}
    return {"protocol": "vmess",
            "settings": {"vnext": [{"address": host, "port": port, "users": [user]}]},
            "streamSettings": _stream(q, host)}


def _vmess(link: str) -> tuple[dict, str]:
    body = link.split("://", 1)[1]
    raw = _b64decode(body.split("#", 1)[0])
    if raw and raw.lstrip().startswith("{"):
        # v2rayN: vmess://base64({"add","port","id","aid","scy","net","tls",...})
        try:
            j = json.loads(raw)
        except ValueError:
            util.die("vmess link: invalid JSON inside base64")
        host = str(j.get("add") or "")
        try:
            port = int(j.get("port") or 0)
        except (TypeError, ValueError):
            port = 0
        if not host or not port:
            util.die("link has no valid host:port")
        net = str(j.get("net") or "tcp")
        q = {
            "type": net,
            "security": "tls" if j.get("tls") == "tls" else str(j.get("tls") or "none"),
            "sni": str(j.get("sni") or ""),
            "fp": str(j.get("fp") or ""),
            "alpn": str(j.get("alpn") or ""),
            "host": str(j.get("host") or ""),
            "path": str(j.get("path") or ""),
            "headerType": str(j.get("type") or "none") if net in ("tcp", "raw") else "",
            "mode": str(j.get("type") or "") if net == "grpc" else "",
            "allowInsecure": str(j.get("allowInsecure") or j.get("skip-cert-verify") or ""),
        }
        if net == "xhttp" and j.get("type") not in (None, "", "none"):
            q["mode"] = str(j["type"])
        ob = _vmess_out(host, port, str(j.get("id") or ""), str(j.get("aid") or "0"),
                        str(j.get("scy") or ""), q)
        return ob, str(j.get("ps") or "")
    # URL form: vmess://uuid@host:port?type=ws&security=tls...#name
    u = urlsplit(link)
    host, port = _endpoint(u)
    q = _query(u)
    ob = _vmess_out(host, port, unquote(u.username or ""), q.get("aid", "0"),
                    q.get("encryption") or q.get("scy") or "", q)
    return ob, _name(u)


def _trojan(link: str) -> tuple[dict, str]:
    u = urlsplit(link)
    host, port = _endpoint(u)
    password = unquote(u.username or "")
    if u.password is not None:  # a ':' inside an unencoded password
        password += ":" + unquote(u.password)
    if not password:
        util.die("trojan link has no password")
    ob = {"protocol": "trojan",
          "settings": {"servers": [{"address": host, "port": port, "password": password}]},
          "streamSettings": _stream(_query(u), host, default_security="tls")}
    return ob, _name(u)


def _ss(link: str) -> tuple[dict, str]:
    body = link.split("://", 1)[1]
    body, _, frag = body.partition("#")
    name = unquote(frag)
    body, _, query = body.partition("?")
    if "plugin=" in query:
        util.die("shadowsocks plugins (obfs, v2ray-plugin, ...) are not supported")
    body = body.rstrip("/")
    if "@" not in body:
        # legacy: ss://base64(method:password@host:port)
        dec = _b64decode(body)
        if not dec or "@" not in dec:
            util.die("shadowsocks link: cannot decode")
        userinfo, hostport = dec.rsplit("@", 1)
    else:
        # SIP002: ss://base64url(method:password)@host:port or plain method:password
        userinfo, hostport = body.rsplit("@", 1)
        userinfo = unquote(userinfo)
        if ":" not in userinfo:
            userinfo = _b64decode(userinfo) or ""
    if ":" not in userinfo:
        util.die("shadowsocks link: no method:password")
    method, password = userinfo.split(":", 1)
    method = method.lower()
    if method not in _SS_METHODS:
        util.die(f"shadowsocks method {method!r} is not supported by Xray "
                 f"(supported: {', '.join(sorted(_SS_METHODS))})")
    host, port = _endpoint(urlsplit("//" + hostport))
    ob = {"protocol": "shadowsocks",
          "settings": {"servers": [{"address": host, "port": port,
                                    "method": method, "password": password}]}}
    return ob, name


def _userinfo(u) -> tuple[str, str]:
    user = unquote(u.username or "")
    pw = unquote(u.password or "")
    if user and u.password is None:
        # v2rayN style: socks://base64(user:pass)@host:port
        text = _b64decode(user)
        if text and ":" in text:
            return tuple(text.split(":", 1))  # type: ignore[return-value]
    return user, pw


def _server(u) -> dict:
    host, port = _endpoint(u)
    srv: dict = {"address": host, "port": port}
    user, pw = _userinfo(u)
    if user:
        srv["users"] = [{"user": user, "pass": pw}]
    return srv


def _socks(link: str) -> tuple[dict, str]:
    u = urlsplit(link)
    return {"protocol": "socks", "settings": {"servers": [_server(u)]}}, _name(u)


def _http(link: str, *, tls: bool) -> tuple[dict, str]:
    u = urlsplit(link)
    ob: dict = {"protocol": "http", "settings": {"servers": [_server(u)]}}
    if tls:
        ob["streamSettings"] = {"security": "tls",
                                "tlsSettings": {"serverName": u.hostname}}
    return ob, _name(u)
