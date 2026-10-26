"""Export an assembled Arabic Markdown file to the approved reading deliverables: HTML + PDF.

Usage:
  python export_reading.py ASSEMBLED.md --out-dir final [--name "<Arabic stem>"]
                           [--doubts uncertain.md] [--meta meta.json] [--index index.json]
                           [--browser PATH] [--no-pdf] [--no-paginate]

Steps (no third-party Python packages; uses the installed Chrome or Edge):
  1. Markdown -> semantic RTL HTML (headings, paragraphs, bold/italic, links, quotes, lists,
     tables, footnotes; front matter becomes a visible header). Alignment markers are removed.
  2. Embeds assets/reading.css with the Readex Pro fonts as data URLs (standalone file).
  3. Paginates into A4 sheets with assets/paginate-reading.js in headless Chrome/Edge at a
     desktop viewport; the paginated DOM is saved, so the HTML needs no script to display.
  4. Prints the same HTML to PDF (A4, no browser headers), then checks: PDF pages == sheets,
     every page is A4, the paginator preserved the text.
  5. Optional: a separate continuous HTML for the doubts file; article index -> final paths.
Prints one status line per output. Exit 1 if a check fails (the HTML is kept and reported).
"""
from __future__ import annotations

import argparse
import base64
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from _common import SKILL_DIR, die, read_json, read_text, write_json, write_text

ASSETS = SKILL_DIR / "assets"
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
MARK = re.compile(r"<!--.*?-->", re.S)


# ============================================================== Markdown -> HTML
INFERRED = re.compile(r"\{\{(.+?)\}\}", re.S)
LEGEND = ('<p class="inferred-note"><span class="inferred">النص الملوّن بهذا اللون</span> '
          'مستنتج من السياق: الكلام في التسجيل غير واضح هناك، والأصل المسموع مدرج في ملف مواضع الشك.</p>')


def inline(text: str, notes: dict[str, int]) -> str:
    # garbled captions never reach the reader: an old «[غير واضح: …]» shows as a coloured «…»
    text = re.sub(r"\[غير واضح(?::[^\]]*)?\]", "{{…}}", text)
    t = html.escape(text, quote=False)
    t = INFERRED.sub(r'<span class="inferred">\1</span>', t)  # {{…}} = completed from context
    # isolate Russian runs so the surrounding brackets/punctuation keep their RTL order
    t = re.sub(r"[А-Яа-яЁё]+(?:[ ,\-]+[А-Яа-яЁё]+)*", r'<bdi dir="ltr">\g<0></bdi>', t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\[\^([^\]]+)\]", lambda m: _fnref(m.group(1), notes), t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t, flags=re.S)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t, flags=re.S)
    t = re.sub(r" {2,}\n", "<br>\n", t)
    return t.replace("\n", " ")


def _fnref(fid: str, notes: dict[str, int]) -> str:
    n = notes.setdefault(fid, len(notes) + 1)
    return f'<sup class="fnref"><a href="#fn-{html.escape(fid)}" id="ref-{html.escape(fid)}">{n}</a></sup>'


def front_matter(md: str) -> tuple[dict, str]:
    m = re.match(r"\ufeff?---\n(.*?)\n---\n", md, re.S)
    if not m:
        return {}, md
    meta = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep:
            meta[k.strip()] = v.strip()
    return meta, md[m.end():]


def md_to_html(md: str) -> tuple[str, str]:
    """Return (title, body_html)."""
    meta, md = front_matter(md.replace("\r\n", "\n"))
    md = MARK.sub("", md)
    blocks = [b.strip("\n") for b in re.split(r"\n\s*\n", md) if b.strip()]
    notes: dict[str, int] = {}
    defs: dict[str, str] = {}
    out: list[str] = []
    title = meta.get("العنوان", "")
    if meta and blocks and blocks[0].startswith("# "):
        # the work file already opens with the title: keep it first, details below it
        title = re.sub(r"[*`]", "", blocks[0][2:].strip()) or title
        out.append(f"<h1>{inline(blocks.pop(0)[2:].strip(), notes)}</h1>")
    elif meta:
        out.append(f"<h1>{inline(title, notes)}</h1>")
    if meta:
        rows = []
        for key in ("المؤلف", "العنوان الأصلي", "التاريخ", "المدة", "المواضيع"):
            if meta.get(key):
                rows.append(f"{key}: {inline(meta[key], notes)}")
        if meta.get("المصدر"):
            u = html.escape(meta["المصدر"])
            rows.append(f'المصدر: <a href="{u}" dir="ltr"><bdi>{u}</bdi></a>')
        if rows:
            out.append('<p class="metadata">' + "<br>".join(rows) + "</p>")
    for b in blocks:
        first = b.lstrip()
        if re.fullmatch(r"(\*\s*){3,}|(-\s*){3,}", first):
            out.append("<hr>")
        elif m := re.match(r"(#{1,6})\s+([^\n]*)\n?(.*)", first, re.S):
            # a heading is only its first line; anything after it is a normal paragraph
            lvl = len(m.group(1))
            text = re.sub(r"\s*`\[([\d:]+)\]`\s*$", "", m.group(2).strip())
            stamp = re.search(r"`\[([\d:]+)\]`\s*$", m.group(2))
            if lvl == 1 and not title:
                title = re.sub(r"[*`]", "", text)
            ts = f' <span class="timestamp">[{stamp.group(1)}]</span>' if stamp else ""
            out.append(f"<h{lvl}>{inline(text, notes)}{ts}</h{lvl}>")
            if m.group(3).strip():
                rest = m.group(3).strip()
                out.append(f'<p{_pclass(rest)}>{inline(rest, notes)}</p>')
        elif first.startswith("[^") and re.match(r"\[\^([^\]]+)\]:", first):
            for d in re.findall(r"\[\^([^\]]+)\]:\s*(.*?)(?=\n\[\^|\Z)", b, re.S):
                defs[d[0]] = d[1].strip()
        elif first.startswith(">"):
            inner = "\n".join(re.sub(r"^\s*>\s?", "", ln) for ln in b.splitlines())
            paras = [p for p in re.split(r"\n\s*\n", inner) if p.strip()]
            out.append("<blockquote>" + "".join(f"<p>{inline(p, notes)}</p>" for p in paras) + "</blockquote>")
        elif first.startswith("|") and "\n" in b:
            out.append(table(b, notes))
        elif re.match(r"([-*+]|\d+[.)])\s", first) and not first.startswith(("**", "– ")):
            ordered = bool(re.match(r"\d", first))
            items = re.split(r"\n(?=\s*(?:[-*+]|\d+[.)])\s)", b)
            lis = "".join(f"<li>{inline(re.sub(r'^\s*(?:[-*+]|\d+[.)])\s+', '', it), notes)}</li>" for it in items)
            out.append(f"<{'ol' if ordered else 'ul'}>{lis}</{'ol' if ordered else 'ul'}>")
        else:
            out.append(f'<p{_pclass(first)}>{inline(b, notes)}</p>')
    if defs or notes:
        items = []
        for fid, n in sorted(notes.items(), key=lambda kv: kv[1]):
            items.append(f'<li id="fn-{html.escape(fid)}">{inline(defs.get(fid, ""), {})} '
                         f'<a href="#ref-{html.escape(fid)}">↩</a></li>')
        out.append('<hr class="footnotes-sep"><ol class="footnotes">' + "".join(items) + "</ol>")
    if any('class="inferred"' in o for o in out):  # explain the colour once, under the source details
        at = next((i + 1 for i, o in enumerate(out) if o == "<hr>"), 1 if out and out[0].startswith("<h1") else 0)
        out.insert(at, LEGEND)
    return title, "\n".join(out)


def _pclass(text: str) -> str:
    t = text.strip()
    if t.startswith(("العنوان الأصلي:", "التاريخ:", "المدة:", "المصدر:", "[المصدر]")):
        return ' class="metadata"'
    if t.startswith(("– ", "— ")):
        return ' class="dialogue"'
    if re.fullmatch(r"\[[^\]]{1,40}\]", t):
        return ' class="cue"'
    if t.startswith("**") and t.endswith("**") and len(t) < 400 and ("؟" in t or "?" in t):
        return ' class="question"'
    return ""


def table(block: str, notes) -> str:
    rows = [r.strip().strip("|").split("|") for r in block.splitlines() if r.strip().startswith("|")]
    rows = [[c.strip() for c in r] for r in rows]
    if len(rows) > 1 and all(re.fullmatch(r":?-{2,}:?", c) for c in rows[1]):
        head, body = rows[0], rows[2:]
    else:
        head, body = None, rows
    h = "<table>"
    if head:
        h += "<thead><tr>" + "".join(f"<th>{inline(c, notes)}</th>" for c in head) + "</tr></thead>"
    h += "<tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c, notes)}</td>" for c in r) + "</tr>" for r in body)
    return h + "</tbody></table>"


# ============================================================== page assembly
def css_with_fonts() -> str:
    css = read_text(ASSETS / "reading.css")

    def embed(m):
        f = ASSETS / m.group(1)
        data = base64.b64encode(f.read_bytes()).decode()
        return f'url("data:font/ttf;base64,{data}")'

    return re.sub(r'url\("(fonts/[^"]+)"\)', embed, css)


def page(title: str, body: str, css: str, extra_head: str = "", body_class: str = "") -> str:
    cls = f' class="{body_class}"' if body_class else ""
    return (f'<!doctype html>\n<html lang="ar" dir="rtl">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{html.escape(title)}</title>\n<style>\n{css}\n</style>\n{extra_head}</head>\n"
            f"<body{cls}>\n<main>\n{body}\n</main>\n</body>\n</html>\n")


def find_browser(explicit: str | None) -> str:
    for c in ([explicit] if explicit else []) + BROWSERS + [shutil.which("chrome") or "", shutil.which("msedge") or ""]:
        if c and Path(c).exists():
            return c
    die("no Chrome/Edge found for pagination and PDF (pass --browser PATH, or use --no-pdf --no-paginate)")


def run_browser(browser: str, args: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    profile = tempfile.mkdtemp(prefix="lzr-browser-")
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           "--allow-file-access-from-files", f"--user-data-dir={profile}", *args]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout)
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def paginate(browser: str, unpaginated: str, workdir: Path) -> str:
    js = read_text(ASSETS / "paginate-reading.js")
    boot = ("<script>" + js + "\nwindow.addEventListener('load', async () => {"
            "try { const r = await window.paginateReading();"
            " document.body.setAttribute('data-paginate', 'ok:' + r.pages); }"
            " catch (e) { document.body.setAttribute('data-paginate', 'error:' + e.message); } });</script>\n")
    tmp = workdir / "_paginate.html"
    tmp.write_text(unpaginated.replace("</head>", boot + "</head>"), encoding="utf-8")
    res = run_browser(browser, ["--window-size=1400,2000", "--virtual-time-budget=120000",
                                "--run-all-compositor-stages-before-draw", "--dump-dom", tmp.resolve().as_uri()])
    dom = res.stdout.decode("utf-8", errors="replace")
    tmp.unlink(missing_ok=True)
    m = re.search(r'data-paginate="([^"]*)"', dom)
    if not m:
        die(f"pagination did not finish (browser exit {res.returncode}): {res.stderr.decode(errors='replace')[-400:]}")
    if not m.group(1).startswith("ok:"):
        die(f"pagination failed: {m.group(1)}")
    dom = re.sub(r"<script>.*?</script>\s*", "", dom, flags=re.S)
    dom = dom.replace("</style>", "\n@page { size: A4; margin: 0; }\n</style>", 1)
    if not dom.lstrip().lower().startswith("<!doctype"):
        dom = "<!doctype html>\n" + dom
    return dom


def print_pdf(browser: str, html_path: Path, pdf_path: Path) -> None:
    tmp_pdf = (html_path.parent / "_print.pdf").resolve()
    res = run_browser(browser, ["--no-pdf-header-footer", "--print-to-pdf-no-header",
                                "--virtual-time-budget=20000", f"--print-to-pdf={tmp_pdf}",
                                html_path.resolve().as_uri()])
    if not tmp_pdf.exists():
        die(f"PDF not produced (browser exit {res.returncode}): {res.stderr.decode(errors='replace')[-400:]}")
    shutil.move(str(tmp_pdf), pdf_path)


def check_pdf(pdf: Path, sheets: int) -> list[str]:
    problems = []
    try:
        from pypdf import PdfReader
    except ImportError:
        return ["pypdf missing: PDF page count/size not verified"]
    r = PdfReader(str(pdf))
    if sheets and len(r.pages) != sheets:
        problems.append(f"PDF has {len(r.pages)} pages but HTML has {sheets} A4 sheets")
    for i, pg in enumerate(r.pages, 1):
        w, h = float(pg.mediabox.width), float(pg.mediabox.height)
        if abs(w - 595.3) > 3 or abs(h - 841.9) > 3:
            problems.append(f"page {i} is {w:.0f}×{h:.0f} pt, not A4")
            break
    sample = (r.pages[0].extract_text() or "") if r.pages else ""
    if not re.search(r"[\u0600-\u06FF]", sample):
        problems.append("no selectable Arabic text on page 1")
    return problems


# ============================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("assembled")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--name", help="Arabic filename stem (default: the assembled file's stem)")
    ap.add_argument("--doubts")
    ap.add_argument("--meta")
    ap.add_argument("--index")
    ap.add_argument("--browser")
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--no-paginate", action="store_true")
    a = ap.parse_args()

    src = Path(a.assembled)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = a.name or src.stem
    css = css_with_fonts()
    title, body = md_to_html(read_text(src))
    unpaginated = page(title or stem, body, css)
    html_path = out / f"{stem}.html"
    pdf_path = out / f"{stem}.pdf"
    problems: list[str] = []
    sheets = 0
    browser = None if (a.no_pdf and a.no_paginate) else find_browser(a.browser)
    if a.no_paginate:
        write_text(html_path, unpaginated)
    else:
        final = paginate(browser, unpaginated, out)
        sheets = len(re.findall(r'class="a4-page"', final))
        write_text(html_path, final)
    print(f"ok: HTML {sheets or 'continuous'} {'A4 sheets' if sheets else ''} -> {html_path}")
    if not a.no_pdf:
        print_pdf(browser, html_path, pdf_path)
        problems += check_pdf(pdf_path, sheets)
        print(f"{'ok' if not problems else 'WARN'}: PDF -> {pdf_path}")
    if a.doubts and Path(a.doubts).exists() and len(read_text(a.doubts).splitlines()) > 4:
        dt, db = md_to_html(read_text(a.doubts))
        d_path = out / f"{stem} – مواضع الشك.html"
        write_text(d_path, page(f"{stem} – مواضع الشك", db, css))
        print(f"ok: doubts HTML -> {d_path}")
    meta = read_json(a.meta, default={}) if a.meta else {}
    if a.index and meta.get("key"):
        idx = read_json(a.index, default={"items": []})
        for it in idx["items"]:
            if it.get("key") == meta["key"]:
                it["file_ar"] = str(html_path)
                if not a.no_pdf:
                    it["file_pdf"] = str(pdf_path)
        write_json(a.index, idx)
        print(f"ok: index updated -> {a.index}")
    for p in problems:
        print("  PROBLEM " + p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
