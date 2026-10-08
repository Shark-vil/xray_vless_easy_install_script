"""Parse share links into Xray outbound objects (for custom outbounds).

Supported: vless:// (tcp / ws / grpc / xhttp / httpupgrade over none / tls /
reality), socks:// socks5:// (plain user:pass or v2rayN's base64 userinfo),
http:// https://. The #fragment is only a display name.
"""
from __future__ import annotations

import base64
import binascii
from urllib.parse import parse_qs, unquote, urlsplit

import util

_NETWORKS = {
    "tcp": "tcp", "raw": "tcp",
    "ws": "ws",
    "grpc": "grpc",
    "xhttp": "xhttp", "splithttp": "xhttp",
    "httpupgrade": "httpupgrade",
}


def parse(link: str) -> tuple[dict, str]:
    """Return (outbound object without "tag", display name)."""
    link = (link or "").strip()
    if "://" not in link:
        util.die("not a share link (expected vless://, socks5:// or http://)")
    scheme = link.split("://", 1)[0].lower()
    if scheme == "vless":
        return _vless(link)
    if scheme in ("socks", "socks5", "socks5h"):
        return _socks(link)
    if scheme in ("http", "https"):
        return _http(link, tls=scheme == "https")
    if scheme in ("hysteria2", "hy2"):
        util.die("hysteria2 links are not supported as outbounds (use vless, socks5 or http)")
    util.die(f"unsupported link type {scheme}:// (supported: vless, socks5, http)")


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


def _endpoint(u) -> tuple[str, int]:
    try:
        port = u.port
    except ValueError:
        port = None
    if not u.hostname or not port:
        util.die("link has no valid host:port")
    return u.hostname, port


def _name(u) -> str:
    return unquote(u.fragment or "")


def _vless(link: str) -> tuple[dict, str]:
    u = urlsplit(link)
    host, port = _endpoint(u)
    uid = unquote(u.username or "")
    if not uid:
        util.die("vless link has no user id")
    q = {k: v[-1] for k, v in parse_qs(u.query, keep_blank_values=True).items()}

    user: dict = {"id": uid, "encryption": q.get("encryption") or "none"}
    if q.get("flow"):
        user["flow"] = q["flow"]

    net_raw = (q.get("type") or "tcp").lower()
    net = _NETWORKS.get(net_raw)
    if not net:
        util.die(f"vless transport {net_raw!r} is not supported "
                 f"(supported: {', '.join(sorted(set(_NETWORKS)))})")
    sec = (q.get("security") or "none").lower()
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
        util.die(f"vless security {sec!r} is not supported (none, tls, reality)")

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

    ob = {"protocol": "vless",
          "settings": {"vnext": [{"address": host, "port": port, "users": [user]}]},
          "streamSettings": stream}
    return ob, _name(u)


def _userinfo(u) -> tuple[str, str]:
    user = unquote(u.username or "")
    pw = unquote(u.password or "")
    if user and u.password is None:
        # v2rayN style: socks://base64(user:pass)@host:port
        padded = user + "=" * (-len(user) % 4)
        for dec in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                text = dec(padded).decode()
            except (binascii.Error, ValueError, UnicodeDecodeError):
                continue
            if ":" in text:
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
