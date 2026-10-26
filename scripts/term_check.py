"""Source-aware terminology check of an Arabic translation against Sablabal's glossary.

Usage:
  python term_check.py SOURCE.md TARGET.md [--overlay book-glossary.tsv] [--lang ru|en] [--report OUT.json]

Both files must carry the same <!-- p0001 --> markers (see split_chunks.py).
For every aligned block:
  * a glossary term found in the source block whose Sablabal rendering is absent in the
    target block                         -> "missing"  (warn: check, it may be rephrased)
  * a known wrong rendering in the target block, when the source block contains that
    concept (e.g. «الروح» for душа without дух) -> "wrong"  (warn or error per glossary)
  * error-level wrong forms (اللاوعي، العقل الباطن، البنى، التضرع، البزنس) -> error anywhere
Warnings inside "> " quotation blocks (reader letters, Bible) are downgraded to info.
This is a review aid, not a verdict. Exit 1 only when there are errors.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from _common import load_glossary, norm_ar, norm_ru, read_text, split_marked, write_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("target")
    ap.add_argument("--overlay")
    ap.add_argument("--lang", default="ru", choices=["ru", "en"])
    ap.add_argument("--report")
    a = ap.parse_args()

    rows = load_glossary(a.overlay)
    src = dict(split_marked(read_text(a.source)))
    dst = dict(split_marked(read_text(a.target)))
    findings = []
    for pid, s_body in src.items():
        t_body = dst.get(pid)
        if t_body is None:
            continue  # align_check reports missing blocks
        s_low = norm_ru(s_body) if a.lang == "ru" else s_body.lower()
        t_norm = norm_ar(t_body)
        quoted = t_body.lstrip().startswith(">")
        for r in rows:
            in_src = _in_source(r, s_low, a.lang)
            wrong_hit = r["_wrong"].search(t_norm) if r["_wrong"] is not None else None
            if (in_src and r["_accept"] is not None and not r["_accept"].search(t_norm)
                    and not (wrong_hit and (r["wrong_level"] == "error"))):
                findings.append(_f(pid, "missing", "info" if quoted else "warn", r,
                                   f"source has «{in_src}», expected «{r['ar']}»"))
            if r["_wrong"] is not None:
                m = r["_wrong"].search(t_norm)
                if not m:
                    continue
                legit = r["_unless"] is not None and a.lang == "ru" and r["_unless"].search(s_low)
                if legit:
                    continue
                level = r["wrong_level"] or "warn"
                if level == "error":
                    findings.append(_f(pid, "wrong", "error", r, f"«{m.group(0).strip()}» → use «{r['ar']}»"))
                elif in_src or not r["ru"]:
                    # projection guards (no ru) stay warnings even inside quotations
                    msg = (f"«{m.group(0).strip()}» for «{in_src}» → Sablabal: «{r['ar']}»" if r["ru"] else
                           f"«{m.group(0).strip()}» is not in the source — do not import this notion ({r['note']})")
                    findings.append(_f(pid, "wrong", "info" if (quoted and r["ru"]) else "warn", r, msg))
    errors = [f for f in findings if f["level"] == "error"]
    warns = [f for f in findings if f["level"] == "warn"]
    report = {"source": a.source, "target": a.target, "errors": len(errors), "warnings": len(warns),
              "findings": findings}
    if a.report:
        write_json(a.report, report)
    print(f"{'FAIL' if errors else 'ok'}: {len(errors)} errors, {len(warns)} warnings, "
          f"{len(findings) - len(errors) - len(warns)} info ({Path(a.target).name})")
    for f in errors + warns[:40]:
        print(f"  {f['level']:5} {f['id']} [{f['term']}] {f['msg']}")
    if len(warns) > 40:
        print(f"  … {len(warns) - 40} more warnings in the report")
    raise SystemExit(1 if errors else 0)


def _in_source(r, s_low, lang):
    if lang == "ru":
        if r["_ru"] is None:
            return ""
        m = r["_ru"].search(s_low)
        return m.group(0) if m else ""
    for p in re.split(r"[,/;()]", r["en"]):
        p = p.strip().lower()
        if len(p) > 3 and re.search(r"\b" + re.escape(p) + r"(?:s|es)?\b", s_low):
            return p
    return ""


def _f(pid, kind, level, r, msg):
    return {"id": pid, "kind": kind, "level": level, "term": r["id"], "msg": msg}


if __name__ == "__main__":
    main()
