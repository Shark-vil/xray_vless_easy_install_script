"""Backups of config.json (as text, comments included) and the xvei state.

One file per backup in xvei-backups/ next to config.json. A backup is made
before every change made through xvei, before a restore, and on request; the
oldest are deleted beyond the limit (state "backups_keep", default 20; 0 turns
the automatic ones off). Restoring stages the old config.json like any other
change, so lib/apply.sh validates it before it goes live.
"""
from __future__ import annotations

import difflib
import json
import os
import shutil
import subprocess
import sys
import time

import json5lite
import state as st
import util
import xrayconf as xc

DEFAULT_KEEP = 20
PAGE = 10


def backup_dir() -> str:
    return os.path.join(os.path.dirname(xc.config_path()), "xvei-backups")


def keep_limit(data: dict) -> int:
    v = data.get("backups_keep", DEFAULT_KEEP)
    return v if isinstance(v, int) and v >= 0 else DEFAULT_KEEP


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def entries() -> list[dict]:
    """All backups, newest first: {"id", "created", "reason", "path"}."""
    d = backup_dir()
    out = []
    for name in os.listdir(d) if os.path.isdir(d) else []:
        if not name.endswith(".json"):
            continue
        path = os.path.join(d, name)
        try:
            with open(path, encoding="utf-8") as fh:
                b = json.load(fh)
        except (OSError, ValueError):
            continue
        out.append({"id": name[:-5], "created": b.get("created", ""),
                    "reason": b.get("reason", ""), "path": path})
    return sorted(out, key=lambda e: e["id"], reverse=True)


def load(bid: str) -> dict:
    with open(os.path.join(backup_dir(), bid + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def resolve(ref: str) -> str:
    """A backup by its number in the list (1 = newest) or by its id."""
    es = entries()
    if ref.isdigit() and 1 <= int(ref) <= len(es):
        return es[int(ref) - 1]["id"]
    if any(e["id"] == ref for e in es):
        return ref
    util.die(f"no backup {ref!r} (see: xvei backup list)")


def create(reason: str, *, force: bool = False) -> str | None:
    """Back up config.json and the state as they are on disk now. Nothing
    when automatic backups are off (unless forced) or nothing changed since
    the newest backup."""
    data = st.load()
    keep = keep_limit(data)
    if keep == 0 and not force:
        return None
    config = _read(xc.config_path())
    state = _read(st.state_path())
    es = entries()
    if es:
        last = load(es[0]["id"])
        if last.get("config") == config and last.get("state") == state:
            if force:
                util.log(f"nothing changed since backup {es[0]['id']}")
            return None
    os.makedirs(backup_dir(), mode=0o700, exist_ok=True)
    bid = time.strftime("%Y%m%d-%H%M%S")
    n = 2
    while os.path.exists(os.path.join(backup_dir(), bid + ".json")):
        bid = f"{time.strftime('%Y%m%d-%H%M%S')}-{n}"
        n += 1
    util.write_json(os.path.join(backup_dir(), bid + ".json"),
                    {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "reason": reason,
                     "config": config, "state": state}, mode=0o600)
    _drop_bak(bid)
    if keep:
        for old in entries()[keep:]:
            os.remove(old["path"])
    return bid


def _drop_bak(bid: str) -> None:
    bak = os.path.join(backup_dir(), bid + ".json.bak")
    if os.path.exists(bak):
        os.remove(bak)


def delete(bid: str) -> None:
    os.remove(os.path.join(backup_dir(), bid + ".json"))
    util.ok(f"deleted backup {bid}")


def restore(bid: str) -> None:
    """Stage the backup's config.json and put its state back; the current
    ones are backed up first, so a restore can be undone the same way."""
    b = load(bid)
    create(f"before restoring {bid}", force=True)
    with open(xc.pending_path(), "w", encoding="utf-8") as fh:
        fh.write(b.get("config") or "{}")
    os.chmod(xc.pending_path(), 0o600)
    if b.get("state"):
        util.atomic_write(st.state_path(), b["state"], mode=0o600)
    util.ok(f"backup {bid} staged")


# ---- showing --------------------------------------------------------------

def pager(text: str) -> None:
    """Long text through `less` on a terminal (q to go back), else printed."""
    if sys.stdout.isatty() and shutil.which("less"):
        keys = "q - back, Up/Down/Space - scroll, /text - search"
        subprocess.run(["less", "-RFX", f"-Ps{keys}"], input=text, text=True, check=False)
    else:
        print(text, end="" if text.endswith("\n") else "\n")


def _pretty(text: str, color: bool) -> str:
    try:
        return json5lite.pretty(text or "{}", color=color)
    except json5lite.Json5Error:
        return text


def show_text(bid: str) -> str:
    return _pretty(load(bid).get("config") or "", util.paint("x", util.BOLD) != "x")


def diff_text(bid: str) -> str:
    """What restoring would change: the backup against the live config."""
    old = _pretty(load(bid).get("config") or "", False).splitlines()
    new = _pretty(_read(xc.config_path()), False).splitlines()
    lines = list(difflib.unified_diff(new, old, "config.json (now)", f"backup {bid}",
                                      lineterm=""))
    if not lines:
        return "config.json is the same as in this backup\n"
    painted = []
    for ln in lines:
        if ln.startswith(("+++", "---")):
            painted.append(util.paint(ln, util.BOLD))
        elif ln.startswith("+"):
            painted.append(util.paint(ln, util.GREEN))
        elif ln.startswith("-"):
            painted.append(util.paint(ln, util.RED))
        elif ln.startswith("@@"):
            painted.append(util.paint(ln, util.CYAN))
        else:
            painted.append(ln)
    return "\n".join(painted) + "\n"


def _summary(b: dict) -> str:
    try:
        cfg = json5lite.loads(b.get("config") or "{}")
    except json5lite.Json5Error:
        return "unreadable config"
    if not isinstance(cfg, dict):
        return "unreadable config"
    return (f"{len(xc.inbounds(cfg))} inbounds, {len(xc.outbounds(cfg))} outbounds, "
            f"{len(xc.rules_view(cfg))} rules")


def print_page(page: int) -> int:
    """List one page (0-based); returns the number of pages."""
    es = entries()
    pages = max(1, -(-len(es) // PAGE))
    page = min(max(page, 0), pages - 1)
    data = st.load()
    keep = keep_limit(data)
    util.header("Backups")
    print(util.paint(f"  {backup_dir()}  {util.SYM['sep']}  keep "
                     + (f"{keep}" if keep else "0 (automatic backups off)")
                     + f"  {util.SYM['sep']}  page {page + 1}/{pages}", util.DIM))
    if not es:
        print(util.paint("    (no backups yet)", util.DIM))
    for i, e in enumerate(es[page * PAGE:(page + 1) * PAGE], page * PAGE + 1):
        print(f"  {util.paint(f'{i:>3})', util.CYAN)} {util.paint(e['created'], util.BOLD)}  "
              f"{e['reason']}")
    return pages


# ---- menu -----------------------------------------------------------------

def _menu_one(bid: str) -> bool:
    """One backup; True when it was staged for restoring."""
    while True:
        b = load(bid)
        util.header(f"Backup {bid}")
        print(f"  {util.paint('Created', util.DIM)}  {b.get('created', '')}")
        print(f"  {util.paint('Reason ', util.DIM)}  {b.get('reason', '')}")
        print(f"  {util.paint('Config ', util.DIM)}  {_summary(b)}")
        print()
        act = util.choose("Action", [
            ("show", "View its config.json"),
            ("diff", "What restoring would change (against the current config)"),
            ("restore", "Restore it"),
            ("delete", "Delete it"),
            ("back", "Back"),
        ], "back")
        if act == "back":
            return False
        if act == "show":
            pager(show_text(bid))
        elif act == "diff":
            pager(diff_text(bid))
        elif act == "restore":
            if util.confirm(f"Restore config.json and the xvei state from {bid}? "
                            "The current ones are backed up first", default_yes=False):
                restore(bid)
                return True
        elif act == "delete":
            if util.confirm(f"Delete backup {bid}?", default_yes=False):
                delete(bid)
                return False


def menu(data: dict) -> bool:
    """The backups menu; True when a backup was staged for restoring."""
    page = 0
    while True:
        pages = print_page(page)
        print()
        print(util.paint("  Number: open a backup   n / p: next / previous page   "
                         "c: back up now   k: how many to keep   0: back", util.DIM))
        raw = util.prompt("Choose", "0").strip().lower()
        if raw in ("0", "", "q"):
            return False
        if raw == "n":
            page = min(page + 1, pages - 1)
        elif raw == "p":
            page = max(page - 1, 0)
        elif raw == "c":
            note = util.prompt("Note (optional)")
            bid = create("manual" + (f": {note}" if note else ""), force=True)
            if bid:
                util.ok(f"backup {bid} created")
            page = 0
        elif raw == "k":
            cur = keep_limit(st.load())
            val = util.prompt("How many backups to keep (0 = automatic backups off)", str(cur))
            if val.isdigit():
                set_keep(int(val))
        elif raw.isdigit() and 1 <= int(raw) <= len(entries()):
            if _menu_one(entries()[int(raw) - 1]["id"]):
                return True
        else:
            util.err("Invalid choice, try again.")


def set_keep(n: int) -> None:
    data = st.load()
    data["backups_keep"] = n
    st.save(data)
    if n:
        for old in entries()[n:]:
            os.remove(old["path"])
        util.ok(f"keeping the last {n} backups")
    else:
        util.ok("automatic backups off (existing ones are kept; 'back up now' still works)")
