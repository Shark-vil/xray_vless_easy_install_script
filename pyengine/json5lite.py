"""Small JSON5 reader + comment-preserving pretty printer (stdlib only).

Xray configs are often hand-written: // and /* */ comments, trailing commas,
sometimes single quotes or bare keys. `loads` accepts that (JSON5 subset:
comments, trailing commas, '...' strings, identifier keys, hex / +/- / .5 /
Infinity / NaN numbers; '#' line comments too). `pretty` re-indents the text
for reading and keeps the comments.
"""
from __future__ import annotations

import json
import re

_NUM = re.compile(
    r"[+-]?(?:0[xX][0-9a-fA-F]+|Infinity|NaN|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)")
_IDENT = re.compile(r"[A-Za-z_$][\w$]*")
_ESC = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v",
        "0": "\0", "/": "/", "\\": "\\", '"': '"', "'": "'"}


class Json5Error(ValueError):
    pass


class _Tok:
    __slots__ = ("kind", "text", "value", "line", "own_line")

    def __init__(self, kind, text, value, line, own_line):
        self.kind = kind          # punct | string | number | ident | comment
        self.text = text          # source text (numbers, comments, punct)
        self.value = value        # decoded value (strings, numbers, idents)
        self.line = line
        self.own_line = own_line  # a newline separates it from the previous token


def _tokens(text: str) -> list[_Tok]:
    toks: list[_Tok] = []
    i, n, line, nl = 0, len(text), 1, True
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            nl = True
            i += 1
            continue
        if c in " \t\r﻿ ":
            i += 1
            continue
        if text.startswith("//", i) or c == "#":
            j = text.find("\n", i)
            j = n if j < 0 else j
            toks.append(_Tok("comment", text[i:j].rstrip(), None, line, nl))
            i = j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            if j < 0:
                raise Json5Error(f"line {line}: unterminated /* comment")
            body = text[i:j + 2]
            toks.append(_Tok("comment", body, None, line, nl))
            line += body.count("\n")
            i = j + 2
            nl = False
            continue
        start_line, own = line, nl
        nl = False
        if c in "{}[]:,":
            toks.append(_Tok("punct", c, None, line, own))
            i += 1
        elif c in "\"'":
            j, buf = i + 1, []
            while True:
                if j >= n:
                    raise Json5Error(f"line {start_line}: unterminated string")
                ch = text[j]
                if ch == c:
                    break
                if ch == "\n":
                    raise Json5Error(f"line {start_line}: newline inside a string")
                if ch == "\\":
                    j += 1
                    e = text[j] if j < n else ""
                    if e == "u":
                        try:
                            buf.append(chr(int(text[j + 1:j + 5], 16)))
                        except ValueError:
                            raise Json5Error(f"line {line}: bad \\u escape") from None
                        j += 4
                    elif e == "x":
                        buf.append(chr(int(text[j + 1:j + 3], 16)))
                        j += 2
                    elif e == "\n":
                        line += 1  # line continuation
                    else:
                        buf.append(_ESC.get(e, e))
                else:
                    buf.append(ch)
                j += 1
            toks.append(_Tok("string", text[i:j + 1], "".join(buf), start_line, own))
            i = j + 1
        else:
            m = _NUM.match(text, i)
            if m and (c.isdigit() or c in "+-."
                      or m.group(0).lstrip("+-") in ("Infinity", "NaN")):
                s = m.group(0)
                body = s.lstrip("+-")
                if body.startswith(("0x", "0X")):
                    val = int(s[:len(s) - len(body)] + str(int(body, 16)))
                elif body in ("Infinity", "NaN"):
                    val = float(s)
                elif any(x in body for x in ".eE"):
                    val = float(s)
                else:
                    val = int(s)
                toks.append(_Tok("number", s, val, line, own))
                i = m.end()
                continue
            m = _IDENT.match(text, i)
            if not m:
                raise Json5Error(f"line {line}: unexpected character {c!r}")
            word = m.group(0)
            val = {"true": True, "false": False, "null": None}.get(word, word)
            toks.append(_Tok("ident", word, val, line, own))
            i = m.end()
    return toks


def loads(text: str):
    toks = [t for t in _tokens(text) if t.kind != "comment"]
    pos = 0

    def peek() -> _Tok | None:
        return toks[pos] if pos < len(toks) else None

    def take(expect: str | None = None) -> _Tok:
        nonlocal pos
        t = peek()
        if t is None:
            raise Json5Error("unexpected end of file")
        if expect is not None and not (t.kind == "punct" and t.text == expect):
            raise Json5Error(f"line {t.line}: expected {expect!r}, got {t.text!r}")
        pos += 1
        return t

    def value():
        t = take()
        if t.kind == "punct" and t.text == "{":
            obj = {}
            while True:
                t = peek()
                if t and t.kind == "punct" and t.text == "}":
                    take()
                    return obj
                k = take()
                if k.kind not in ("string", "ident"):
                    raise Json5Error(f"line {k.line}: expected a key, got {k.text!r}")
                key = k.value if k.kind == "string" else k.text
                take(":")
                obj[key] = value()
                t = take()
                if t.kind == "punct" and t.text == "}":
                    return obj
                if not (t.kind == "punct" and t.text == ","):
                    raise Json5Error(f"line {t.line}: expected ',' or '}}', got {t.text!r}")
        if t.kind == "punct" and t.text == "[":
            arr = []
            while True:
                t = peek()
                if t and t.kind == "punct" and t.text == "]":
                    take()
                    return arr
                arr.append(value())
                t = take()
                if t.kind == "punct" and t.text == "]":
                    return arr
                if not (t.kind == "punct" and t.text == ","):
                    raise Json5Error(f"line {t.line}: expected ',' or ']', got {t.text!r}")
        if t.kind in ("string", "number"):
            return t.value
        if t.kind == "ident" and t.text in ("true", "false", "null"):
            return t.value
        raise Json5Error(f"line {t.line}: unexpected {t.text!r}")

    result = value()
    if peek() is not None:
        raise Json5Error(f"line {peek().line}: unexpected {peek().text!r} after the end")
    return result


# ---- pretty printer --------------------------------------------------------

_C = {"key": "\033[36m", "string": "\033[32m", "number": "\033[33m",
      "literal": "\033[35m", "comment": "\033[90m", "off": "\033[0m"}


def pretty(text: str, color: bool = False, indent: str = "  ") -> str:
    toks = _tokens(text)
    sig = [k for k, t in enumerate(toks) if t.kind != "comment"]
    next_sig = {}
    for a, b in zip(sig, sig[1:] + [None]):
        next_sig[a] = b

    def paint(kind: str, s: str) -> str:
        return f"{_C[kind]}{s}{_C['off']}" if color else s

    def scalar(k: int) -> str:
        t = toks[k]
        nxt = next_sig.get(k)
        is_key = nxt is not None and toks[nxt].kind == "punct" and toks[nxt].text == ":"
        if t.kind == "string" or (t.kind == "ident" and is_key):
            s = json.dumps(t.value if t.kind == "string" else t.text, ensure_ascii=False)
            return paint("key" if is_key else "string", s)
        if t.kind == "number":
            return paint("number", t.text)
        return paint("literal", t.text)

    def close_of(k: int) -> int | None:
        depth = 0
        for j in range(k, len(toks)):
            t = toks[j]
            if t.kind == "punct" and t.text in "[{":
                depth += 1
            elif t.kind == "punct" and t.text in "]}":
                depth -= 1
                if depth == 0:
                    return j
        return None

    def inline_array(k: int) -> tuple[str, int] | None:
        """Short arrays of scalars stay on one line: ["h2", "http/1.1"]."""
        end = close_of(k)
        if end is None:
            return None
        parts, plain = [], 0
        for j in range(k + 1, end):
            t = toks[j]
            if t.kind == "comment" or (t.kind == "punct" and t.text != ","):
                return None
            if t.kind != "punct":
                parts.append(scalar(j))
                plain += len(t.text) + 2
        if plain > 60:
            return None
        return "[" + ", ".join(parts) + "]", end

    out: list[str] = []
    level = 0
    pending_nl = False
    prev_sig = None

    def newline() -> None:
        out.append("\n" + indent * level)

    k = 0
    while k < len(toks):
        t = toks[k]
        if t.kind == "comment":
            body = paint("comment", t.text)
            if not t.own_line and out:
                out.append(" " + body)
            else:
                if out:
                    newline()
                out.append(body)
            pending_nl = True
            k += 1
            continue
        if t.kind == "punct" and t.text in "]}":
            level = max(level - 1, 0)
            empty = (prev_sig is not None and toks[prev_sig].kind == "punct"
                     and toks[prev_sig].text in "[{" and toks[k - 1].kind != "comment")
            if not empty:
                newline()
            out.append(t.text)
            pending_nl = False
            prev_sig = k
            k += 1
            continue
        if t.kind == "punct" and t.text == ",":
            nxt = next_sig.get(k)
            if nxt is not None and toks[nxt].kind == "punct" and toks[nxt].text in "]}":
                k += 1  # drop trailing comma
                continue
            out.append(",")
            pending_nl = True
            prev_sig = k
            k += 1
            continue
        if pending_nl:
            newline()
            pending_nl = False
        if t.kind == "punct" and t.text == ":":
            out.append(": ")
        elif t.kind == "punct" and t.text in "[{":
            short = inline_array(k) if t.text == "[" else None
            if short:
                out.append(short[0])
                prev_sig = short[1]
                k = short[1] + 1
                continue
            out.append(t.text)
            level += 1
            pending_nl = True
        else:
            out.append(scalar(k))
        prev_sig = k
        k += 1
    return "".join(out).lstrip("\n") + "\n"
