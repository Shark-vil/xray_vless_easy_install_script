"""REALITY key material. Prefers the `xray` binary, falls back to openssl."""
from __future__ import annotations

import base64
import re
import secrets

import util

# Sane public masquerade targets: TLS 1.3, HTTP/2, not behind Cloudflare,
# unlikely to be blocked in the regions this tool targets.
DEFAULT_DESTS = [
    "www.microsoft.com",
    "www.samsung.com",
    "www.nvidia.com",
    "dl.google.com",
    "www.cloudflare.com",
]


def _from_xray() -> tuple[str, str] | None:
    if not util.have("xray"):
        return None
    res = util.run(["xray", "x25519"], check=False)
    priv = pub = ""
    for line in (res.stdout or "").splitlines():
        m = re.match(r"\s*Private\s*key:\s*(\S+)", line, re.I)
        if m:
            priv = m.group(1)
        m = re.match(r"\s*Public\s*key:\s*(\S+)", line, re.I)
        if m:
            pub = m.group(1)
    if priv and pub:
        return priv, pub
    return None


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _from_openssl() -> tuple[str, str] | None:
    if not util.have("openssl"):
        return None
    import subprocess

    priv_der = subprocess.run(
        ["openssl", "genpkey", "-algorithm", "X25519", "-outform", "DER"],
        check=True, capture_output=True).stdout
    pub_der = subprocess.run(
        ["openssl", "pkey", "-inform", "DER", "-pubout", "-outform", "DER"],
        input=priv_der, check=True, capture_output=True).stdout
    # raw scalar = last 32 bytes of each DER blob
    return _b64url(priv_der[-32:]), _b64url(pub_der[-32:])


def gen_keypair() -> tuple[str, str]:
    """Return (private_key, public_key) base64url strings for REALITY."""
    for src in (_from_xray, _from_openssl):
        try:
            kp = src()
        except Exception:  # noqa: BLE001 - fall through to next source
            kp = None
        if kp:
            return kp
    util.die("cannot generate REALITY keys: need `xray x25519` or `openssl`")


def gen_short_id() -> str:
    return secrets.token_hex(8)


def normalize_dest(dest: str) -> tuple[str, str]:
    """Return (dest_with_port, server_name)."""
    dest = (dest or "").strip()
    if not dest:
        dest = DEFAULT_DESTS[0]
    host = dest.split("/")[0]
    if ":" in host:
        return host, host.split(":")[0]
    return f"{host}:443", host
