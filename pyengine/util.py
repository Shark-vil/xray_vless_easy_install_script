"""Small helpers shared across the engine. Standard library only."""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import uuid

C_INFO = "\033[96m"
C_ERR = "\033[91m"
C_OK = "\033[92m"
C_WARN = "\033[93m"
C_RESET = "\033[0m"


def log(msg: str) -> None:
    print(f"{C_INFO}[xvei]{C_RESET} {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"{C_OK}[xvei]{C_RESET} {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    print(f"{C_WARN}[xvei]{C_RESET} {msg}", file=sys.stderr)


def err(msg: str) -> None:
    print(f"{C_ERR}[xvei:error]{C_RESET} {msg}", file=sys.stderr)


def die(msg: str, code: int = 1) -> "NoReturn":  # type: ignore[name-defined]
    err(msg)
    raise SystemExit(code)


def new_uuid() -> str:
    return str(uuid.uuid4())


def token(nbytes: int = 12) -> str:
    """URL-safe-ish lowercase hex token for ws/xhttp paths."""
    return secrets.token_hex(nbytes)


def rand_password(nbytes: int = 16) -> str:
    import base64

    return base64.b64encode(secrets.token_bytes(nbytes)).decode()


def run(cmd: list[str], *, check: bool = True, capture: bool = True,
        input_text: str | None = None) -> subprocess.CompletedProcess:
    """Run a command as an argv list (never shell=True)."""
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        input=input_text,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def have(binary: str) -> bool:
    from shutil import which

    return which(binary) is not None


def atomic_write(path: str, data: str, mode: int = 0o644) -> None:
    """Write file atomically, preserving a .bak of the previous content."""
    path = os.path.abspath(path)
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                prev = fh.read()
            with open(path + ".bak", "w", encoding="utf-8") as fh:
                fh.write(prev)
        except OSError:
            pass
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".xvei.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(data)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_json(path: str, obj, mode: int = 0o644) -> None:
    atomic_write(path, json.dumps(obj, indent=2, ensure_ascii=False) + "\n", mode)


def prompt(text: str, default: str | None = None) -> str:
    """Read a line from the controlling terminal even when stdin is a pipe."""
    suffix = f" [{default}]" if default else ""
    try:
        with open("/dev/tty", "r+", encoding="utf-8") as tty:
            tty.write(f"{C_INFO}?{C_RESET} {text}{suffix}: ")
            tty.flush()
            line = tty.readline()
    except OSError:
        line = input(f"? {text}{suffix}: ")
    line = (line or "").strip()
    if not line and default is not None:
        return default
    return line


def confirm(text: str, default_yes: bool = True) -> bool:
    d = "Y/n" if default_yes else "y/N"
    ans = prompt(f"{text} ({d})", "y" if default_yes else "n").lower()
    return ans in ("y", "yes", "d", "да")


def choose(text: str, options: list[tuple[str, str]], default: str | None = None) -> str:
    """options = [(value, label), ...]; returns the chosen value."""
    while True:
        print(f"{C_INFO}?{C_RESET} {text}", file=sys.stderr)
        for i, (_val, label) in enumerate(options, 1):
            print(f"   {i}) {label}", file=sys.stderr)
        raw = prompt("Number", default)
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1][0]
        for val, _label in options:
            if raw == val:
                return val
        err("Invalid choice, try again.")
