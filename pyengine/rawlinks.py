"""Client share links read off the inbounds in config.json.

The link comes from the inbound as it is: its clients, transport and
security - whoever created it, xvei or a hand edit. An inbound that only
listens on a unix socket or on localhost is reached through the TLS
fallbacks of another inbound (the usual "WS behind VLESS TLS on :443"); the
link then takes the port and TLS of that inbound.
"""
from __future__ import annotations

import base64
import json
from urllib.parse import quote, urlencode

import xrayconf as xc


def host_for(data: dict, *, by_ip: bool = False) -> str:
    """Where clients connect: the domain, or the IP (REALITY has no cert)."""
    if by_ip or not data.get("domain"):
        return data.get("server_ip") or data.get("domain") or "SERVER_IP"
    return data["domain"]


def _carrier(cfg: dict, ib: dict) -> tuple[dict, dict] | None:
    """The inbound (and its fallback entry) that hands traffic to `ib`."""
    targets = {str(ib.get("listen") or ""), str(ib.get("port") or "")} - {""}
    if ib.get("listen") in xc.LOCAL_LISTENS and ib.get("port"):
        targets.add(f"{ib['listen']}:{ib['port']}")
    for x in xc.inbounds(cfg):
        if x is ib:
            continue
        for fb in (x.get("settings") or {}).get("fallbacks") or []:
            if str(fb.get("dest")) in targets:
                return x, fb
    return None


def _reachable(cfg: dict, ib: dict) -> tuple[int, dict, bool] | str:
    """(public port, stream settings that do the TLS, carried by a fallback)
    or why there is no link."""
    if xc.is_public(ib):
        return xc.port_of(ib), ib.get("streamSettings") or {}, False
    carried = _carrier(cfg, ib)
    if not carried:
        return "local only"
    outer = carried[0]
    outer_ss = outer.get("streamSettings") or {}
    if outer_ss.get("security") not in ("tls", "reality") or xc.port_of(outer) is None:
        return "local only"
    return xc.port_of(outer), outer_ss, True


def _tls_params(data: dict, sec_ss: dict) -> dict | None:
    """Query parameters for the security layer; None if it cannot be linked."""
    sec = sec_ss.get("security") or "none"
    if sec == "tls":
        tls = sec_ss.get("tlsSettings") or {}
        return {"security": "tls", "sni": tls.get("serverName") or data.get("domain") or "",
                "fp": "chrome"}
    if sec == "reality":
        rs = sec_ss.get("realitySettings") or {}
        pbk = x25519_public(rs.get("privateKey") or "")
        names = rs.get("serverNames") or []
        if not pbk or not names:
            return None
        return {"security": "reality", "sni": names[0], "fp": "chrome", "pbk": pbk,
                "sid": (rs.get("shortIds") or [""])[0]}
    return {"security": "none"}


def _transport_params(ss: dict, host: str) -> dict:
    """`host`: the Host header when the inbound does not set one (the domain
    behind TLS; none with REALITY, whose SNI is someone else's site)."""
    net = ss.get("network") or "tcp"
    q: dict = {"type": {"splithttp": "xhttp", "raw": "tcp"}.get(net, net)}
    if net == "ws":
        ws = ss.get("wsSettings") or {}
        q["host"] = ws.get("host") or (ws.get("headers") or {}).get("Host") or host
        q["path"] = ws.get("path") or "/"
    elif net in ("xhttp", "splithttp"):
        xh = ss.get("xhttpSettings") or ss.get("splithttpSettings") or {}
        q["host"] = xh.get("host") or host
        q["path"] = xh.get("path") or "/"
        q["mode"] = xh.get("mode") or "auto"
    elif net == "httpupgrade":
        hu = ss.get("httpupgradeSettings") or {}
        q["host"] = hu.get("host") or host
        q["path"] = hu.get("path") or "/"
    elif net == "grpc":
        q["serviceName"] = (ss.get("grpcSettings") or {}).get("serviceName") or ""
        q["mode"] = "gun"
    return q


def _labeller(data: dict, ib: dict, clients: list[dict]):
    """One client: "tag@host"; several: "tag-email" so they can be told apart."""
    def label(c: dict) -> str:
        if len(clients) > 1 and c.get("email"):
            return f"{ib['tag']}-{c['email']}"
        return f"{ib['tag']}@{data.get('domain') or data.get('server_ip') or 'xvei'}"
    return label


def inbound_links(data: dict, cfg: dict, ib: dict) -> tuple[list[tuple[str, str]], str]:
    """[(client name, link)] for one inbound, and a note when there are none."""
    proto = ib.get("protocol")
    settings = ib.get("settings") or {}
    if proto in ("socks", "http"):
        return _proxy_links(data, ib, proto, settings)
    if proto not in ("vless", "vmess", "trojan", "shadowsocks"):
        return [], f"{proto}: no share link format"
    where = _reachable(cfg, ib)
    if isinstance(where, str):
        return [], where
    port, sec_ss, carried = where
    tls = _tls_params(data, sec_ss)
    if tls is None:
        return [], "REALITY keys / server names missing"
    ss = ib.get("streamSettings") or {}
    host = host_for(data, by_ip=tls["security"] == "reality")
    default_host = (data.get("domain") or tls.get("sni", "")) if tls["security"] == "tls" else ""
    q_base = {**tls, **_transport_params(ss, default_host)}
    q_base = {k: v for k, v in q_base.items() if v != "" or k == "path"}
    if carried and q_base["type"] in ("ws", "httpupgrade", "tcp"):
        # behind the :443 fallbacks only HTTP/1.1 reaches them (h2 goes to the site)
        q_base["alpn"] = "http/1.1"

    out: list[tuple[str, str]] = []
    if proto == "shadowsocks":
        clients = settings.get("clients") or [settings]
        label = _labeller(data, ib, clients)
        for c in clients:
            method = c.get("method") or settings.get("method")
            pw = c.get("password")
            if not method or not pw:
                continue
            if method.startswith("2022-") and c is not settings and settings.get("password"):
                pw = f"{settings['password']}:{pw}"
            info = base64.urlsafe_b64encode(f"{method}:{pw}".encode()).decode().rstrip("=")
            out.append((c.get("email") or "", f"ss://{info}@{host}:{port}#{quote(label(c))}"))
        return out, "" if out else "no clients"

    clients = [c for c in settings.get("clients") or [] if isinstance(c, dict)]
    label = _labeller(data, ib, clients)
    for c in clients:
        if proto == "vmess":
            j = {"v": "2", "ps": label(c), "add": host, "port": str(port), "id": c.get("id", ""),
                 "aid": "0", "scy": "auto", "net": q_base["type"], "type": "none",
                 "host": q_base.get("host", ""), "path": q_base.get("path", ""),
                 "tls": "" if tls["security"] == "none" else tls["security"],
                 "sni": tls.get("sni", ""), "fp": "chrome"}
            if q_base.get("alpn"):
                j["alpn"] = q_base["alpn"]
            out.append((c.get("email") or "",
                        "vmess://" + base64.b64encode(json.dumps(j).encode()).decode()))
            continue
        q = dict(q_base)
        if proto == "vless":
            q = {"encryption": "none", **q}
            if c.get("flow"):
                q["flow"] = c["flow"]
            cred = c.get("id", "")
        else:
            cred = quote(c.get("password", ""), safe="")
        out.append((c.get("email") or "",
                    f"{proto}://{cred}@{host}:{port}?{urlencode(q)}#{quote(label(c))}"))
    return out, "" if out else "no clients"


def _proxy_links(data: dict, ib: dict, proto: str,
                 settings: dict) -> tuple[list[tuple[str, str]], str]:
    if not xc.is_public(ib):
        return [], "local only"
    host, port = host_for(data, by_ip=True), xc.port_of(ib)
    accounts = settings.get("accounts") or [{}]
    out: list[tuple[str, str]] = []
    for a in accounts:
        user, pw = a.get("user"), a.get("pass")
        auth = f"{quote(user, safe='')}:{quote(pw or '', safe='')}@" if user else ""
        scheme = "socks5" if proto == "socks" else "http"
        out.append((user or "", f"{scheme}://{auth}{host}:{port}#{quote(ib['tag'])}"))
        if proto == "socks":
            # opens straight in Telegram
            q = {"server": host, "port": port, **({"user": user, "pass": pw} if user else {})}
            out.append((f"{user or ib['tag']} (Telegram)",
                        f"https://t.me/socks?{urlencode(q)}"))
    return out, ""


# ---- X25519 public key from a REALITY private key (RFC 7748) ------------

_P = 2 ** 255 - 19


def x25519_public(private_b64: str) -> str:
    try:
        k = bytearray(base64.urlsafe_b64decode(private_b64 + "=" * (-len(private_b64) % 4)))
    except ValueError:
        return ""
    if len(k) != 32:
        return ""
    k[0] &= 248
    k[31] &= 127
    k[31] |= 64
    scalar = int.from_bytes(k, "little")
    x1, x2, z2, x3, z3, swap = 9, 1, 0, 9, 1, 0
    for t in reversed(range(255)):
        bit = (scalar >> t) & 1
        swap ^= bit
        if swap:
            x2, x3, z2, z3 = x3, x2, z3, z2
        swap = bit
        a, b = (x2 + z2) % _P, (x2 - z2) % _P
        aa, bb = a * a % _P, b * b % _P
        e = (aa - bb) % _P
        c, d = (x3 + z3) % _P, (x3 - z3) % _P
        da, cb = d * a % _P, c * b % _P
        x3 = (da + cb) ** 2 % _P
        z3 = x1 * (da - cb) ** 2 % _P
        x2 = aa * bb % _P
        z2 = e * (aa + 121665 * e) % _P
    if swap:
        x2, z2 = x3, z3
    pub = x2 * pow(z2, _P - 2, _P) % _P
    return base64.urlsafe_b64encode(pub.to_bytes(32, "little")).decode().rstrip("=")
