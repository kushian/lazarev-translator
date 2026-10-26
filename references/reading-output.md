# Final reading output: HTML and PDF

Apply to books, lectures and articles. The default deliverables are two files in the
project's final output directory, with the same translated Arabic filename stem:

- `النهائي/<العنوان العربي>.html`
- `النهائي/<العنوان العربي>.pdf`

If the existing naming convention includes a known date, retain it in both filenames.
Markdown is an internal translation, checking and assembly format, not the default deliverable.
Do not ask the user to choose the reading format again. SRT remains an additional output when
requested and timestamps exist. Explicit later user format instructions take precedence.

## The export command (use it; do not hand-build HTML/PDF)

```
python -X utf8 S/export_reading.py "<assembled>.md" --out-dir <النهائي dir> \
   [--doubts "<assembled> – مواضع الشك.md"] [--meta meta.json --index ترجمات/مقالات/index.json]
```
It implements every step below with the installed Chrome or Edge (no Python packages needed):
semantic RTL HTML, embedded CSS and Readex Pro fonts, A4 pagination with
`assets/paginate-reading.js` at a desktop viewport, PDF printed from the same HTML without
browser headers, and the checks (PDF pages = sheets, A4 size, selectable Arabic, text preserved).
It also writes the separate doubts HTML and points the article index at the final HTML/PDF.
Exit 1 means a check failed: read the PROBLEM lines, fix, re-run. Then still look at rendered
pages (step 7) — a passing script is not a visual review. The steps below document what the
script does, for repairs and for unusual content (oversized tables/images).

## Assemble without changing the translation

1. Complete source alignment, terminology and meaning reviews on the marked Markdown files.
2. Assemble the checked text with `assemble_book.py` into `work/assembled/`. For `book`, this is
   now the default; for `single`, pass `--out-dir <project>/work/assembled`.
3. Convert the assembled Markdown to semantic HTML using an available Markdown renderer.
   Preserve all text, headings, emphasis, links, lists, quotations, tables and footnotes. Parse
   front matter as metadata and show its title/author/source as a readable header, not YAML.
   Do not implement Markdown conversion by stripping punctuation or a few regex replacements.
4. Write UTF-8 HTML with `<!doctype html>`, `<html lang="ar" dir="rtl">`, charset and viewport
   metadata, a meaningful `<title>`, and the complete text inside `<main>`. Embed the CSS from
   `assets/reading.css` in a `<style>` element so the file opens independently. Keep a visible
   translated title at the beginning. Do not add translator credit or rewrite the translation.
5. Print this same HTML to the matching PDF using an available rendering engine that supports
   Arabic shaping, bidirectional text and print CSS (for example a local browser print engine
   or an installed HTML-to-PDF engine). Prefer available local/bundled dependencies. Ask before
   installing missing dependencies, following the skill's existing installation rule.
6. Use A4, comfortable margins, an Arabic-capable font, body text around 14 pt, generous line
   spacing and page numbers. Wait for fonts to load before printing; embed/subset the fonts in
   PDF where supported. Disable browser URL/date headers. Do not mirror/reverse Arabic strings
   or turn whole pages into images. Keep PDF text selectable and searchable.
7. Inspect rendered PDF pages from the beginning, middle and end, plus any tables or difficult
   page breaks. Check connected Arabic letters, RTL order, justified paragraphs, unclipped text,
   heading placement, page numbers and content completeness. Compare the final HTML text with
   assembled text; page creation or a successful process exit alone is not a layout check.
8. Deliver links to HTML and PDF. If PDF generation fails or a renderer is missing, retain the
   HTML, report the specific blocker and do not claim both outputs are complete. Do not silently
   replace the PDF with Markdown or an empty placeholder.

## Alignment and pagination

Body paragraphs use `text-align: justify` and `text-align-last: right`. Titles, headings,
short questions, dialogue turns and non-speech cues stay right-aligned. Mark short standalone
questions/dialogue/cues with the matching CSS classes. Preserve paragraph gaps. Do not insert
manual spaces or kashida characters to force alignment. Keep headings with following text,
avoid single orphan lines, and allow long paragraphs/tables to span pages rather than clip them.

Use the print engine's page-number footer if it does not support CSS page margin boxes; do not
enable both and duplicate page numbers. Show distinct A4 sheets on screen, with a neutral background, clear page boundaries and page numbers. At screen widths of 900px or less, reflow into a continuous responsive column without horizontal scrolling. Hide page numbers and sheet decoration only on narrow screens; retain A4 sheets on desktop and for print.

## Doubts and indexing

Keep working doubts in `uncertain.md`. If there are open doubts, export them separately as
`النهائي/<العنوان العربي> – مواضع الشك.html`, using the same RTL styling and complete tables;
do not insert this commentary into the translated body. A separate PDF of doubts is optional
unless requested. Historical deliverables and backups are not deleted automatically.
For articles, retain deduplication entries and update `file_ar` to the final HTML path; also
record `file_pdf` after successful PDF export. Never leave a final index pointing at an internal
assembled Markdown file. All workflows finish with this export step.

## Approved A4 layout (user-selected)

- Use the supplied `assets/fonts/ReadexPro-Light.ttf` at weight 300 for body text and
  `ReadexPro-Bold.ttf` at weight 700 for headings, strong emphasis and questions. Embed both
  fonts as data URLs in standalone HTML; replace the relative font URLs in the CSS during
  export. Do not depend on the user's installed fonts or a remote font service.
- Use `assets/reading.css`: body 14 pt, line height 2.1, paragraph gap 1.25em; headings
  23/18/16 pt. Keep justified body text with right-aligned last lines and RTL.
- Each visible sheet is exactly 210 × 297 mm; internal margins are 22 mm top/left/right
  and 24 mm bottom. Content height is 251 mm. Use page numbers in the lower margin.
- After rendering semantic HTML and awaiting `document.fonts.ready`, load
  `assets/paginate-reading.js` in the browser and call `await window.paginateReading()`.
  It builds `.a4-page` sheets and splits long paragraphs while preserving inline markup.
  It verifies normalized text preservation. Serialize the resulting DOM into the final HTML
  so opening the file does not depend on running a pagination script.
- For these explicit sheets append `@page { size: A4; margin: 0; }`, print with zero outer
  margins and disable browser headers/footers. Each sheet already contains internal margins
  and its page number; adding another set would duplicate them.
- Do not paginate notes tables with the paragraph-only helper. Keep notes HTML in a continuous
  A4-width reading layout, or use a table-aware pagination solution. For translated bodies
  containing oversized tables/images, extend the paginator or use a compatible paged HTML
  engine; never clip the block or omit it.
- Confirm HTML sheet count equals PDF page count, check all PDF page sizes, and inspect pages
  from the beginning/middle/end. If a page overflows or pagination reports changed text,
  repair it before delivery. Preserve the complete translation and established headings.

## Responsive screen reading
Use the screen-only breakpoint in assets/reading.css. At 900px and below, .a4-page and .page-content use display: contents so text follows the viewport. Keep font sizes readable and margins fluid. These screen rules must not change PDF or print pagination. Check widths 390, 768 and 1280 px for horizontal overflow, and emulate print at a narrow viewport to confirm A4 sheets remain intact. Run pagination at a desktop viewport or under print media, never with the narrow screen layout active.
