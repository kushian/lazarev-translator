# Lectures, seminars, videos, audio

`S` = this skill's `scripts/` folder; run as `python -X utf8 "S/<script>.py" …`.

```
ترجمات/محاضرات/<YYYY-MM-DD العنوان العربي>/
├── meta.json            ← title_ru, url, date, duration, speakers (write it yourself)
├── source/raw.ru.vtt|srt|txt     ← exactly what was obtained
├── source/raw-segments.md        ← words as captioned, timed segments <!-- s0001 start-end -->
├── source/cleaned.md             ← same segments, punctuation/paragraphs/speakers rebuilt
├── asr-fixes.md                  ← every changed word, with reason
├── work/lecture.ar.md            ← Arabic, same <!-- s… --> markers
└── النهائي/<التاريخ العنوان>.html + .pdf (and .srt when requested)
```

## 0. Output format
Default to readable HTML + PDF using `reading-output.md`; do not ask again. Add SRT when requested.
SRT requires timestamps; an untimed transcript still supports complete HTML and PDF output.

## 1. Get the Russian text (cheapest reliable source first)
1. A transcript or caption file the user gives you.
2. YouTube captions — needs `yt-dlp` (ask permission once: `python -m pip install yt-dlp`):
   `yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs ru --sub-format vtt -o "source/raw.%(ext)s" URL`
   Prefer uploaded subtitles (`raw.ru.vtt` without `-orig`/auto) over automatic ones.
   **Auto-dubbed videos:** YouTube now adds machine-dubbed audio tracks (e.g. «English – dubbed-auto»);
   downloaders like WinX pick the default, often the dub. Captions are unaffected. When the user wants
   the video itself, or audio for transcription, take the **original Russian** track explicitly
   (`yt-dlp -F URL` lists them; needs ffmpeg for merging — ask before installing, e.g.
   `winget install Gyan.FFmpeg`):
   `yt-dlp -f "bv*[height<=1080][ext=mp4]+ba[language=ru][ext=m4a]/bv*[height<=1080]+ba[language=ru]" --merge-output-format mp4 -o "video.%(ext)s" URL`
   Re-tag the audio as Russian (`ffmpeg -i video.mp4 -c copy -map 0 -metadata:s:a:0 language=rus out.mp4`),
   name it exactly like the Arabic `.srt` in `النهائي/` so players load the subtitles automatically.
3. Audio/video without captions — speech-to-text is the last resort: CPU transcription of a
   2–3 h lecture takes hours. Explain the cost, ask, then e.g. `python -m pip install faster-whisper`
   and transcribe with language `ru`, model `medium` or better, writing an `.srt`.
4. lazarev.ru courses, the online cinema (club.lazarev.ru) and anything behind a login: never sign
   in or fetch; the user downloads the video/captions/transcript and gives you the file.

## 1b. Check the caption quality before anything else
`python -X utf8 S/captions.py quality source/raw.ru.vtt --report source/quality.json`
- **good** (punctuated, few odd fragments): continue with these captions.
- **usable** (punctuated, but many odd fragments): continue; garbled spots are completed from
  context (§4, coloured `{{…}}`). Offer the Whisper route below as an option.
- **poor** (no punctuation — older or bad auto-captions): see "If the captions are garbled".

### If the captions are garbled
YouTube auto-captions vary a lot from video to video. When `quality` says **poor**, or rebuilding the
Russian shows dozens of nonsense words, do not translate around them. In this order:
1. **Ask the user for a better source:** an uploaded transcript, the lecture's text on lazarev.ru,
   or a subtitle file from the course.
2. **Offer Whisper** on the **original Russian audio** (§1: never the auto-dub), stating the cost
   before installing or running anything: model download ~1.5 GB (medium) to ~3 GB (large-v3), and
   on a CPU roughly half to twice the lecture's length (much faster with a GPU). Keep the YouTube
   captions as a second source: words on which both agree are reliable, words they disagree on go to
   `uncertain.md` as one list for the user. (Scripted Whisper transcription and the two-source
   comparison are planned — see ROADMAP.ar.md; until then run faster-whisper by hand with
   `language="ru"`, `vad_filter=True`, `word_timestamps=True`, and write an `.srt`.)
3. **Otherwise (the user's default):** translate from the captions and complete every garbled spot
   from context as `{{…}}` (§4); it shows in a different colour in the reading file, the `.srt` and
   the burned-in video, and is listed in the doubts file. Tell the user how many spots there are.
Whisper can invent text in silence or music and repeat a line many times: check its output for
repeated lines before using it.

## 2. Clean mechanically
`python -X utf8 S/captions.py clean source/raw.ru.vtt --out source`
Removes rolling auto-caption repetitions (a technical artifact, not speech) and groups words into
**whole-sentence** timed segments (one translation unit per sentence; very long sentences are cut at
a comma). Words inside one caption get proportional times, so two sentences never share a timestamp. A plain-text transcript: save it as `source/full.txt` and run
`split_chunks.py source/full.txt --out source --prefix s` (no timing).

Non-speech tags (`[Музыка]`, `[Аплодисменты]`, `[Смех]`) are not words: `clean` turns each run of
them into its own segment holding only `♪`. Keep those segments exactly as they are in `cleaned.md`.

YouTube auto-captions carry a timestamp for every word; `clean` uses them (cleaning-report.json says
`"word_times": "per-word …"`), so subtitles start when the word is spoken, not when the cue settles.

**Captions without punctuation** (older videos: `clean` then makes few, very long segments) — do not
punctuate segment by segment. Write the whole lecture once as `source/punctuated.txt`: the captioned
words in the same order, with punctuation, capitals, speaker labels on their own (`**Ведущая:**`),
`[неразборчиво: …]` around garble, and only clear recognition fixes. Then
`python -X utf8 S/captions.py align source/punctuated.txt --words source/words.json --out source`
→ whole-sentence `cleaned.md` plus `raw-segments.md` regrouped to match, so `wordcheck` below audits
every word you changed. It refuses if under 90 % of caption words are found (words moved or dropped).
A false start marked `…` ends a segment; inside a sentence write it with ` - ` instead.

## 3. Rebuild the Russian — the line between "rebuild" and "edit"
Copy `raw-segments.md` to `cleaned.md` and, inside each segment, without moving text between
segments:
- **Allowed freely:** punctuation, capital letters, paragraph breaks, speaker labels
  (`**Лазарев:**`, `**Вопрос из зала:**`, `**Ведущий:**`), and a topic heading `## …` at the start of
  a segment where the subject changes.
- **Allowed only with a log line in `asr-fixes.md`:** changing a word that is clearly a
  recognition error (e.g. «полевые структуры» heard as «полевые структура»). Table columns:
  segment | time | captioned | corrected | reason | confidence.
- **Speaker labels are added, never substituted:** if the speaker *says* «Вопрос из зала…» or
  «Следующий вопрос», those words are speech — keep and translate them, and add the label
  before them (`**Ведущий:** Вопрос из зала: …`). Turning spoken words into a label deletes them.
- **Never:** removing repetitions, false starts, fillers («вот», «значит», «так сказать»),
  digressions or audience remarks — they are speech and get translated. Never guess a word:
  keep the captioned word and add `[неразборчиво: …]`.
Then: `python -X utf8 S/captions.py wordcheck source/raw-segments.md source/cleaned.md`
It must pass (≤ 2 % words changed, no segment lost) and every change it lists must be in
`asr-fixes.md`. It counts **words only**: punctuation, capitals, `## headings`, `¶`, speaker labels,
bare dashes and the `[неразборчиво:` marker are ignored, so rebuilding layout never trips the 2 %. If a speaker cannot be identified, label «**متحدث آخر:**» rather than guess.

## 4. Translate
Translate `cleaned.md` into `work/lecture.ar.md`, copying every `<!-- sNNNN start-end -->` line
exactly. Everything is translated, including repetitions and spoken connectors (rendered as
natural spoken Arabic: «يعني»، «إذن»، «هكذا»، «حسناً»). Labels: «**لازاريف:**»،
«**سؤال من الحضور:**»، «**المحاور:**».

**Music marks:** a segment that is only `♪` (music, applause or laughter) is copied as `♪`, never
translated: no «[موسيقى]» or «[تصفيق]» in the Arabic. The player shows it as a quiet note and the
reading text leaves it out.

**Garbled spots (user rule): complete them from context, never show them raw.** For every
`[неразборчиво: x]` in the source segment, write in the Arabic the most likely meaning, inferred
from the sentence, the surrounding argument and Lazarev's usual wording, inside `{{…}}`:
`أحد معارفي قال إنَّ {{كثيراً من رجال العصابات الذين عرفهم}} اليوم تحت التراب`.
- Complete only what the context really supports; keep it short, in the speaker's voice, no new
  claims. If nothing can be inferred, write `{{…}}` (a coloured ellipsis), never the Cyrillic.
- Also use `{{…}}` when a clear ASR fix is not certain enough for `asr-fixes.md`.
- Never write Russian letters or «[غير واضح]» in the Arabic: readers and viewers do not see the
  source, and mixed scripts break the line order.
`{{…}}` is rendered orange in HTML/PDF (with a one-line legend under the source details) and
yellow in the `.srt` and the burned-in video.
Long lectures (> ~3,000 words): translate in passes of ~40 segments, appending; to resume, run
`align_check.py` — the missing segment IDs are where to continue. For multi-session work create a
state file: `status.py init <dir> --kind lecture --slug <slug> --title-ru "…"` and note progress
with `status.py set` on a single chunk, or simply rely on align_check's missing list.


### Reading layout before assembly
Timed captions: start each new paragraph's segment with `¶ ` (style.md §11); without it every
caption segment would become a one-line paragraph. Untimed transcripts use normal blank-line
paragraphs inside their segments.
Apply `style.md` §11: add neutral topic headings, rebuild coherent paragraphs, and visually
separate each spoken question from its answer. Keep the full text and every segment marker;
one segment may contain several paragraphs. Layout edits do not authorize rewriting claims,
summarizing, removing repetition, or moving speech between segments.

## 5. Check
`align_check.py source/cleaned.md work/lecture.ar.md --inferred work/inferred.md` (warns when a
garbled source spot has no `{{…}}`; writes the table «heard → completed» for the doubts file) and
`term_check.py source/cleaned.md work/lecture.ar.md` — same handling as for books.

## 6. Assemble and export
- **Internal Markdown assembly:** `python -X utf8 S/assemble_book.py single work/lecture.ar.md --kind lecture --meta meta.json --title-ar "…" --topics "…" --out-dir work/assembled --doubts uncertain.md work/inferred.md`
  → a visible title and source details, topic headings, and preserved paragraph breaks;
  timed section headings retain `[hh:mm:ss]`. Export: `python -X utf8 S/export_reading.py "work/assembled/<name>.md" --out-dir النهائي --doubts "work/assembled/<name> – مواضع الشك.md"` (see `reading-output.md`). Inspect the assembled Markdown itself before
  delivery: title, paragraphs, question/answer separation, and section headings must survive.
- **srt:** `python -X utf8 S/captions.py build-srt work/lecture.ar.md --out "النهائي/<التاريخ العنوان>.srt"`
  → no full stop at the end of a subtitle line (user rule; ؟ ! … and commas stay),
  max 36 characters × 2 lines per cue, split at clause boundaries (after ، . ؟ or before a dash),
  timing shared inside each sentence segment; it flags cues that start with punctuation or end on a
  dangling word (من، إلى، لم، بل، أن…) — fix the translation, never ship them. RLM at line
  starts, UTF-8 BOM. Translator notes are kept out of subtitles, and `{{…}}` text is shown in yellow (`--inferred-color`). If full wording makes cues too
  dense to read, tell the user — do not condense.

**Arabic colour runs:** keep adjacent inferred words inside one colour tag per subtitle line;
per-word colour tags can reverse Arabic word runs in legacy players. A standalone SRT cannot
set the player's global bidi renderer. Mixed-colour lines need an RTL-aware renderer; keep
`Encoding=-1` when burning with libass. Inspect a mixed white/yellow cue with a multiword
yellow phrase, not only all-white sample frames. Never reverse the stored Arabic to compensate.

- **video with the subtitles burned in** (when the user wants the video; download it with the
  original Russian audio as in §1): `python -X utf8 S/embed_subtitles.py "النهائي/<name>.mp4" "النهائي/<name>.srt" --out-dir النهائي`
  → «<name> – ترجمة مدمجة.mp4» (Readex Pro Bold 19 on a translucent box, H.264 720p for
  phones/WhatsApp; re-encodes for a few minutes). Video deliverables are exactly three: the
  original video, the Arabic `.srt`, and the burned-in `.mp4` — no MKV. Inspect every frame in
  `النهائي/_frames/`: beginning/middle/end plus up to two mixed-colour samples selected
  automatically. Check any user-reported timestamp in the completed full MP4 too. Report a
  corrected video only after encoding finishes and these frames are checked; an SRT update
  alone is not a corrected MP4. Delete the frames folder after inspection. For the burned MP4,
  leave the external SRT disabled to avoid duplicate or incorrectly reordered overlay text.
