"""Shared helpers for lazarev-translator scripts (stdlib only).

Every script imports this first: it forces UTF-8 on stdout/stderr, because the
Windows console defaults to cp1252/cp1256 and crashes on Cyrillic or Arabic.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SKILL_DIR = Path(__file__).resolve().parent.parent
GLOSSARY = SKILL_DIR / "references" / "glossary.tsv"
REGISTRY = Path.home() / ".lazarev-translator" / "projects.json"

# ---------------------------------------------------------------- text normalization
_AR_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_AR_ALEF = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"})


def norm_ar(text: str) -> str:
    """Normalize Arabic for matching only (never for output)."""
    text = unicodedata.normalize("NFKC", text)  # undo presentation forms from PDFs
    text = _AR_DIACRITICS.sub("", text)
    return text.translate(_AR_ALEF)


def norm_ru(text: str) -> str:
    return text.lower().replace("ё", "е")


# Cyrillic-aware "start of word" for glossary stems
RU_WORD_START = r"(?<![а-яёa-z])"

# ---------------------------------------------------------------- files
def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_text(path: str | Path, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def read_json(path: str | Path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def write_json(path: str | Path, data) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def sha1_file(path: str | Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- names
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
    "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def slugify(text: str, max_len: int = 60) -> str:
    """ASCII slug for working folders/files (Russian is transliterated)."""
    text = norm_ru(text)
    text = "".join(_TRANSLIT.get(ch, ch) for ch in text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text[:max_len].rstrip("-")) or "untitled"


def arabic_filename(title: str, ext: str = ".md", max_len: int = 110, suffix: str = "") -> str:
    """Windows-safe Arabic file name for final deliverables; the suffix survives truncation."""
    title = re.sub(r"\s*:\s*", " – ", title)          # «العنوان: الفرعي» keeps its break as a dash
    name = re.sub(r'[\\/:*?"<>|\u0000-\u001f]', " ", title)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if len(name) > max_len:                      # cut at a word boundary, never mid-word
        name = name[:max_len].rsplit(" ", 1)[0]
    return (name.strip(" .") or "ترجمة") + suffix + ext


# ---------------------------------------------------------------- glossary
GLOSSARY_COLS = ["id", "topics", "ru", "en", "ar", "accept", "wrong", "wrong_unless_ru",
                 "wrong_level", "status", "evidence", "note"]
STATUS_RANK = {"locked": 0, "attested": 1, "book": 2, "inferred": 3}


def load_glossary(overlay: str | Path | None = None) -> list[dict]:
    """Core glossary plus an optional per-project overlay (same columns).

    Precedence: locked > attested > book overlay > inferred. An overlay row with the
    same id replaces a core row only if the core row is inferred; otherwise it is kept
    as an additional row and flagged as a conflict.
    """
    rows = _read_tsv(GLOSSARY)
    if overlay and Path(overlay).exists():
        by_id = {r["id"]: r for r in rows}
        for r in _read_tsv(overlay):
            r.setdefault("status", "book")
            r["status"] = r["status"] or "book"
            core = by_id.get(r["id"])
            if core is None:
                rows.append(r)
            elif core["status"] == "inferred":
                rows[rows.index(core)] = r
            else:
                r["conflict"] = f"overlay disagrees with {core['status']} core row; core wins"
                rows.append(r)
    for r in rows:
        r["_ru"] = re.compile(RU_WORD_START + "(?:" + r["ru"] + ")") if r.get("ru") else None
        r["_accept"] = re.compile(norm_ar(r["accept"])) if r.get("accept") else None
        r["_wrong"] = re.compile(norm_ar(r["wrong"])) if r.get("wrong") else None
        r["_unless"] = (re.compile(RU_WORD_START + "(?:" + r["wrong_unless_ru"] + ")")
                        if r.get("wrong_unless_ru") else None)
    return rows


def _read_tsv(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for r in rows:
        for c in GLOSSARY_COLS:
            r.setdefault(c, "")
            r[c] = r[c] or ""
    return rows


# ---------------------------------------------------------------- paragraph IDs
PARA_MARK = re.compile(r"<!--\s*(p\d{4,6}|s\d{4,6})(?:\s+[^>]*)?-->")


def split_marked(text: str) -> list[tuple[str, str]]:
    """Return [(id, body)] for text that uses <!-- p0001 --> markers."""
    parts = PARA_MARK.split(text)
    out = []
    # parts: [pre, id1, body1, id2, body2, ...]
    for i in range(1, len(parts), 2):
        out.append((parts[i], parts[i + 1].strip()))
    return out


# ---------------------------------------------------------------- registry
def registry_add(kind: str, slug: str, root: Path, title: str = "") -> None:
    reg = read_json(REGISTRY, default={"projects": []})
    reg["projects"] = [p for p in reg["projects"] if p.get("path") != str(root)]
    reg["projects"].append({"kind": kind, "slug": slug, "path": str(root), "title": title})
    write_json(REGISTRY, reg)


def die(msg: str, code: int = 1):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)
