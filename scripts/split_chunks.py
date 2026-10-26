"""Give every source block a stable ID and split the text into translation chunks.

Usage:
  python split_chunks.py FULL.txt --out SOURCE_DIR [--target 1800] [--max 2500] [--prefix p]

Reads blocks separated by blank lines (output of extract_text.py or a pasted text).
Writes:
  SOURCE_DIR/marked.md          whole text, each block preceded by <!-- p0001 -->
  SOURCE_DIR/chunks/c001.md     one file per chunk (same markers)
  SOURCE_DIR/chunks.json        manifest: id, title, first/last block, words, file
Chunks never cross a top-level heading (# or ##) once they have >= 25% of target words,
and never split a block. IDs are permanent: the translation must keep every marker.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from _common import read_text, write_json, write_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("full")
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=int, default=1800)
    ap.add_argument("--max", type=int, default=2500)
    ap.add_argument("--prefix", default="p", choices=["p", "s"])
    a = ap.parse_args()

    text = read_text(a.full).replace("\r\n", "\n")
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    out = Path(a.out)
    width = 4 if len(blocks) < 10000 else 6
    ids = [f"{a.prefix}{i:0{width}d}" for i in range(1, len(blocks) + 1)]

    marked = "\n\n".join(f"<!-- {i} -->\n{b}" for i, b in zip(ids, blocks))
    write_text(out / "marked.md", marked + "\n")

    chunks, cur, words, title = [], [], 0, ""
    current_title = ""

    def close():
        nonlocal cur, words
        if cur:
            n = len(chunks) + 1
            cid = f"c{n:03d}"
            body = "\n\n".join(f"<!-- {i} -->\n{b}" for i, b in cur)
            header = f"<!-- chunk {cid} | {cur[0][0]}-{cur[-1][0]} | words {words} -->"
            write_text(out / "chunks" / f"{cid}.md", header + "\n\n" + body + "\n")
            chunks.append({"id": cid, "title": title, "first": cur[0][0], "last": cur[-1][0],
                           "blocks": len(cur), "words": words, "file": f"chunks/{cid}.md"})
        cur, words = [], 0

    for i, b in zip(ids, blocks):
        w = len(b.split())
        is_top = bool(re.match(r"#{1,2}\s", b))
        if is_top:
            current_title = b.lstrip("# ").strip()
        if cur and ((is_top and words >= 0.25 * a.target) or words + w > a.max or words >= a.target and _sentence_end(cur[-1][1])):
            close()
        if not cur:
            title = current_title
        cur.append((i, b))
        words += w
    close()

    write_json(out / "chunks.json", {"blocks": len(blocks), "chunks": chunks})
    total = sum(c["words"] for c in chunks)
    print(f"ok: {len(blocks)} blocks, {len(chunks)} chunks, {total} words -> {out / 'chunks.json'}")


def _sentence_end(block: str) -> bool:
    return bool(re.search(r"[.!?…»\"]\s*$", block))


if __name__ == "__main__":
    main()
