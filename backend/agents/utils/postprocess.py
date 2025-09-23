from __future__ import annotations

import re
from typing import Iterable, List


_space_re = re.compile(r"\s+")


def dedupe_preserve_order(items: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        key = it.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(it.strip())
    return out


def clamp_length(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[: max(0, max_chars - 1)].rstrip() + "…"


def normalize_spaces(s: str) -> str:
    return _space_re.sub(" ", s.strip())


def strip_trailing_punct(s: str) -> str:
    return s.rstrip(" !?.，。！？…")


def sanitize_hashtag(tag: str) -> str:
    t = tag.strip().lower().replace(" ", "")
    if not t.startswith("#"):
        t = "#" + t
    return t


def top_unique(items: Iterable[str], max_items: int, max_chars: int | None = None) -> List[str]:
    out: List[str] = []
    seen = set()
    for it in items:
        s = normalize_spaces(it)
        s = strip_trailing_punct(s)
        if max_chars:
            s = clamp_length(s, max_chars)
        key = s.lower()
        if key in seen or not s:
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= max_items:
            break
    return out

