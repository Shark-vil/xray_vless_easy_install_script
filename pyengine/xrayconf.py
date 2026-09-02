"""Assemble the full Xray config.json from state."""
from __future__ import annotations

import inbounds
import outbounds
import routing


def build(data: dict) -> dict:
    return {
        "log": {"loglevel": "warning", "dnsLog": False},
        "dns": {"servers": ["1.1.1.1", "8.8.8.8", "localhost"]},
        "inbounds": inbounds.build(data),
        "outbounds": outbounds.build(data),
        "routing": routing.build(data),
    }
