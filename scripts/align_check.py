"""Completeness check: is every source block present, in order, and plausibly complete?

Usage:
  python align_check.py SOURCE.md TARGET.md [--report OUT.json]

Errors (exit 1): a block ID missing, duplicated, extra or out of order; an empty
target block; a footnote marker [^x] lost.
Warnings: length ratio far from the chunk's median (possible omission or addition),
numbers/dates missing, a question in the source with no question mark in the target,
heading/quotation shape changed, Cyrillic left untranslated, a garbled source spot
([неразборчиво: …]) with no {{…}} completion in its target block.
--inferred OUT.md writes the list of context completions (heard Russian -> Arabic) for the
doubts file.
It proves accounting, not meaning: follow up warnings by re-reading the source block.
"""
from __future__ import annotations

import argparse
import re
import statistics

from _common import read_text, split_marked, write_json, write_text

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
CYR_WORD = re.compile(r"[А-Яа-яЁё]{3,}")
GARBLED = re.compile(r"\[неразборчиво:\s*([^\]]*)\]")
INFERRED = re.compile(r"\{\{(.+?)\}\}", re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("target")
    ap.add_argument("--report")
    ap.add_argument("--inferred", help="write the table of {{…}} completions here")
    ap.add_argument("--low", type=float, default=0.55)
    ap.add_argument("--high", type=float, default=1.8)
    a = ap.parse_args()

    src = split_marked(read_text(a.source))
    dst = split_marked(read_text(a.target))
    s_ids = [i for i, _ in src]
    t_ids = [i for i, _ in dst]
    findings = []

    def add(level, pid, msg):
        findings.append({"level": level, "id": pid, "msg": msg})

    seen = set()
    for i in t_ids:
        if i in seen:
            add("error", i, "duplicated block ID in target")
        seen.add(i)
    for i in s_ids:
        if i not in seen:
            add("error", i, "block missing in target (omission)")
    for i in seen - set(s_ids):
        add("error", i, "block ID not in source (addition or typo)")
    common = [i for i in t_ids if i in set(s_ids)]
    if common != [i for i in s_ids if i in set(common)]:
        add("error", "-", "block order differs from source")

    tmap = dict(dst)
    inferred_rows = []
    ratios = {}
    for pid, s in src:
        t = tmap.get(pid)
        if t is None:
            continue
        if not t.strip():
            add("error", pid, "empty target block")
            continue
        s_plain, t_plain = _plain(s), _plain(t)
        if len(s_plain) >= 80:
            ratios[pid] = len(t_plain) / max(1, len(s_plain))
        for n in set(re.findall(r"\d+", s)):
            if n not in t.translate(AR_DIGITS):
                add("warn", pid, f"number {n} not found in target")
        for fn in re.findall(r"\[\^[^\]]+\]", s):
            if fn not in t:
                add("error", pid, f"footnote marker {fn} lost")
        if "?" in s and not re.search(r"[؟?]", t):
            add("warn", pid, "source asks a question, target has no question mark")
        if s.lstrip().startswith("#") != t.lstrip().startswith("#"):
            add("warn", pid, "heading shape differs")
        if s.lstrip().startswith(">") != t.lstrip().startswith(">"):
            add("warn", pid, "quotation shape differs")
        garbled = GARBLED.findall(s)
        filled = INFERRED.findall(t)
        if len(filled) < len(garbled):
            add("warn", pid, f"{len(garbled)} garbled spot(s) in source, {len(filled)} {{{{…}}}} in target")
        if "[غير واضح" in t:
            add("warn", pid, "old [غير واضح] mark: complete from context as {{…}} instead")
        for k, g in enumerate(garbled):
            inferred_rows.append((pid, g.strip(), filled[k].strip() if k < len(filled) else "—"))
        for f in filled[len(garbled):]:
            inferred_rows.append((pid, "—", f.strip()))
        left = CYR_WORD.findall(INFERRED.sub("", t))
        if left:
            add("warn", pid, f"Cyrillic left in target: {' '.join(left[:5])}")
    if len(ratios) >= 4:
        med = statistics.median(ratios.values())
        for pid, r in ratios.items():
            rel = r / med
            if rel < a.low:
                add("warn", pid, f"target much shorter than usual (x{rel:.2f} of median) — possible omission")
            elif rel > a.high:
                add("warn", pid, f"target much longer than usual (x{rel:.2f} of median) — possible addition")
    unclear = len(re.findall(r"\[غير واضح", read_text(a.target)))
    if a.inferred and inferred_rows:
        rows = ["## مواضع مستنتجة من السياق", "",
                "الكلام في هذه المواضع غير واضح في الترجمة النصية الآلية؛ أُكمل من السياق ويظهر في الترجمة بلون مختلف.", "",
                "| المقطع | المسموع في الترجمة النصية | المستنتج من السياق |", "|---|---|---|"]
        rows += [f"| {p} | {g} | {f} |" for p, g, f in inferred_rows]
        write_text(a.inferred, "\n".join(rows) + "\n")
    errors = [f for f in findings if f["level"] == "error"]
    warns = [f for f in findings if f["level"] == "warn"]
    report = {"source_blocks": len(s_ids), "target_blocks": len(t_ids), "errors": len(errors),
              "warnings": len(warns), "unclear_marks": unclear, "inferred": len(inferred_rows), "findings": findings}
    if a.report:
        write_json(a.report, report)
    print(f"{'FAIL' if errors else 'ok'}: {len(s_ids)} source / {len(t_ids)} target blocks, "
          f"{len(errors)} errors, {len(warns)} warnings, {len(inferred_rows)} {{{{…}}}} completed from context"
          + (f", {unclear} old [غير واضح]" if unclear else ""))
    for f in errors + warns[:40]:
        print(f"  {f['level']:5} {f['id']} {f['msg']}")
    raise SystemExit(1 if errors else 0)


def _plain(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text)
    return re.sub(r"[\s#>*_\-–—«»\"()\[\]]+", "", text)


if __name__ == "__main__":
    main()
