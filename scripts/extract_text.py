"""Extract clean source text from a book or document.

Usage:
  python extract_text.py SOURCE --out DIR            # FB2, FB2.ZIP, EPUB, PDF, DOCX, TXT, MD
  python extract_text.py SOURCE.pdf --render-pages DIR [--dpi 170] [--pages 1-20]
                                                      # scanned PDF -> PNG pages (needs PyMuPDF)
  python extract_text.py --from-pages DIR --out DIR   # merge OCR page texts NNN.txt -> full.txt

Writes DIR/full.txt (blocks separated by a blank line; "# " headings, "> " quotations,
footnotes as [^id] with definitions at the end) and DIR/extract-report.json
(language, block counts, quality score, pages that look scanned).
Prints one short status line. Exit 2 when quality is too low to translate from.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from html.parser import HTMLParser
from pathlib import Path

from _common import die, write_json, write_text

CYR = re.compile(r"[А-Яа-яЁё]")
LAT = re.compile(r"[A-Za-z]")
ARB = re.compile(r"[؀-ۿ]")
PRES_FORMS = re.compile(r"[ﭐ-﷿ﹰ-﻿]")


# ======================================================================= FB2
def extract_fb2(data: bytes) -> tuple[list[str], dict]:
    m = re.match(rb'<\?xml[^>]*encoding=["\']([\w-]+)["\']', data[:200])
    enc = m.group(1).decode() if m else None
    if enc is None:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            data = data.decode("cp1251").encode("utf-8")
    root = ET.fromstring(data)
    ns = {"f": root.tag.split("}")[0].strip("{")} if root.tag.startswith("{") else {"f": ""}
    q = (lambda t: f"{{{ns['f']}}}{t}") if ns["f"] else (lambda t: t)
    href_attr = "{http://www.w3.org/1999/xlink}href"

    notes: dict[str, str] = {}
    bodies = root.findall(q("body"))
    for body in bodies:
        if body.get("name") in ("notes", "comments"):
            for sec in body.iter(q("section")):
                nid = sec.get("id")
                if nid:
                    title_ps = {id(p) for t in sec.findall(q("title")) for p in t.iter(q("p"))}
                    txt = " ".join(_fb2_inline(p, q, href_attr) for p in sec.iter(q("p")) if id(p) not in title_ps)
                    notes[nid] = txt.strip()

    blocks: list[str] = []

    def walk(el, depth):
        for ch in el:
            tag = ch.tag.split("}")[-1]
            if tag == "section":
                walk(ch, depth + 1)
            elif tag == "title":
                t = " ".join(_fb2_inline(p, q, href_attr) for p in ch.iter(q("p"))).strip()
                if t:
                    blocks.append("#" * min(depth + 1, 4) + " " + t)
            elif tag == "subtitle":
                blocks.append("#" * min(depth + 2, 5) + " " + _fb2_inline(ch, q, href_attr))
            elif tag in ("epigraph", "cite"):
                for p in ch.iter():
                    ptag = p.tag.split("}")[-1]
                    if ptag in ("p", "v", "text-author"):
                        t = _fb2_inline(p, q, href_attr)
                        if t:
                            blocks.append("> " + t)
            elif tag == "poem":
                lines = [_fb2_inline(v, q, href_attr) for v in ch.iter(q("v"))]
                if lines:
                    blocks.append("\n".join("> " + x for x in lines if x))
            elif tag == "p":
                t = _fb2_inline(ch, q, href_attr)
                if t:
                    blocks.append(t)
            elif tag in ("empty-line", "image", "binary"):
                continue
            else:
                walk(ch, depth)

    for body in bodies:
        if body.get("name") not in ("notes", "comments"):
            walk(body, 0)
    title_el = root.find(f".//{q('book-title')}")
    meta = {"title": title_el.text.strip() if title_el is not None and title_el.text else "",
            "encoding": enc or "detected"}
    return _append_notes(blocks, notes), meta


def _fb2_inline(el, q, href_attr) -> str:
    out = []
    if el.text:
        out.append(el.text)
    for ch in el:
        tag = ch.tag.split("}")[-1]
        if tag == "a" and (ch.get("type") == "note" or (ch.get(href_attr) or "").startswith("#")):
            out.append(f"[^{(ch.get(href_attr) or '#n').lstrip('#')}]")
        else:
            out.append(_fb2_inline(ch, q, href_attr))
        if ch.tail:
            out.append(ch.tail)
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _append_notes(blocks: list[str], notes: dict[str, str]) -> list[str]:
    used = [n for n in notes if f"[^{n}]" in "\n".join(blocks)]
    if used:
        blocks.append("# [notes]")
        for n in used:
            blocks.append(f"[^{n}]: {notes[n]}")
    return blocks


# ======================================================================= EPUB / HTML
class _HtmlBlocks(HTMLParser):
    BLOCK = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote", "div", "td", "dd", "dt"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self.notes: dict[str, str] = {}
        self.buf: list[str] = []
        self.stack: list[str] = []
        self.quote = 0
        self.skip = 0
        self.note_id = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        etype = a.get("epub:type", "") + " " + a.get("role", "")
        if tag in ("script", "style", "nav", "head"):
            self.skip += 1
        if tag == "aside" and ("footnote" in etype or "endnote" in etype or "note" in etype):
            self._flush()
            self.note_id = a.get("id", f"n{len(self.notes) + 1}")
            self.stack.append("aside")
            return
        if tag == "a" and ("noteref" in etype or (a.get("href", "").find("#") >= 0 and a.get("class", "").find("note") >= 0)):
            self.buf.append(f"[^{a.get('href', '#n').split('#')[-1]}]")
            self.skip += 1
            self.stack.append("a-note")
            return
        if tag == "blockquote":
            self.quote += 1
        if tag in self.BLOCK or tag == "br":
            if tag == "br":
                self.buf.append(" ")
            else:
                self._flush()
        self.stack.append(tag)

    def handle_endtag(self, tag):
        top = self.stack.pop() if self.stack else None
        if top == "a-note":
            self.skip -= 1
            return
        if top == "aside" and self.note_id:
            txt = re.sub(r"\s+", " ", "".join(self.buf)).strip()
            self.notes[self.note_id] = txt
            self.buf, self.note_id = [], None
            return
        if tag in ("script", "style", "nav", "head"):
            self.skip = max(0, self.skip - 1)
        if tag in self.BLOCK:
            self._flush(tag)
        if tag == "blockquote":
            self.quote = max(0, self.quote - 1)

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)

    def _flush(self, tag: str | None = None):
        if self.note_id:
            return
        txt = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        if not txt:
            return
        if tag and re.fullmatch(r"h[1-6]", tag):
            txt = "#" * int(tag[1]) + " " + txt
        elif self.quote:
            txt = "> " + txt
        self.blocks.append(txt)


def extract_epub(path: Path) -> tuple[list[str], dict]:
    z = zipfile.ZipFile(path)
    container = ET.fromstring(z.read("META-INF/container.xml"))
    opf_path = next(el.get("full-path") for el in container.iter() if el.tag.endswith("rootfile"))
    opf = ET.fromstring(z.read(opf_path))
    base = str(Path(opf_path).parent).replace("\\", "/")
    base = "" if base == "." else base + "/"
    manifest = {el.get("id"): el.get("href") for el in opf.iter() if el.tag.endswith("item")}
    spine = [el.get("idref") for el in opf.iter() if el.tag.endswith("itemref")]
    title = next((el.text for el in opf.iter() if el.tag.endswith("title") and el.text), "")
    parser = _HtmlBlocks()
    for idref in spine:
        href = manifest.get(idref)
        if not href:
            continue
        try:
            raw = z.read(base + href.split("#")[0])
        except KeyError:
            continue
        parser.feed(raw.decode("utf-8", errors="replace"))
        parser._flush()
    return _append_notes(parser.blocks, parser.notes), {"title": title.strip()}


def extract_docx(path: Path) -> tuple[list[str], dict]:
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    blocks = []
    for p in root.iter(w + "p"):
        txt = "".join(t.text or "" for t in p.iter(w + "t")).strip()
        if not txt:
            continue
        style = p.find(f"{w}pPr/{w}pStyle")
        sval = style.get(w + "val", "") if style is not None else ""
        m = re.search(r"(\d)", sval) if sval.lower().startswith(("heading", "заголовок")) else None
        blocks.append(("#" * int(m.group(1)) + " " if m else "") + txt)
    return blocks, {"title": ""}


# ======================================================================= PDF
def extract_pdf(path: Path) -> tuple[list[str], dict]:
    try:
        from pypdf import PdfReader
    except ImportError:
        die("pypdf is not installed (pip install pypdf)")
    reader = PdfReader(str(path))
    scanned_pages, pages_lines = [], []
    for pno, page in enumerate(reader.pages, 1):
        items: list[tuple[float, float, str]] = []

        def visit(text, cm, tm, font_dict, font_size):
            if text and text.strip():
                x = tm[4] * cm[0] + cm[4]
                y = tm[5] * cm[3] + cm[5]
                items.append((round(y, 1), x, text))

        try:
            page.extract_text(visitor_text=visit)
        except Exception:
            items = []
        if sum(len(t.strip()) for _, _, t in items) < 40:
            scanned_pages.append(pno)
            pages_lines.append([])
            continue
        # lines: group by y (top to bottom); order items left->right, or right->left for Arabic
        items.sort(key=lambda it: -it[0])
        lines: list[list] = []
        for y, x, tx in items:
            if lines and abs(lines[-1][0] - y) < 2.5:
                lines[-1][1].append((x, tx))
            else:
                lines.append([y, [(x, tx)]])
        out = []
        for y, parts in lines:
            joined = "".join(tx for _, tx in parts)
            rtl = len(ARB.findall(joined)) > len(CYR.findall(joined)) + len(LAT.findall(joined))
            parts.sort(key=lambda p: -p[0] if rtl else p[0])
            text = re.sub(r"\s+", " ", "".join(tx for _, tx in parts)).strip()
            if text:
                out.append((y, min(x for x, _ in parts), max(x for x, _ in parts), text, rtl))
        pages_lines.append(out)

    # running headers/footers: the same line (digits ignored) on many pages
    from collections import Counter
    key = lambda s: re.sub(r"\d+", "#", s)[:60]
    freq = Counter(key(ln[3]) for pl in pages_lines for ln in pl[:2] + pl[-2:])
    n_pages = max(1, len(pages_lines) - len(scanned_pages))
    furniture = {k for k, c in freq.items() if c >= max(3, 0.3 * n_pages)}

    blocks: list[str] = []
    page_scores = []
    for pl in pages_lines:
        body = [ln for ln in pl if key(ln[3]) not in furniture and not re.fullmatch(r"\d{1,4}", ln[3])]
        if not body:
            continue
        page_scores.append(_quality("\n".join(ln[3] for ln in body)))
        gaps = [body[i][0] - body[i + 1][0] for i in range(len(body) - 1)]
        step = sorted(gaps)[len(gaps) // 2] if gaps else 12
        left = sorted(ln[1] for ln in body)[len(body) // 4]
        para = ""
        prev_y = None
        for y, x0, _x1, text, rtl in body:
            # item x positions are run starts, so indentation is only reliable for LTR text
            indent = (not rtl) and (x0 - left > 8)
            big_gap = prev_y is not None and prev_y - y > 1.6 * step
            ends_sentence = bool(re.search(r"[.!?…»\"؟:]$", para))
            starts = indent or big_gap or (ends_sentence and text[:1] in "—–-«\"") or re.match(r"#{1,4} ", text)
            if para and starts:
                blocks.append(para)
                para = text
            elif para.endswith("-") and not para.endswith(" -"):
                para = para[:-1] + text
            else:
                para = (para + " " + text).strip()
            prev_y = y
        if para:
            blocks.append(para)
    meta = {"title": (reader.metadata.title if reader.metadata and reader.metadata.title else ""),
            "pages": len(reader.pages), "scanned_pages": scanned_pages,
            "dropped_running_lines": len(furniture),
            "page_quality_min": min(page_scores) if page_scores else 0.0}
    return blocks, meta


def render_pages(path: Path, out: Path, dpi: int, pages: str | None) -> None:
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.24
    except ImportError:
        try:
            import fitz  # older PyMuPDF
        except ImportError:
            die("PyMuPDF is not installed. Ask the user for permission, then: python -m pip install pymupdf", 3)
    doc = fitz.open(str(path))
    sel = _page_range(pages, doc.page_count)
    out.mkdir(parents=True, exist_ok=True)
    for i in sel:
        pix = doc[i - 1].get_pixmap(dpi=dpi)
        pix.save(str(out / f"{i:04d}.png"))
    print(f"rendered {len(sel)} pages to {out} (read each PNG, write the text to {out}/NNNN.txt)")


def _page_range(spec: str | None, n: int) -> list[int]:
    if not spec:
        return list(range(1, n + 1))
    res = []
    for part in spec.split(","):
        a, _, b = part.partition("-")
        res.extend(range(int(a), int(b or a) + 1))
    return [p for p in res if 1 <= p <= n]


def merge_pages(src: Path) -> tuple[list[str], dict]:
    files = sorted(src.glob("[0-9]*.txt"))
    if not files:
        die(f"no NNNN.txt page files in {src}")
    blocks, short = [], []
    lens = [len(f.read_text(encoding="utf-8").strip()) for f in files]
    med = sorted(lens)[len(lens) // 2] if lens else 0
    for f, ln in zip(files, lens):
        if med and ln < 0.35 * med:
            short.append(f.stem)
        txt = f.read_text(encoding="utf-8")
        blocks.extend(b.strip() for b in re.split(r"\n\s*\n", txt) if b.strip())
    return blocks, {"pages": len(files), "suspiciously_short_pages": short}


# ======================================================================= quality
def _quality(text: str) -> float:
    letters = len(re.findall(r"\w", text)) or 1
    pres = len(PRES_FORMS.findall(text)) / letters
    lines = [ln for ln in text.splitlines() if ln.strip()]
    tiny = sum(1 for ln in lines if len(ln.strip()) < 3) / (len(lines) or 1)
    return round(max(0.0, 1.0 - 2 * pres - tiny), 3)


def _language(text: str) -> str:
    c, l, a = len(CYR.findall(text)), len(LAT.findall(text)), len(ARB.findall(text))
    return max((("ru", c), ("en", l), ("ar", a)), key=lambda kv: kv[1])[0]


# ======================================================================= main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--render-pages")
    ap.add_argument("--dpi", type=int, default=170)
    ap.add_argument("--pages")
    ap.add_argument("--from-pages")
    a = ap.parse_args()

    if a.render_pages:
        render_pages(Path(a.source), Path(a.render_pages), a.dpi, a.pages)
        return
    if a.from_pages:
        blocks, meta = merge_pages(Path(a.from_pages))
        meta["format"] = "ocr-pages"
    else:
        if not a.source or not a.out:
            ap.error("SOURCE and --out are required")
        src = Path(a.source)
        if not src.exists():
            die(f"not found: {src}")
        name = src.name.lower()
        if name.endswith(".fb2.zip") or (name.endswith(".zip") and _zip_has(src, ".fb2")):
            z = zipfile.ZipFile(src)
            inner = next(n for n in z.namelist() if n.lower().endswith(".fb2"))
            blocks, meta = extract_fb2(z.read(inner))
            meta["format"] = "fb2.zip"
        elif name.endswith(".fb2"):
            blocks, meta = extract_fb2(src.read_bytes())
            meta["format"] = "fb2"
        elif name.endswith(".epub"):
            blocks, meta = extract_epub(src)
            meta["format"] = "epub"
        elif name.endswith(".pdf"):
            blocks, meta = extract_pdf(src)
            meta["format"] = "pdf"
        elif name.endswith(".docx"):
            blocks, meta = extract_docx(src)
            meta["format"] = "docx"
        elif name.endswith((".txt", ".md")):
            raw = src.read_bytes()
            try:
                txt = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                txt = raw.decode("cp1251")
            blocks = [b.strip() for b in re.split(r"\n\s*\n", txt) if b.strip()]
            lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
            if len(blocks) * 3 < len(lines):  # one paragraph per line (web copies, transcripts)
                blocks = lines
            # short ALL-CAPS lines are section titles in web copies («ВСТУПЛЕНИЕ», «ИСТОРИИ»)
            blocks = [("## " + b.strip().title()) if (len(b) < 60 and b.isupper() and len(re.findall(r"[А-ЯA-Z]", b)) >= 4
                      and not b.startswith("#")) else b for b in blocks]
            meta = {"format": "text", "title": ""}
        else:
            die(f"unsupported format: {src.suffix} (supported: fb2, fb2.zip, epub, pdf, docx, txt, md)")

    out = Path(a.out)
    text = "\n\n".join(html.unescape(b) for b in blocks)
    write_text(out / "full.txt", text + "\n")
    quality = _quality(text)
    meta.update({
        "language": _language(text),
        "blocks": len(blocks),
        "headings": sum(1 for b in blocks if b.startswith("#")),
        "words": len(text.split()),
        "quality": quality,
    })
    needs_ocr = bool(meta.get("scanned_pages")) and len(meta["scanned_pages"]) > 0.3 * max(1, meta.get("pages", 1))
    meta["verdict"] = ("needs-ocr" if needs_ocr else "low-quality" if quality < 0.8 else "ok")
    write_json(out / "extract-report.json", meta)
    print(f"{meta['verdict']}: {meta['format']} lang={meta['language']} blocks={meta['blocks']} "
          f"words={meta['words']} quality={quality} -> {out / 'full.txt'}")
    mid = [b for b in blocks if len(b) > 80]
    if mid:
        print("sample (check it reads naturally — scrambled order means use page images):")
        print("  " + mid[len(mid) // 2][:220])
    if meta["verdict"] != "ok":
        sys.exit(2)


def _zip_has(path: Path, ext: str) -> bool:
    try:
        return any(n.lower().endswith(ext) for n in zipfile.ZipFile(path).namelist())
    except zipfile.BadZipFile:
        return False


if __name__ == "__main__":
    main()
