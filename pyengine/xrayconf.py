"""Assemble the full Xray config.json from state."""
from __future__ import annotations

import copy

import inbounds
import outbounds
import routing


def build(data: dict) -> dict:
    if data.get("adopted"):
        return _build_adopted(data)
    return {
        "log": {"loglevel": "warning", "dnsLog": False},
        "dns": {"servers": ["1.1.1.1", "8.8.8.8", "localhost"]},
        "inbounds": inbounds.build(data),
        "outbounds": outbounds.build(data),
        "routing": routing.build(data),
    }


def _build_adopted(data: dict) -> dict:
    """The adopted config with xvei's parts merged in. Every key, inbound,
    outbound and rule it had stays as is; its first outbound stays first (it
    is Xray's default route). xvei's own outbounds whose tag already exists
    there (e.g. "direct", "block") are not added twice, and "direct" / "block"
    only when a rule uses them - with no xvei edits the result equals the
    adopted config."""
    cfg = copy.deepcopy(data["base"])
    ibs = list(cfg.get("inbounds") or []) + inbounds.build(data)
    if "inbounds" in cfg or ibs:
        cfg["inbounds"] = ibs
    rt = routing.build(data)
    used = {r.get("outboundTag") for r in rt.get("rules", [])}
    base_out = list(cfg.get("outbounds") or [])
    have = {o.get("tag") for o in base_out}
    obs = base_out + [
        o for o in outbounds.build(data)
        if o["tag"] not in have
        and (o["tag"] not in (outbounds.TAG_DIRECT, outbounds.TAG_BLOCK) or o["tag"] in used)]
    if "outbounds" in cfg or obs:
        cfg["outbounds"] = obs
    if "routing" in cfg or rt.get("rules"):
        cfg["routing"] = rt
    return cfg
