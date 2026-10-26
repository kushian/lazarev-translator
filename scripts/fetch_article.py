"""Fetch lazarev.ru posts verbatim (no summarizing), or register a pasted text, for translation.

Usage:
  python fetch_article.py URL [--root ترجمات/مقالات] [--force]
  python fetch_article.py --list SECTION_URL [--limit 10] [--root ...]   # newest posts not yet translated
  python fetch_article.py --paste FILE --title-ru "..." [--date YYYY-MM-DD] [--source-name telegram] [--url URL]
  python fetch_article.py --check URL_OR_FILE                             # already translated?

For a post it writes ROOT/<date>-<slug>/
  source.html   raw page (cache)
  source.md     title, date, body as blocks with <!-- p0001 --> markers; reader letters as "> " blocks
  meta.json     url (canonical), date, title_ru, author line, sha1 of the text
Comments, side news, banners and <!-- noindex --> parts are dropped. robots.txt is respected,
requests are spaced >= 2 s. Paid/login pages are never fetched (the skill does not sign in).
The dedup index is ROOT/index.json (keyed by canonical URL, or by text hash for pastes).
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

from _common import die, norm_ru, read_json, read_text, sha1_text, slugify, write_json, write_text

UA = "Mozilla/5.0 (lazarev-translator; personal translation)"
MONTHS = {"январ": 1, "феврал": 2, "март": 3, "апрел": 4, "ма": 5, "июн": 6, "июл": 7, "август": 8,
          "сентябр": 9, "октябр": 10, "ноябр": 11, "декабр": 12}
_last_request = [0.0]


def canonical(url: str) -> str:
    p = urllib.parse.urlsplit(url.strip())
    path = re.sub(r"/+$", "", p.path) + "/"
    return urllib.parse.urlunsplit(("https", p.netloc.lower().replace("www.", ""), path, "", ""))


def fetch(url: str) -> str:
    if re.search(r"/(profile|cart|courses/my|lk|account|login|auth)/", url) or "club.lazarev.ru" in url:
        die("refusing to fetch an account/paid page — ask the user to download it and give the file")
    rp = urllib.robotparser.RobotFileParser()
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(url))
    rp.set_url(base + "/robots.txt")
    try:
        rp.read()
        if not rp.can_fetch(UA, url):
            die(f"robots.txt disallows {url}")
    except OSError:
        pass
    wait = 2.0 - (time.time() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ru"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        charset = r.headers.get_content_charset() or "utf-8"
    _last_request[0] = time.time()
    try:
        return raw.decode(charset)
    except (UnicodeDecodeError, LookupError):
        return raw.decode("cp1251", errors="replace")


class _Post(HTMLParser):
    """Collect title (h1.head-title), date (.article-dt) and body (div.content)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.date, self.blocks = "", "", []
        self.mode = None
        self.depth = 0          # div depth inside .content
        self.quote = 0          # depth marker for blockquote divs
        self.buf: list[str] = []
        self.noindex = False
        self.base = ""
        self.links: list[str | None] = []  # open <a> hrefs inside the body

    def handle_comment(self, data):
        d = data.strip()
        if d == "noindex":
            self.noindex = True
        elif d == "/noindex":
            self.noindex = False

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "") or ""
        classes = cls.split()
        if tag == "h1" and "head-title" in classes:
            self.mode = "title"
        elif tag == "div" and "article-dt" in classes and not self.date:
            self.mode = "date"
        elif tag == "div" and classes == ["content"] and not self.blocks and self.mode is None:
            self.mode, self.depth = "body", 1
            return
        if self.mode == "body":
            if tag == "div":
                self.depth += 1
                if "blockquote" in classes or "blockquote-txt" in classes:
                    self._flush()
                    self.quote = self.quote or self.depth
            elif tag in ("p", "li", "h2", "h3", "h4"):
                self._flush()
                if tag != "p":
                    self.buf.append({"h2": "## ", "h3": "### ", "h4": "#### "}.get(tag, "- "))
            elif tag == "br":
                self.buf.append("\n")
            elif tag in ("strong", "b"):
                self.buf.append("**")
            elif tag in ("em", "i"):
                self.buf.append("*")
            elif tag == "a":
                href = dict(attrs).get("href") or ""
                if href and not href.startswith(("#", "javascript:")):
                    href = urllib.parse.urljoin(self.base, href) if self.base else href
                    self.buf.append("[")
                    self.links.append(href)
                else:
                    self.links.append(None)

    def handle_endtag(self, tag):
        if self.mode == "title" and tag == "h1":
            self.mode = None
        elif self.mode == "date" and tag == "div":
            self.mode = None
        elif self.mode == "body":
            if tag == "div":
                if self.quote and self.depth == self.quote:
                    self._flush()
                    self.quote = 0
                self.depth -= 1
                if self.depth == 0:
                    self._flush()
                    self.mode = "done"
            elif tag in ("p", "li", "h2", "h3", "h4"):
                self._flush()
            elif tag in ("strong", "b"):
                self.buf.append("**")
            elif tag in ("em", "i"):
                self.buf.append("*")
            elif tag == "a" and self.links:
                href = self.links.pop()
                if href:
                    self.buf.append(f"]({href})")

    def handle_data(self, data):
        if self.noindex and self.mode != "body":
            return
        if self.mode == "title":
            self.title += data
        elif self.mode == "date":
            self.date += data
        elif self.mode == "body":
            self.buf.append(data)

    def _flush(self):
        txt = "".join(self.buf)
        self.buf = []
        txt = re.sub(r"\*\*(\s*)\*\*", lambda m: " " if m.group(1) else "", txt)
        paras = [re.sub(r"[ \t ]+", " ", p).strip() for p in re.split(r"\n\s*\n", txt)]
        for p in paras:
            p = re.sub(r"\s*\n\s*", " ", p).strip()
            if not p or p in ("**", "*"):
                continue
            self.blocks.append("> " + p if self.quote else p)


def ru_date(text: str) -> str:
    m = re.search(r"(\d{1,2})\s+([А-Яа-яё]+)\s+(\d{4})", text)
    if not m:
        return dt.date.today().isoformat()
    mon = next((v for k, v in MONTHS.items() if norm_ru(m.group(2)).startswith(k)), 1)
    return f"{int(m.group(3)):04d}-{mon:02d}-{int(m.group(1)):02d}"


def index_path(root: Path) -> Path:
    return root / "index.json"


def in_index(root: Path, key: str) -> dict | None:
    idx = read_json(index_path(root), default={"items": []})
    return next((it for it in idx["items"] if it["key"] == key), None)


def write_post(root: Path, key: str, title: str, date: str, blocks: list[str], extra: dict, html: str = ""):
    slug = slugify(extra.get("slug_hint") or title)[:50]
    pdir = root / f"{date}-{slug}"
    head = [f"# {title}"] if title else []
    allb = head + blocks
    body = "\n\n".join(f"<!-- p{i:04d} -->\n{b}" for i, b in enumerate(allb, 1))
    write_text(pdir / "source.md", body + "\n")
    if html:
        write_text(pdir / "source.html", html)
    meta = {"kind": "article", "key": key, "date": date, "title_ru": title, "blocks": len(allb),
            "words": len(" ".join(allb).split()), "sha1": sha1_text("\n".join(allb)), **extra}
    write_json(pdir / "meta.json", meta)
    return pdir, meta


def cmd_url(url: str, root: Path, force: bool):
    key = canonical(url)
    done = in_index(root, key)
    if done and not force:
        print(f"skip: already translated -> {done.get('file_ar')}")
        return None
    html = fetch(key)
    p = _Post()
    m_base = re.search(r'<base\s+href="([^"]+)"', html)
    p.base = m_base.group(1) if m_base else "{0.scheme}://{0.netloc}/".format(urllib.parse.urlsplit(key))
    p.feed(html)
    if not p.blocks:
        die("could not find the post body (div.content) — the page layout may have changed")
    title = re.sub(r"\s+", " ", unescape(p.title)).strip()
    date = ru_date(p.date)
    pdir, meta = write_post(root, key, title, date, p.blocks,
                            {"url": key, "slug_hint": key.rstrip("/").split("/")[-1]}, html)
    quotes = sum(1 for b in p.blocks if b.startswith(">"))
    print(f"ok: {date} «{title}» {meta['blocks']} blocks ({quotes} reader-letter blocks), "
          f"{meta['words']} words -> {pdir / 'source.md'}")
    return pdir


def cmd_list(section: str, root: Path, limit: int):
    section = canonical(section)
    base = urllib.parse.urlsplit(section)
    path = base.path
    found: list[str] = []
    page = 1
    while len(found) < limit and page <= 10:
        url = section if page == 1 else f"{section}?page={page}"
        html = fetch(url)
        links = re.findall(r'href="((?:https?://(?:www\.)?lazarev\.ru)?' + re.escape(path) + r'[^"#?]+/)"', html)
        new = 0
        for href in links:
            full = canonical(urllib.parse.urljoin(section, href))
            if full == section or full in found:
                continue
            found.append(full)
            new += 1
        if not new:
            break
        page += 1
    todo = [u for u in found if not in_index(root, u)][:limit]
    print(f"{len(todo)} posts not yet translated (of {len(found)} listed):")
    for u in todo:
        print("  " + u)


def cmd_paste(file: str, title: str, date: str | None, source_name: str, root: Path, url: str = ""):
    txt = read_text(file).replace("\r\n", "\n")
    blocks = [b.strip() for b in re.split(r"\n\s*\n", txt) if b.strip()]
    key = "sha1:" + sha1_text(re.sub(r"\s+", " ", norm_ru(txt)).strip())
    done = in_index(root, key)
    if done:
        print(f"skip: this text was already translated -> {done.get('file_ar')}")
        return
    pdir, meta = write_post(root, key, title, date or dt.date.today().isoformat(), blocks,
                            {"source": source_name, "slug_hint": title, **({"url": url} if url else {})})
    print(f"ok: pasted text «{title}» {meta['blocks']} blocks -> {pdir / 'source.md'}")


def cmd_check(arg: str, root: Path):
    key = canonical(arg) if arg.startswith("http") else "sha1:" + sha1_text(
        re.sub(r"\s+", " ", norm_ru(read_text(arg))).strip())
    hit = in_index(root, key)
    print(f"translated: {hit['file_ar']}" if hit else "not translated yet")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?")
    ap.add_argument("--root", default="ترجمات/مقالات")
    ap.add_argument("--list")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--paste")
    ap.add_argument("--title-ru", default="")
    ap.add_argument("--date")
    ap.add_argument("--source-name", default="paste")
    ap.add_argument("--check")
    ap.add_argument("--url", default="", help="original URL of a pasted text (kept in the header)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    if a.list:
        cmd_list(a.list, root, a.limit)
    elif a.paste:
        cmd_paste(a.paste, a.title_ru, a.date, a.source_name, root, a.url)
    elif a.check:
        cmd_check(a.check, root)
    elif a.url:
        cmd_url(a.url, root, a.force)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
