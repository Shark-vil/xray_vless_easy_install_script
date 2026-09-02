"""Camouflage web site for the nginx fallback (what a plain browser sees when
it hits the domain directly, instead of going through VLESS).

Kinds:
  auth     - HTTP Basic auth prompt against an empty user file (always 401).
             This is the default and matches the original script's behaviour.
  blank    - a bare "It works" page
  <preset> - a self-contained static site shipped in assets/sites/<preset>/
             (no external requests at all - safe for camouflage)
  proxy    - reverse-proxy a real upstream. Most sites break when proxied
             (bot walls, host checks, absolute redirects), so a short list of
             known-proxyable upstreams is offered as presets.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit

# name -> (title shown in menus, directory under assets/sites/)
STATIC_PRESETS = {
    "nebula":   "Solar-system facts site",
    "critters": "Animal encyclopedia",
    "game2048": "2048 puzzle game",
    "snake":    "Snake arcade game",
    "notes":    "Minimal personal blog",
}

# name -> upstream URL (curated: these tolerate being reverse-proxied)
PROXY_PRESETS = {
    "example":  "https://example.com",
    "rfc":      "https://www.rfc-editor.org",
    "cern":     "http://info.cern.ch",
    "gnu":      "https://www.gnu.org",
    "iana":     "https://www.iana.org",
}

ASSETS_ROOT = os.path.join(os.path.dirname(__file__), "..", "assets", "sites")
WEBROOT = "/var/www/xvei-site"


def preset_dir(name: str) -> str:
    return os.path.normpath(os.path.join(ASSETS_ROOT, name))


def is_static(kind: str) -> bool:
    return kind in STATIC_PRESETS


def resolve_proxy_url(raw: str) -> str:
    raw = (raw or "").strip()
    if raw in PROXY_PRESETS:
        return PROXY_PRESETS[raw]
    if raw and "://" not in raw:
        raw = "https://" + raw
    return raw


# ---- nginx vhost --------------------------------------------------------

# The vless-tls inbound offers ALPN h2 + http/1.1. When a plain browser hits the
# domain, Xray hands the *decrypted* stream to nginx - and if the browser picked
# h2, that stream is cleartext HTTP/2 (h2c). Serving both h2c and HTTP/1.1 on one
# socket only works on nginx >= 1.25.1, so instead we split by ALPN in Xray's
# fallbacks: http/1.1 traffic lands on :8080, h2c on :8081. Each socket then only
# ever sees a single protocol and the nginx version stops mattering. Without this
# the h2c stream hits an HTTP/1.1-only nginx and the browser gets
# ERR_HTTP2_PROTOCOL_ERROR / -902.
_COMMON = """    server_name _;
    server_tokens off;
"""

_LISTEN_H1 = """    listen 127.0.0.1:8080 default_server;
    listen [::1]:8080 default_server;
"""

_LISTEN_H2C = """    listen 127.0.0.1:8081 http2 default_server;
    listen [::1]:8081 http2 default_server;
"""


def nginx_vhost(data: dict) -> str:
    site = data.get("site") or {"type": "auth"}
    kind = site.get("type", "auth")

    if kind == "proxy":
        url = resolve_proxy_url(site.get("proxy_url", ""))
        parts = urlsplit(url)
        upstream_host = parts.netloc
        scheme = parts.scheme or "https"
        body = f"""
    location / {{
        proxy_pass {scheme}://{upstream_host};
        proxy_http_version 1.1;
        proxy_set_header Host {upstream_host};
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Accept-Encoding "";
        proxy_ssl_server_name on;
        proxy_ssl_name {upstream_host};
        proxy_hide_header X-Frame-Options;
        proxy_hide_header Content-Security-Policy;
        proxy_redirect ~^https?://[^/]+/(.*)$ /$1;
    }}
"""
    elif is_static(kind):
        body = f"""
    root {WEBROOT};
    index index.html;
    location / {{ try_files $uri $uri/ /index.html; }}
"""
    elif kind == "blank":
        body = """
    location / {
        default_type text/html;
        return 200 "<!doctype html><title>It works</title><h1>It works!</h1>";
    }
"""
    elif kind == "404":
        body = "\n    location / { return 404; }\n"
    else:  # auth (default)
        body = """
    location / {
        auth_basic "Restricted";
        auth_basic_user_file /dev/null;
    }
"""
    block = _COMMON + body + "}\n"
    return f"server {{\n{_LISTEN_H1}{block}\nserver {{\n{_LISTEN_H2C}{block}"
