# Articles, readers' letters, Q&A, short posts

`S` = this skill's `scripts/` folder; run as `python -X utf8 "S/<script>.py" …`.

```
ترجمات/مقالات/
├── index.json                         ← what is already translated (by canonical URL or text hash)
├── <YYYY-MM-DD>-<slug>/source.html  source.md  meta.json  work.ar.md
└── النهائي/<YYYY-MM-DD العنوان العربي>.html + .pdf ← two reading formats per post
```

Sources: lazarev.ru public sections — `news/author/` (author's posts, readers' questions with
answers), `news/pisma-chitatalej/` (readers' letters), `help/faq/`, `articles/…`, the quote of the
day; forum threads; Telegram (the user pastes); lazarev-international.com (English).

## One post from lazarev.ru
1. `python -X utf8 S/fetch_article.py <URL>` → `ترجمات/مقالات/<date>-<slug>/source.md`.
   It takes the page verbatim (title, date, body; reader letters become `> ` blocks), drops
   comments, side news and banners, respects robots.txt, and refuses login/paid pages.
   Never use a summarizing web tool to get the text — it rewrites it.
2. Glossary slice: `glossary.py --scan <dir>/source.md`.
3. Translate into `<dir>/work.ar.md` with the same markers. Q&A layout (style.md §5): the reader's
   letter as `> ` blockquotes in the reader's voice, the answer in Lazarev's voice; keep editorial
   lines of the post (rubric intro, contact line) — they are part of the post.
4. `align_check.py` and `term_check.py` on `source.md` / `work.ar.md`.
5. Topic tags: pick from الحقل والطاقة، الماورائيات، المال والأعمال، العائلة والعلاقات،
   الأطفال والحمل، الأمراض والجسد، الدين والصلاة، المصير والمستقبل (one or more).
6. `python -X utf8 S/assemble_book.py single <dir>/work.ar.md --kind article --meta <dir>/meta.json --title-ar "…" --topics "…" --out-dir <dir>/work/assembled [--doubts <dir>/uncertain.md] [--author "…"]`
   → internal assembled Markdown + entry in `index.json` (+ internal doubts if given).
   Then export: `python -X utf8 S/export_reading.py "<dir>/work/assembled/<date> <title>.md" --out-dir ترجمات/مقالات/النهائي --doubts "<dir>/work/assembled/<date> <title> – مواضع الشك.md" --meta <dir>/meta.json --index ترجمات/مقالات/index.json`
   → HTML + PDF (+ doubts HTML) in `النهائي/`, and the index points at them (see `reading-output.md`).
   `--author`: the header names Lazarev by default. For posts written *about* him by the site's
   editors (rubric intros, readers' letters without his answer, news) pass
   `--author "هيئة تحرير موقع lazarev.ru"`; for a reader's letter alone, the reader as signed.
   Links in the post (Telegram, email, other pages) are kept as Markdown links — keep them.
Comments under posts are not translated unless the user asks.

## Batch ("translate the last 10 posts of …")
1. `python -X utf8 S/fetch_article.py --list <SECTION_URL> --limit 10` → URLs not yet in `index.json`.
2. Show the user the list (titles once fetched) and confirm before starting; keep batches ≤ 20.
3. Run the single-post steps for each, one after another; `index.json` is updated after each, so an
   interrupted batch resumes by listing again.

## Pasted text (Telegram, forum, a page you cannot fetch, the English site)
Save the user's text to a file, then
`python -X utf8 S/fetch_article.py --paste <file> --title-ru "<title>" --date YYYY-MM-DD --source-name telegram [--url <original URL>]`
(dedup by text hash). For English sources use `--lang en` in `glossary.py --scan` and
`term_check.py`; English is a translation of a translation: when an English word blurs a Lazarev
distinction (soul = душа or дух? depression = уныние or депрессия?), choose by Sablabal's usage
and context and log the choice in `<dir>/uncertain.md` (see quality.md §3).
