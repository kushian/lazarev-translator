# Full book workflow (FB2 / EPUB / PDF / scanned / DOCX / TXT)

All paths below are relative to the folder the session was opened in. `S` = this skill's
`scripts/` folder. Run every script as `python -X utf8 "S/<script>.py" …`.

```
ترجمات/كتب/<العنوان العربي>/          ← Arabic folder name (user rule)
├── project.json  project.md        ← state (truth) + readable view
├── book-glossary.tsv               ← this book's new terms and names (same columns as glossary.tsv)
├── uncertain.md                    ← doubts, with block IDs
├── source/original.<ext>  full.txt  marked.md  chunks/c001.md …  chunks.json
├── work/c001.md …                  ← Arabic, same <!-- p0001 --> markers
├── checks/c001-align.json  c001-terms.json
└── النهائي/<العنوان العربي>.html + .pdf ← reading deliverables (same Arabic filename stem)
```

## 0. Resume first
`python -X utf8 S/status.py find --query "<title or slug>"`. If a project exists, never create a
second one: run `status.py next <dir>` and continue from what it prints.

## 1. Set up
1. slug: transliterated Russian title, e.g. `vyzdorovlenie-dushi` (`_common.slugify`).
2. Copy the user's file to `ترجمات/كتب/<العنوان العربي>/source/original.<ext>` (do not move it).
3. Arabic title: look it up in `works.md`. If none exists, propose one and say so to the user.

## 2. Extract
`python -X utf8 S/extract_text.py source/original.<ext> --out source`
- `ok` → continue.
- `low-quality` (scrambled lines, broken ligatures, quality < 0.8) → open a few pages of `full.txt`;
  if it is not cleanly readable, use the scanned route.
- `needs-ocr` (scanned) → first ask the user whether an FB2/EPUB edition exists (cheaper, exact).
  Otherwise, with the user's permission and a cost estimate (≈1 image read per page):
  1. `python -m pip install pymupdf` (ask first),
  2. `extract_text.py source/original.pdf --render-pages source/pages --pages 1-20` (batches of 20),
  3. read each PNG and write its Russian text **verbatim** to `source/pages/NNNN.txt`
     (no translation, no correction; unreadable spots as `[неразборчиво]`),
  4. re-read every 10th page and compare with what you wrote; fix and note discrepancies,
  5. `extract_text.py --from-pages source/pages --out source` — it flags suspiciously short pages.

## 3. Split and initialise
```
python -X utf8 S/split_chunks.py source/full.txt --out source
python -X utf8 S/status.py init ترجمات/كتب/<العنوان العربي> --kind book --slug <slug> \
   --source source/original.<ext> --title-ru "<Russian title>" --title-ar "<Arabic title>" \
   --chunks ترجمات/كتب/<العنوان العربي>/source/chunks.json
```

## 4. Decide the book's terms before translating
`python -X utf8 S/glossary.py --unknown source/marked.md --overlay book-glossary.tsv --top 60`
For each recurring Lazarev-specific term or proper name in that list, decide the rendering:
search Sablabal's usage first (`glossary.py --term`), then choose in his spirit. Append a row to
`book-glossary.tsv` (status `book`, evidence = why). Names go in too (ru regex → Arabic form), so
the 20th chapter spells them like the 1st. Tell the user briefly which new terms you fixed.

## 5. Chunk loop (one chunk at a time, all state on disk)
For each chunk:
1. `status.py next <dir>` → source, target, overlay, previous tail. `status.py set <dir> cNNN in_progress`.
2. Load the context packet — only this, not the whole book:
   - `glossary.py --scan <chunk> --overlay <dir>/book-glossary.tsv` (the terms in this chunk),
   - the previous tail printed by `next`,
   - style.md §3–§6 (re-read after any context compaction or every ~5 chunks).
3. Translate block by block into `work/cNNN.md`: copy the chunk header line and every marker
   exactly; one Arabic block per source block. For a long chunk write it in two or three
   appends so partial work survives an interruption (`next` resumes from the first missing ID).
4. `python -X utf8 S/align_check.py <src> <dst> --report checks/cNNN-align.json` → fix every error;
   for each warning re-read that source block and fix or consciously accept.
5. `python -X utf8 S/term_check.py <src> <dst> --overlay <dir>/book-glossary.tsv --report checks/cNNN-terms.json`
   → fix errors; for warnings either fix or accept (a legitimate synonym, a quotation, a reader's word).
6. Meaning spot-check (see quality.md): back-translate 2 random blocks plus every block the length
   check flagged; fix drift; log real doubts in `uncertain.md`.
7. `status.py set <dir> cNNN checked`.
After 4–6 chunks, tell the user progress (Arabic, one line) and suggest continuing in a fresh
session when the conversation is long — nothing is lost, `next` knows where to resume.

## 6. Assemble
`python -X utf8 S/assemble_book.py book ترجمات/كتب/<العنوان العربي>`
→ internal `work/assembled/<Arabic title>.md` with a title block, contents list (no page numbers), all chapters.
Then `python -X utf8 S/export_reading.py "work/assembled/<Arabic title>.md" --out-dir النهائي --doubts "work/assembled/<Arabic title> – مواضع الشك.md"`
→ `النهائي/<Arabic title>.html` and `.pdf`; review the rendered pages (`reading-output.md`).
Fix any variant warnings it prints (two spellings of a name, a forbidden form), re-run.
Translate only what the source contains: the author's own forewords yes; no translator preface,
no Sablabal preface, no acknowledgements or legal notice that are not in the source.

## Report to the user (Arabic)
Path of the final file, number of chapters/words, how many terms were newly decided, how many
open items are in `uncertain.md`. Say the checks confirm completeness and terminology — not that
the meaning is "verified" (the user cannot read Russian; be honest about what was checked).
