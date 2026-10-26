"""Query the Sablabal glossary (references/glossary.tsv, the single source of truth).

Usage:
  python glossary.py --scan CHUNK.md [--overlay book-glossary.tsv] [--lang ru|en]
        -> the glossary slice for this chunk (only terms that occur in it), most frequent first
  python glossary.py --unknown SOURCE.md [--top 40] [--overlay ...]
        -> frequent Russian words NOT covered by the glossary (candidates for book-glossary.tsv)
  python glossary.py --topic money|family|children|disease|religion|fate|field|meta|core
  python glossary.py --term WORD          (search ru / en / ar columns)
  python glossary.py --render-topics DIR  (regenerate the readable topic views)
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

from _common import STATUS_RANK, load_glossary, norm_ar, norm_ru, read_text, write_text

TOPIC_NAMES = {
    "core": "المصطلحات الأساسية", "field": "الحقل والطاقة والكون", "meta": "الماورائيات",
    "money": "المال والأعمال", "family": "العائلة والعلاقات", "children": "الأطفال والحمل",
    "disease": "الأمراض والجسد", "religion": "الدين والصلاة", "fate": "المصير والمستقبل",
}
RU_STOP = set("""это этого этой этом этот эта эти тогда когда потому поэтому который которая которые
которых которое которого очень может можно нужно надо будет было были была если чтобы только
теперь всегда себя свою своих своей своего своим свои меня мене тебя него нему неё нее ними
сейчас после перед между через более менее самый самая самое также тоже ещё однако просто
человек человека человеку людей люди людям жизни жизнь жизнью сказал говорит говорю спросил
сильно много мало потом почему каждый каждая всего всех всем всеми вообще значит именно""".split())


def _e(s: str) -> str:
    """Escape pipes so regexes do not break Markdown tables."""
    return (s or "").replace("|", r"\|")


def table(rows, counts=None):
    out = ["| ru | ar (Sablabal) | status | note |", "|---|---|---|---|"]
    for r in rows:
        c = f" ×{counts[r['id']]}" if counts else ""
        note = "; ".join(x for x in (r.get("note", ""), r.get("conflict", "")) if x)
        out.append(f"| `{_e(r['ru']) or '—'}`{c} | **{r['ar']}** | {r['status']} | {_e(note)} |")
    return "\n".join(out)


def scan(path, overlay, lang):
    rows = load_glossary(overlay)
    src = read_text(path)
    counts = {}
    if lang == "en":
        low = src.lower()
        for r in rows:
            phrases = [p.strip() for p in re.split(r"[,/;()]", r["en"]) if len(p.strip()) > 3]
            n = sum(len(re.findall(r"\b" + re.escape(p.lower()) + r"(?:s|es)?\b", low)) for p in phrases)
            if n:
                counts[r["id"]] = n
    else:
        low = norm_ru(src)
        for r in rows:
            if r["_ru"] is not None:
                n = len(r["_ru"].findall(low))
                if n:
                    counts[r["id"]] = n
    hit = [r for r in rows if r["id"] in counts]
    hit.sort(key=lambda r: (STATUS_RANK.get(r["status"], 9), -counts[r["id"]]))
    print(f"glossary slice for {Path(path).name}: {len(hit)} terms (locked/attested first)")
    print(table(hit, counts))
    inferred = [r["ar"] for r in hit if r["status"] == "inferred"]
    if inferred:
        print("\nINFERRED terms present (log each use in uncertain.md):", "، ".join(inferred))


def unknown(path, overlay, top):
    rows = load_glossary(overlay)
    low = norm_ru(read_text(path))
    for r in rows:  # blank out everything the glossary already covers (also multi-word terms)
        if r["_ru"] is not None:
            low = re.sub("(?:" + r["_ru"].pattern + r")[а-я]*", " ", low)
    words = re.findall(r"[а-я]{5,}", low)
    cnt = Counter(w for w in words if w not in RU_STOP)
    res = []
    for w, n in cnt.most_common():
        res.append((w, n))
        if len(res) >= top:
            break
    print(f"top {len(res)} frequent words not in the glossary (decide recurring Lazarev terms before translating):")
    print(", ".join(f"{w}×{n}" for w, n in res))


def topic(name):
    rows = [r for r in load_glossary() if name in r["topics"].split(",")]
    print(f"## {TOPIC_NAMES.get(name, name)} ({len(rows)})")
    print(table(rows))


def term(word):
    w = word.lower()
    rows = [r for r in load_glossary()
            if w in r["ru"].lower() or w in r["en"].lower() or norm_ar(word) in norm_ar(r["ar"])
            or (r["_ru"] is not None and r["_ru"].search(norm_ru(word)))]
    for r in rows:
        print(f"[{r['id']}] ru:{r['ru']} | en:{r['en']} | ar:{r['ar']} | status:{r['status']} | "
              f"wrong:{r['wrong'] or '-'} | {r['evidence']} | {r['note']}")
    if not rows:
        print("no entry; if this is a recurring Lazarev term, decide it from Sablabal's corpus and add it to book-glossary.tsv")


def render_topics(out):
    rows = load_glossary()
    out = Path(out)
    for key, name in TOPIC_NAMES.items():
        sel = [r for r in rows if key in r["topics"].split(",")]
        body = [f"# {name}", "",
                "> Generated from `references/glossary.tsv` by `scripts/glossary.py --render-topics`. "
                "Do not edit by hand; edit the TSV.", "",
                "| الروسية | English | العربية (سبلبل) | الحالة | تجنّب | ملاحظة |", "|---|---|---|---|---|---|"]
        for r in sel:
            body.append(f"| `{_e(r['ru']) or '—'}` | {_e(r['en'])} | **{r['ar']}** | {r['status']} | "
                        f"{_e(r['wrong'])} | {_e(r['note'])} |")
        write_text(out / f"{key}.md", "\n".join(body) + "\n")
    print(f"ok: wrote {len(TOPIC_NAMES)} topic views to {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan")
    ap.add_argument("--unknown")
    ap.add_argument("--topic")
    ap.add_argument("--term")
    ap.add_argument("--render-topics")
    ap.add_argument("--overlay")
    ap.add_argument("--lang", default="ru", choices=["ru", "en"])
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    if a.scan:
        scan(a.scan, a.overlay, a.lang)
    elif a.unknown:
        unknown(a.unknown, a.overlay, a.top)
    elif a.topic:
        topic(a.topic)
    elif a.term:
        term(a.term)
    elif a.render_topics:
        render_topics(a.render_topics)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
