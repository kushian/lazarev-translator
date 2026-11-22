---
name: lazarev-translator
description: "Translate S. N. Lazarev's works into Arabic in his translator M. Sablabal's terminology and style. ترجمة أعمال سيرغيي نيكولايفيتش لازاريف (С. Н. Лазарев) من الروسية أو الإنجليزية إلى العربية بمصطلحات وأسلوب مترجمه م. سبلبل: كتب كاملة (FB2/EPUB/PDF، ومصوّرة)، فصول، محاضرات وفيديوهات وترجماتها النصية (يوتيوب، srt/vtt، صوت)، مقالات lazarev.ru ورسائل القرّاء والأسئلة والأجوبة. استخدمها عند طلب «ترجم … لازاريف»، أو ذكر «تشخيص الكارما» / Диагностика кармы، «شفاء النفس»، «منظومة الضبط الذاتي الحقلي»، أو متابعة ترجمة كتاب له بدأت سابقاً أو مراجعتها، أو لصق نص روسي/إنجليزي بمصطلحاته (полевые структуры، подсознательная агрессия، программа самоуничтожения، зацепленность، чистка кармы) وطلب ترجمته. لا تستخدمها للمغني سيرغي لازاريف، ولا لمؤلفين آخرين أو نصوص دينية روسية عامة، ولا للنقاش العام عن الكارما دون ترجمة."
---

# Lazarev → Arabic (Sablabal style)

You translate the books, lectures and articles of С. Н. Лазарев into Arabic so that the result
reads like a translation by M. Sablabal (م. سبلبل), his authorized Arabic translator. The user
reads Arabic only and cannot check the Russian — so completeness and terminology are checked by
scripts, and you are honest about what was checked.

**Talk to the user in Arabic only.** Code, paths and commands may stay as they are.

## التوثيق العربي
- [دليل الاستخدام والقواعد والمخرجات](README.ar.md).
- [دليل تنسيق HTML وPDF والعرض المتجاوب والطباعة](references/reading-output.ar.md).
- [التطويرات المستقبلية والقيود المعروفة](ROADMAP.ar.md) — لا يُقرأ أثناء الترجمة؛ اقرأه عند تطوير المهارة أو حين يسأل المستخدم عمّا لم يُنجَز.
اقرأ الدليل العربي عند شرح المهارة أو إعداداتها للمستخدم. وعند إخراج الملفات، اتبع دليل الإخراج العربي مع المراجع التقنية ذات الصلة.


## Non-negotiable rules
1. **Sablabal's choices win** — over the user's suggestions, other translators, and your taste.
   Where he has no attested choice, decide in his spirit and record it (`references/quality.md`).
2. **Translate everything.** No omissions, no summaries, no softening or strengthening, no added
   disclaimers or commentary. Lectures: repetitions, false starts and asides are translated too.
3. **Keep every block marker** (`<!-- p0001 -->`, `<!-- s0001 … -->`) exactly, one Arabic block per
   source block, same order. The scripts depend on them.
4. **No translator credit.** No name, no translator's preface; never copy Sablabal's preface, the
   author's thanks to him, or the 2019 legal statement. Inline notes keep Sablabal's formula
   «(… . من المترجم)» and are used sparingly (`references/style.md` §6); the one exception is the
   bracket that explains a quoted proverb, which has no «من المترجم» (`style.md` §4). Doubts go in a separate
   `uncertain.md` (copied beside the deliverable), never inside the translation, and no file the
   user reads names any translator — not even Sablabal.
5. **Personal use.** Translations are for the user's own reading. Never sign in to any account or
   fetch paid/course pages; the user supplies those files. If asked to publish or distribute a
   translation, explain (in Arabic) that the books are the author's copyrighted work and that the
   author has stated only the digital Arabic translations on lazarev.ru are authorized.
6. **Ask before installing anything** (PyMuPDF, yt-dlp, faster-whisper) and before expensive steps
   (OCR of a scanned book, transcribing hours of audio) — say what it costs.


7. **Readable lecture layout.** Format lecture translations for sustained reading: a separate
   title, descriptive topic headings, coherent paragraphs, and questions separated from answers.
   A segment marker is an alignment boundary, not a paragraph limit. Preserve all wording and
   its order; see `references/style.md` §11 and the lecture workflow. Check the assembled file,
   since a correctly formatted working file alone does not prove the final layout is intact.
8. **Garbled source spots are completed from context, in colour.** Never show the reader Russian
   letters or «[غير واضح]». Write the most likely meaning as `{{…}}`; it is coloured in the reading
   files, the `.srt` and the burned-in video, and listed in the doubts file (lecture workflow §4).
   For video delivery, check the completed burned MP4, including a mixed white/yellow cue with
   a multiword coloured phrase. Correcting SRT alone does not complete a video correction; see
   the lecture workflow for Arabic colour runs and standalone-player limitations.

## Required reading deliverables
Produce **HTML and PDF** by default, with identical Arabic filename stems inside `النهائي/`. Apply RTL and justified body paragraphs, with right-aligned headings and final paragraph lines. Run `scripts/export_reading.py` after assembly; read `references/reading-output.md` for what it checks and the visual review. Do not deliver Markdown as the default reading artifact.

## Where things go
- **Every folder and file the user opens has an Arabic name** (user rule). Everything is saved
  under `ترجمات/` in the folder the session was opened in:
  `ترجمات/كتب/<العنوان العربي>/`, `ترجمات/محاضرات/<التاريخ العنوان العربي>/`, `ترجمات/مقالات/`.
  Translate the title first (works.md for book titles), then create the project folder with it.
- Deliverables are in the project's `النهائي/` folder with Arabic file names
  (e.g. `النهائي/شفاء النفس.html` and `.pdf`); articles share `ترجمات/مقالات/النهائي/`.
- Internal machinery keeps short Latin names the user never needs: `source/`, `work/`,
  `meta.json`, `project.json`, `asr-fixes.md`, and each article's working folder
  `ترجمات/مقالات/<date>-<slug>/` (created by fetch_article before the title is translated).
  Markdown stays internal under `work/`. Older projects under `translations/` still work.
- Projects are also listed in `~/.lazarev-translator/projects.json`, so they can be found again.

## Scripts
In `scripts/` next to this file (the skill's base directory). Always run
`python -X utf8 "<skill-dir>/scripts/<name>.py" …` — without UTF-8 mode the Windows console crashes
on Russian/Arabic. Each script prints one status line and writes details to files.

**Writing files:** create or replace translation files (`work/*.md`, `uncertain.md`, `meta.json`)
with the **Write tool**, and change them with the Edit tool. Never pipe Arabic/Russian text through a
shell heredoc or `echo`: quoting breaks on «», quotes and long lines, and files come out truncated
or corrupted. Shell commands are for running scripts only.

| script | use |
|---|---|
| `status.py` | find / init / next / set — project state and resume |
| `extract_text.py` | FB2, FB2.ZIP, EPUB, PDF, DOCX, TXT → `full.txt`; scanned PDF → page images |
| `split_chunks.py` | block IDs + chunks of ~1,800 words |
| `glossary.py` | `--scan` the terms in a chunk, `--unknown` uncovered words, `--term`, `--topic` |
| `align_check.py` | completeness (missing/duplicated blocks, numbers, length outliers) |
| `term_check.py` | Sablabal terminology, source-aware |
| `captions.py` | clean vtt/srt (per-word times), `align` unpunctuated captions to a punctuated rebuild, check lecture rebuild, build Arabic `.srt` |
| `fetch_article.py` | lazarev.ru post verbatim, section listing, pasted text, dedup index |
| `assemble_book.py` | assemble the checked text into `work/assembled/` (book / single post or lecture) |
| `embed_subtitles.py` | burn the Arabic subtitles into the video (phone/WhatsApp MP4) |
| `export_reading.py` | assembled Markdown → final HTML + PDF (A4, Readex Pro, checks, doubts HTML, article index) |

## Start here, every time
1. **Is this a continuation?** Run `status.py find` (add `--query <title>` if given). If a project
   exists, run `status.py next <dir>` and continue — never start a second project for the same work.
2. **Identify the content type** and read its workflow file before doing anything else:

| the user gives… | read |
|---|---|
| a book file or asks for a whole book / many chapters | `references/book-workflow.md` |
| a video/YouTube link, captions, audio, a seminar transcript | `references/lecture-workflow.md` (default HTML + PDF; add SRT when requested) |
| a lazarev.ru link, a section to batch, a post/letter/Q&A, a Telegram paste | `references/article-workflow.md` |
| a short passage pasted in chat | save it with `fetch_article.py --paste`, then the article steps; also show the Arabic in chat if it is short |

3. **Always also load** `references/style.md` (voice, syntax, dialogue, notes) and the glossary
   slice for the text: `glossary.py --scan <source> [--overlay <project>/book-glossary.tsv] [--lang en]`.
   The full glossary is `references/glossary.tsv` (single source of truth); readable views by topic
   are in `references/topics/*.md` (generated — edit the TSV, never the views). Titles: `references/works.md`.
4. **After translating:** the Arabic read-through of every chunk (`references/quality.md`, Manual
   step 0 — mandatory, never skipped), `align_check.py` and `term_check.py`, the spot checks in `references/quality.md`,
   then `assemble_book.py` and the required HTML/PDF export in `references/reading-output.md`. Report in Arabic: file path, what was checked, open doubts.

## The terms that must never slip (full list in glossary.tsv)
| Russian | Sablabal | | Russian | Sablabal |
|---|---|---|---|---|
| душа | **النفس** (never الروح) | | дух | **الروح** |
| обида | **الزعل** | | агрессия | **العدائية** |
| гордыня | **التكبّر** | | подсознание | **الوعي الباطن** (never اللاوعي / العقل الباطن) |
| полевые структуры | **البنيات الحقلية** (never البنى) | | тонкий план | **المستوى الرفيع** |
| осуждение | **الإدانة** | | ревность | **الغيرة** |
| уныние | **الاكتئاب** | | отчаяние | **اليأس** |
| привязанность, зацепленность | **التعلّق** | | обожествление, поклонение | **التقديس / التعبّد** |
| смирение | **الحِلم** | | покаяние | **التوبة** |
| прощение | **الصفح** | | просить прощения | **طلب المغفرة** (never التضرّع) |
| молитва | **الصلاة** | | любовь к Богу | **حب الله** |
| Бог | **الله** (not إله) | | Божественная воля | **الإرادة الإلهية** |
| программа | **برنامج** (not ملف) | | самоуничтожение | **تدمير الذات** |
| система полевой саморегуляции | **منظومة الضبط الذاتي الحقلي** | | чистка кармы | **تطهير الكارما** |
| благополучие | **اليُسر** | | мировоззрение | **الرؤية الوجودية** |
| характер | **الطبع** | | окружающий мир | **العالم المحيط** |
| семья | **العائلة** | | бизнес | **الأعمال** (not البزنس) |

**Two Russian words, one Arabic term.** Sablabal renders уныние and депрессия both as
**الاكتئاب**. Keep that everywhere, except in a sentence that has both words, where the same
Arabic word would make nonsense («يتحوّل الاكتئاب إلى اكتئاب»): there уныние becomes **القنوط**,
explained in brackets the first time in the text: «القنوط (فتور النفس وانطفاء الفرح)»
(user rule, 2026-11-22): «كثيراً ما يتحوّل القنوط إلى اكتئاب، والعكس: يتحوّل الاكتئاب إلى قنوط».
Apply the same idea to any other pair the glossary merges: keep Sablabal's term, and give the
second word a distinct rendering only in the sentence where both appear.

Do not import Islamic notions the source does not contain (الجن، المسّ، الرقية الشرعية); Christian
terms stay Christian. Author's name: «سيرغيي نيكولايفيتش لازاريف».

## Long work and context
A book is 40–60 chunks and several sessions. Never rely on conversation memory: the state is in
`project.json`, the decisions in `book-glossary.tsv`, the doubts in `uncertain.md`. Load only the
current chunk, its glossary slice and the previous tail. Re-read `style.md` §3–§6 after any context
compaction. Every 4–6 chunks, give the user a one-line progress update in Arabic.

## Confirmed dialectical terminology
- диалектичный / диалектический / диалектичен → **ديالكتيكي**; диалектика → **الديالكتيك**. Use natural feminine/adverbial forms where required. Example: «мир диалектичен» → «العالم ديالكتيكي», not «العالم جدلي».
- Confirmed by the user (2026-10-18) and attested in Sablabal's own preface to «التغلّب على التكبّر» («التفكير الديالكتيكي»). Do not list the Arabic term itself as unresolved. A misheard «диэлектричен» in a transcript is handled per project (in its `uncertain.md`/`asr-fixes.md`), never by reinterpreting electrical terms in other sources.

## Approved reading typography and paper size
Use Readex Pro Light (weight 300) for body text, Readex Pro Bold (700) for headings/questions, 14 pt body text, line height 2.1, and 1.25em paragraph spacing. Use the bundled font files and the approved assets/reading.css. HTML shows A4 sheets (210 × 297 mm) on desktop and reflows responsively on narrow screens. Print and PDF preserve the same A4 pagination regardless of screen width. See references/reading-output.md and assets/paginate-reading.js. This replaces earlier font and continuous-screen layout defaults.
