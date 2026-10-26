"""Assemble final Arabic deliverables (Arabic file names) from checked working files.

Usage:
  python assemble_book.py book PROJECT_DIR [--allow-unchecked]
      -> PROJECT_DIR/work/assembled/<Arabic title>.md (internal; then export HTML/PDF) : title block, table of contents, all chunks in order
  python assemble_book.py single WORK.md --title-ar "..." --out-dir DIR [--meta meta.json]
                          [--topics "المال، العائلة"] [--kind article|lecture] [--index INDEX.json]
      -> DIR/<date> <Arabic title>.md with a front-matter header; lectures keep [hh:mm:ss] next to headings;
         articles are recorded in the dedup index.
Markers (<!-- p0001 -->, <!-- s0001 … -->) are removed only here, after all checks passed.
Also scans the whole text for inconsistent variants (two spellings of a name or term).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from _common import arabic_filename, die, norm_ar, read_json, read_text, write_json, write_text

AUTHOR_AR = "سيرغيي نيكولايفيتش لازاريف"
VARIANTS = [  # (preferred, regex of competing forms) — checked across the whole deliverable
    ("سيرغيي", r"سيرغي(?!ي)|سرغيي|سيرجي|سيرغاي"),
    ("نيكولايفيتش", r"نيكولايفتش|نيكولاييفيتش|نيقولايفيتش"),
    ("البنيات", r"(^|\s)[وفبلك]?(ال)?بنى(\s|$)"),
    ("الوعي الباطن", r"اللاوعي|العقل الباطن"),
    ("التكبّر", r"الغرور"),
    ("العدائية", r"العدوانية"),
    ("(no translator name in deliverables)", r"سبلبل|كلمة المترجم"),
]
SEG = re.compile(r"<!--\s*s\d{4,6}\s+([\d:.,]+)-[\d:.,]+\s*-->\s*")
MARK = re.compile(r"<!--\s*[ps]\d{4,6}[^>]*-->\s*")


PARA_START = ("#", "**", ">", "– ", "— ", "[", "|", "***", "- ", "¶")


def lecture_layout(text: str) -> str:
    """Timed segments are alignment units, not paragraphs.

    - Text inside one segment keeps its own blank-line paragraph breaks (never merged).
    - A segment continues the previous paragraph unless it opens with «¶ » (new paragraph),
      a heading, a speaker label (**…:**), a quotation, a dialogue dash or a cue.
    - A heading is always its own line (never joined to the prose after it) and carries the
      segment's start time `[hh:mm:ss]`.
    """
    parts = SEG.split(text)
    paras: list[str] = [p.strip() for p in re.split(r"\n\s*\n", parts[0]) if p.strip()]
    open_para = False
    for i in range(1, len(parts), 2):
        start = parts[i].split(".")[0]
        blocks = [b.strip() for b in re.split(r"\n\s*\n", parts[i + 1]) if b.strip()]
        for j, b in enumerate(blocks):
            lines = b.split("\n")
            if lines[0].startswith("#"):          # heading line → own block, with timestamp
                paras.append(f"{lines[0].rstrip()} `[{start}]`" if j == 0 else lines[0])
                b = "\n".join(lines[1:]).strip()
                open_para = False
                if not b:
                    continue
            new = b.startswith("¶")
            b = b.lstrip("¶").strip()
            if j == 0 and open_para and not new and not b.startswith(PARA_START):
                paras[-1] = paras[-1].rstrip() + " " + b
            else:
                paras.append(b)
            open_para = not b.startswith(("#", "|", "***", ">"))
    return "\n\n".join(paras)


def strip_markers(text: str, keep_time: bool) -> str:
    if keep_time and SEG.search(text):
        text = lecture_layout(text)
    text = text.replace("¶ ", "").replace("¶", "")
    text = MARK.sub("", text)
    text = re.sub(r"<!--\s*chunk[^>]*-->\s*", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def articles_index(start: Path) -> Path:
    """The one dedup index: ترجمات/مقالات/index.json (or legacy translations/articles/), wherever the post folder is.

    Post folders live directly under the articles root (…/articles/<date>-<slug>/), so the
    index sits next to them — never inside a post's work/ or النهائي/ folder.
    """
    p = start.resolve()
    for parent in [p] + list(p.parents):
        if parent.name in ("مقالات", "articles"):
            return parent / "index.json"
    post = p.parent if p.is_file() else p
    return post.parent / "index.json"


def toc(text: str) -> str:
    items = []
    for m in re.finditer(r"^(#{1,2}) (.+)$", text, flags=re.M):
        indent = "  " if len(m.group(1)) == 2 else ""
        items.append(f"{indent}- {m.group(2).strip()}")
    return "## المحتويات\n\n" + "\n".join(items) + "\n" if items else ""


def variant_scan(text: str) -> list[str]:
    n = norm_ar(text)
    out = []
    for pref, rx in VARIANTS:
        hits = re.findall(rx, n, flags=re.M)
        if hits:
            out.append(f"{len(hits)}× competing form instead of «{pref}» ({rx})")
    return out


def cmd_book(a):
    pdir = Path(a.project)
    data = read_json(pdir / "project.json")
    if not data:
        die("no project.json")
    pending = [c["id"] for c in data["chunks"] if c["status"] != "checked"]
    if pending and not a.allow_unchecked:
        die(f"{len(pending)} chunks not checked yet: {', '.join(pending[:10])}")
    parts = []
    for c in data["chunks"]:
        p = pdir / c["dst"]
        if not p.exists():
            die(f"missing {p}")
        parts.append(read_text(p))
    body = strip_markers("\n\n".join(parts), keep_time=False)
    title = data.get("title_ar") or data.get("title_ru") or data["slug"]
    head = f"# {title}\n\n**{AUTHOR_AR}**\n\n*{data.get('title_ru', '')}*\n\n"
    final = head + toc(body) + "\n" + body
    assembled_dir = pdir / "work" / "assembled"
    out = assembled_dir / arabic_filename(title)
    write_text(out, final)
    unc = pdir / "uncertain.md"
    if unc.exists() and len(read_text(unc).splitlines()) > 4:
        write_text(assembled_dir / arabic_filename(title, suffix=" – مواضع الشك"), read_text(unc))
    warn = variant_scan(final)
    print(f"ok: {len(data['chunks'])} chunks, {len(final.split())} words -> {out}")
    for w in warn:
        print("  WARN " + w)


def cmd_single(a):
    meta = read_json(a.meta, default={}) if a.meta else {}
    kind = a.kind or meta.get("kind", "article")
    body = strip_markers(read_text(a.work), keep_time=(kind == "lecture"))
    date = meta.get("date", "")
    fm = ["---", f"العنوان: {a.title_ar}"]
    if meta.get("title_ru"):
        fm.append(f"العنوان الأصلي: {meta['title_ru']}")
    author = a.author if a.author is not None else AUTHOR_AR
    if author:
        fm.append(f"المؤلف: {author}")
    if meta.get("url"):
        fm.append(f"المصدر: {meta['url']}")
    if date:
        fm.append(f"التاريخ: {date}")
    if meta.get("duration"):
        fm.append(f"المدة: {meta['duration']}")
    if a.topics:
        fm.append(f"المواضيع: {a.topics}")
    fm.append("---")
    if kind == "lecture":
        # A lecture is a reading document: visible title and compact source details.
        # Remove only an identical leading title already present in the work file.
        body = re.sub(r"\A\ufeff?# " + re.escape(a.title_ar) + r"[ \t]*\n+", "", body)
        header = [f"# {a.title_ar}"]
        if author:
            header.append(f"**{author}**")
        details = []
        if meta.get("title_ru"):
            details.append(f"العنوان الأصلي: {meta['title_ru']}")
        if date:
            details.append(f"التاريخ: {date}")
        if meta.get("duration"):
            details.append(f"المدة: {meta['duration']}")
        if meta.get("url"):
            details.append(f"[المصدر]({meta['url']})")
        if details:
            header.append("  \n".join(details))
        final = "\n\n".join(header) + "\n\n***\n\n" + body
    else:
        final = "\n".join(fm) + "\n\n" + body
    name = arabic_filename(f"{date} {a.title_ar}".strip())
    out = Path(a.out_dir) / name
    write_text(out, final)
    if kind == "article" and meta.get("key"):
        idx_path = Path(a.index) if a.index else articles_index(Path(a.meta) if a.meta else Path(a.work))
        idx = read_json(idx_path, default={"items": []})
        idx["items"] = [it for it in idx["items"] if it["key"] != meta["key"]]
        idx["items"].append({"key": meta["key"], "date": date, "title_ru": meta.get("title_ru", ""),
                             "title_ar": a.title_ar, "topics": a.topics or "", "file_ar": str(out)})
        write_json(idx_path, idx)
    parts = [read_text(p).strip() for p in (a.doubts or []) if Path(p).exists() and read_text(p).strip()]
    if parts:  # uncertain.md + the {{…}} list from align_check --inferred, one file for the reader
        d_out = Path(a.out_dir) / arabic_filename(f"{date} {a.title_ar}".strip(), suffix=" – مواضع الشك")
        write_text(d_out, "\n\n".join(parts) + "\n")
        print(f"   doubts -> {d_out}")
    print(f"ok: {len(final.split())} words -> {out}")
    for w in variant_scan(final):
        print("  WARN " + w)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("book")
    p.add_argument("project")
    p.add_argument("--allow-unchecked", action="store_true")
    p = sub.add_parser("single")
    p.add_argument("work")
    p.add_argument("--title-ar", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--meta")
    p.add_argument("--topics")
    p.add_argument("--kind", choices=["article", "lecture"])
    p.add_argument("--index")
    p.add_argument("--author", help='header author line; default Lazarev, "" to omit')
    p.add_argument("--doubts", nargs="+", help="uncertain.md (and work/inferred.md) joined next to the deliverable")
    a = ap.parse_args()
    cmd_book(a) if a.cmd == "book" else cmd_single(a)


if __name__ == "__main__":
    main()
