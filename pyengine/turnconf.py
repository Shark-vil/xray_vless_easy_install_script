"""Render the Turnable server config (JSON).

Turnable carries client traffic through the TURN relays of VK calls to this
server, which hands it to a local plain VLESS inbound of Xray (see
inbounds._turnable_local) - so Xray does the routing, as with Hysteria2.
"""
from __future__ import annotations

import json

import state as st

SERVER_ID = "xvei"
PROVIDER_ID = "xvei"
ROUTE_ID = "xray"


def build(data: dict) -> str | None:
    ib = st.get_type(data, "turnable")
    if not ib or not ib.get("priv_key"):
        return None  # keys come from `turnable config keygen` (lib/turnable.sh)
    cfg = {
        "servers": {
            SERVER_ID: {
                "type": "relay",
                "platform_id": "vk.com",
                "call_id": ib["call_id"],
                "pub_key": ib["pub_key"],
                "priv_key": ib["priv_key"],
                "proto": "dtls",
                "listen_addr": f"0.0.0.0:{ib['port']}",
                "public_ip": data.get("server_ip") or data.get("domain") or "",
                "cloak": "none",
                "provider": PROVIDER_ID,
            }
        },
        "providers": {
            PROVIDER_ID: {
                "type": "raw",
                "routes": [{
                    "id": ROUTE_ID,
                    "address": "127.0.0.1",
                    "port": ib["local_port"],
                    "socket": "tcp",
                    "transport": "kcp",
                    "encryption": "handshake",
                    "name": "xvei",
                }],
                "users": [{
                    "uuid": ib["turnable_uuid"],
                    "allowed_routes": [ROUTE_ID],
                    "type": "relay",
                    "peers": ib.get("peers", 5),
                }],
            }
        },
    }
    return json.dumps(cfg, indent=2) + "\n"
