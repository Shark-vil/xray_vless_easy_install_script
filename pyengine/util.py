"""Small helpers shared across the engine. Standard library only."""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import uuid

# ---- terminal output -------------------------------------------------------
# Colors only on a terminal (never in pipes / files) and never with NO_COLOR.
# lib/common.sh uses the same symbols and colors.

def _colors(stream) -> bool:
    return (hasattr(stream, "isatty") and stream.isatty()
            and not os.environ.get("NO_COLOR") and os.environ.get("TERM") != "dumb")


_ERR_COLOR = _colors(sys.stderr)
C_INFO = "\033[96m" if _ERR_COLOR else ""
C_ERR = "\033[91m" if _ERR_COLOR else ""
C_OK = "\033[92m" if _ERR_COLOR else ""
C_WARN = "\033[93m" if _ERR_COLOR else ""
C_RESET = "\033[0m" if _ERR_COLOR else ""

BOLD, DIM, CYAN, GREEN, YELLOW, RED = "1", "2", "96", "92", "93", "91"

_UNI = {"rule": "─", "bullet": "•", "dot": "●", "arrow": "→", "back": "←", "sep": "·",
        "ok": "✓", "err": "✗", "info": "›"}
_ASCII = {"rule": "-", "bullet": "*", "dot": "*", "arrow": "->", "back": "<-", "sep": "|",
          "ok": "+", "err": "x", "info": ">"}


def _unicode_ok(stream) -> bool:
    try:
        "".join(_UNI.values()).encode(getattr(stream, "encoding", None) or "ascii")
        return True
    except (LookupError, UnicodeEncodeError):
        return False


# box-drawing and symbols, or plain ASCII on a terminal / locale without UTF-8
# (lib/common.sh sets XVEI_ASCII from the locale)
SYM = (_UNI if not os.environ.get("XVEI_ASCII")
       and _unicode_ok(sys.stdout) and _unicode_ok(sys.stderr) else _ASCII)


def paint(text: str, *codes: str, stream=None) -> str:
    """`text` in the given SGR codes (BOLD, CYAN, ...) if `stream` shows colors."""
    if not codes or not _colors(stream or sys.stdout):
        return text
    return f"\033[{';'.join(codes)}m{text}\033[0m"


def header(title: str, stream=None) -> None:
    """A section title: a blank line, then `── Title ─────`."""
    stream = stream or sys.stdout
    r = SYM["rule"]
    line = f"{r}{r} {title} " + r * max(3, 60 - len(title) - 4)
    print(f"\n{paint(line, BOLD, CYAN, stream=stream)}", file=stream)


def subheader(title: str, stream=None) -> None:
    stream = stream or sys.stdout
    print(paint(title, BOLD, stream=stream), file=stream)


def log(msg: str) -> None:
    print(f"{C_INFO}{SYM['info']}{C_RESET} {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"{C_OK}{SYM['ok']}{C_RESET} {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    print(f"{C_WARN}!{C_RESET} {msg}", file=sys.stderr)


def err(msg: str) -> None:
    print(f"{C_ERR}{SYM['err']} {msg}{C_RESET}", file=sys.stderr)


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


def prompt(text: str, default: str | None = None, *, show_default: bool = True) -> str:
    """Read a line from the controlling terminal even when stdin is a pipe."""
    suffix = paint(f" [{default}]", DIM, stream=sys.stderr) if default and show_default else ""
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
    ans = prompt(f"{text} {paint(f'({d})', DIM, stream=sys.stderr)}",
                 "y" if default_yes else "n", show_default=False).lower()
    return ans in ("y", "yes", "d", "да")


def choose(text: str, options: list[tuple[str, str]], default: str | None = None) -> str:
    """options = [(value, label), ...]; returns the chosen value. A "back"
    option is always listed last as 0, the others are numbered from 1."""
    back = [o for o in options if o[0] == "back"]
    items = [o for o in options if o[0] != "back"]
    if back and default == "back":
        default = "0"
    w = len(str(len(items)))
    sys.stdout.flush()  # whatever the menu printed above goes first
    while True:
        print(f"{C_INFO}?{C_RESET} {paint(text, BOLD, stream=sys.stderr)}", file=sys.stderr)
        for i, (_val, label) in enumerate(items, 1):
            num = paint(f"{i:>{w}})", CYAN, stream=sys.stderr)
            print(f"  {num} {label}", file=sys.stderr)
        if back:
            print(paint(f"  {'0':>{w}}) {back[0][1]}", DIM, stream=sys.stderr), file=sys.stderr)
        raw = prompt("Choose", default)
        if back and raw == "0":
            return "back"
        if raw.isdigit() and 1 <= int(raw) <= len(items):
            return items[int(raw) - 1][0]
        for val, _label in options:
            if raw == val:
                return val
        err("Invalid choice, try again.")
