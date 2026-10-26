"""Project state for long translations (books, long lectures). project.json is the truth;
project.md is a readable view regenerated on every change.

Usage:
  python status.py find [--query TEXT]          # existing projects in ./ترجمات (or legacy ./translations) and the registry
  python status.py init PROJECT_DIR --kind book|lecture|article --slug SLUG --source FILE
                        --title-ru "..." [--title-ar "..."] [--lang ru|en] [--chunks SOURCE_DIR/chunks.json]
  python status.py show PROJECT_DIR
  python status.py next PROJECT_DIR             # next chunk + the context packet paths + previous tail
  python status.py set PROJECT_DIR CHUNK STATUS [--note "..."]   STATUS: pending|in_progress|translated|checked
  python status.py title PROJECT_DIR --title-ar "..."

Never rely on chat memory to know where a book stands: run `next`.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from _common import (REGISTRY, die, read_json, read_text, registry_add, sha1_file, split_marked,
                     write_json, write_text)

STATUSES = ["pending", "in_progress", "translated", "checked"]
AR_STATUS = {"pending": "لم يبدأ", "in_progress": "جارٍ", "translated": "مترجم", "checked": "مفحوص"}


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def load(pdir: Path) -> dict:
    p = pdir / "project.json"
    data = read_json(p)
    if data is None:
        die(f"no project.json in {pdir} — run `status.py find` or `status.py init`")
    return data


def save(pdir: Path, data: dict) -> None:
    data["updated"] = now()
    write_json(pdir / "project.json", data)
    render(pdir, data)


def render(pdir: Path, data: dict) -> None:
    done = sum(1 for c in data["chunks"] if c["status"] == "checked")
    lines = [f"# {data.get('title_ar') or data.get('title_ru')}", "",
             f"- **الأصل:** {data.get('title_ru', '')} ({data.get('lang', 'ru')})",
             f"- **النوع:** {data['kind']} — **المجلد:** `{data['root']}`",
             f"- **التقدّم:** {done} / {len(data['chunks'])} مقطع مفحوص",
             f"- **آخر تحديث:** {data.get('updated', '')}", "",
             "| المقطع | العنوان | الكلمات | الحالة | ملاحظة |", "|---|---|---|---|---|"]
    for c in data["chunks"]:
        lines.append(f"| {c['id']} | {c.get('title', '')} | {c.get('words', '')} | "
                     f"{AR_STATUS.get(c['status'], c['status'])} | {c.get('note', '')} |")
    write_text(pdir / "project.md", "\n".join(lines) + "\n")


def cmd_init(a):
    pdir = Path(a.project).resolve()
    if (pdir / "project.json").exists():
        die(f"project already exists: {pdir / 'project.json'} — resume it with `status.py next`")
    chunks = []
    if a.chunks:
        man = read_json(a.chunks)
        base = Path(a.chunks).resolve().parent
        for c in man["chunks"]:
            chunks.append({"id": c["id"], "title": c.get("title", ""), "first": c["first"], "last": c["last"],
                           "words": c["words"], "src": str((base / c["file"]).relative_to(pdir)).replace("\\", "/"),
                           "dst": f"work/{c['id']}.md", "status": "pending", "note": ""})
    src = Path(a.source).resolve() if a.source else None
    data = {"schema": 1, "kind": a.kind, "slug": a.slug, "title_ru": a.title_ru or "", "title_ar": a.title_ar or "",
            "lang": a.lang, "root": str(pdir), "source_file": str(src) if src else "",
            "source_sha1": sha1_file(src) if src and src.exists() else "",
            "overlay": "book-glossary.tsv", "created": now(), "chunks": chunks}
    pdir.mkdir(parents=True, exist_ok=True)
    if not (pdir / "book-glossary.tsv").exists():
        from _common import GLOSSARY_COLS
        write_text(pdir / "book-glossary.tsv", "\t".join(GLOSSARY_COLS) + "\n")
    if not (pdir / "uncertain.md").exists():
        write_text(pdir / "uncertain.md", "# مواضع الشك\n\n| المعرّف | العبارة الأصلية | الترجمة المختارة | السبب |\n|---|---|---|---|\n")
    save(pdir, data)
    registry_add(a.kind, a.slug, pdir, data["title_ar"] or data["title_ru"])
    print(f"ok: project {a.slug} with {len(chunks)} chunks at {pdir}")


def cmd_show(a):
    pdir = Path(a.project)
    data = load(pdir)
    counts = {s: sum(1 for c in data["chunks"] if c["status"] == s) for s in STATUSES}
    print(f"{data['slug']} ({data['kind']}): " + ", ".join(f"{s}={n}" for s, n in counts.items()))
    nxt = _next(data)
    print(f"next: {nxt['id']} ({nxt['status']})" if nxt else "all chunks checked — ready to assemble")


def _next(data):
    for want in ("in_progress", "translated", "pending"):
        for c in data["chunks"]:
            if c["status"] == want:
                return c
    return None


def cmd_next(a):
    pdir = Path(a.project)
    data = load(pdir)
    if data.get("source_file") and Path(data["source_file"]).exists() and data.get("source_sha1"):
        if sha1_file(data["source_file"]) != data["source_sha1"]:
            print("WARNING: the source file changed since init — check before continuing")
    c = _next(data)
    if not c:
        print("all chunks checked — run assemble_book.py")
        return
    idx = data["chunks"].index(c)
    print(f"next chunk: {c['id']}  status={c['status']}  words={c['words']}  title={c.get('title', '')}")
    print(f"  source : {pdir / c['src']}")
    print(f"  target : {pdir / c['dst']}")
    print(f"  overlay: {pdir / data.get('overlay', 'book-glossary.tsv')}")
    if c["status"] == "translated":
        print("  action : run align_check.py + term_check.py on it, fix, then `set ... checked`")
    elif c["status"] == "in_progress" and (pdir / c["dst"]).exists():
        done = len(split_marked(read_text(pdir / c["dst"])))
        print(f"  action : partially written ({done} blocks) — continue from the first missing block ID")
    if idx > 0:
        prev = pdir / data["chunks"][idx - 1]["dst"]
        if prev.exists():
            tail = split_marked(read_text(prev))[-2:]
            print("  previous translated tail (for continuity):")
            for pid, body in tail:
                print(f"    <!-- {pid} --> {body[:300]}")


def cmd_set(a):
    pdir = Path(a.project)
    data = load(pdir)
    if a.status not in STATUSES:
        die(f"status must be one of {STATUSES}")
    c = next((c for c in data["chunks"] if c["id"] == a.chunk), None)
    if c is None:
        die(f"no chunk {a.chunk}")
    if a.status in ("translated", "checked") and not (pdir / c["dst"]).exists():
        die(f"target file missing: {pdir / c['dst']}")
    c["status"] = a.status
    if a.note is not None:
        c["note"] = a.note
    if a.status in ("translated", "checked"):
        c["dst_sha1"] = sha1_file(pdir / c["dst"])
    save(pdir, data)
    print(f"ok: {a.chunk} -> {a.status}")


def cmd_title(a):
    pdir = Path(a.project)
    data = load(pdir)
    data["title_ar"] = a.title_ar
    save(pdir, data)
    registry_add(data["kind"], data["slug"], Path(data["root"]), a.title_ar)
    print("ok")


def cmd_find(a):
    found = {}
    for p in [*Path.cwd().glob("ترجمات/**/project.json"), *Path.cwd().glob("translations/**/project.json")]:
        d = read_json(p)
        found[str(p.parent.resolve())] = d
    if not a.here:  # the registry lists projects in other folders too — this is what prevents duplicates
        reg = read_json(REGISTRY, default={"projects": []})
        for e in reg["projects"]:
            p = Path(e["path"]) / "project.json"
            if p.exists() and str(p.parent) not in found:
                found[str(p.parent)] = read_json(p)
    q = (a.query or "").lower()
    n = outside = 0
    cwd = str(Path.cwd().resolve())
    for path, d in found.items():
        meta = read_json(Path(path) / "meta.json", default={}) or {}
        hay = " ".join([d.get("slug", ""), d.get("title_ru", ""), d.get("title_ar", ""),
                        d.get("url", ""), meta.get("url", ""), meta.get("title_ru", "")]).lower()
        if q and q not in hay:
            continue
        done = sum(1 for c in d["chunks"] if c["status"] == "checked")
        is_here = path.startswith(cwd)
        outside += not is_here
        here = "" if is_here else "  (OUTSIDE current folder)"
        print(f"{d['kind']:8} {d['slug']:40} {done}/{len(d['chunks'])}  {path}{here}")
        n += 1
    if not n:
        print("no existing project found" + (" in this folder" if a.here else ""))
    elif outside:
        print("NOTE: a project OUTSIDE this folder already exists for this work. Do not start a second one:\n"
              "      ask the user (in Arabic) whether to continue it where it is (status.py next <its path>)\n"
              "      or to start a separate copy here on purpose. `find --here` lists only this folder.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("project")
    p.add_argument("--kind", required=True, choices=["book", "lecture", "article"])
    p.add_argument("--slug", required=True)
    p.add_argument("--source")
    p.add_argument("--title-ru")
    p.add_argument("--title-ar")
    p.add_argument("--lang", default="ru", choices=["ru", "en"])
    p.add_argument("--chunks")
    for name in ("show", "next"):
        sp = sub.add_parser(name)
        sp.add_argument("project")
    p = sub.add_parser("set")
    p.add_argument("project")
    p.add_argument("chunk")
    p.add_argument("status")
    p.add_argument("--note")
    p = sub.add_parser("title")
    p.add_argument("project")
    p.add_argument("--title-ar", required=True)
    p = sub.add_parser("find")
    p.add_argument("--query", help="title (ru/ar), slug or URL fragment, e.g. the YouTube id")
    p.add_argument("--here", action="store_true", help="only projects under the current folder")
    a = ap.parse_args()
    {"init": cmd_init, "show": cmd_show, "next": cmd_next, "set": cmd_set, "title": cmd_title,
     "find": cmd_find}[a.cmd](a)


if __name__ == "__main__":
    main()
