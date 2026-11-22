# Quality: what the checks prove, and what you must still do

The user reads Arabic only. They cannot catch an omission, a reversed negation or a wrong
term. These steps are the safety net; do them every time.

## Automatic (scripts)
| Check | Proves | Does not prove |
|---|---|---|
| `align_check.py` | every block present, in order; numbers, footnotes, questions kept; no wildly short/long block | that the meaning is right |
| `term_check.py` | Sablabal's terms used where the source has the concept; forbidden forms absent | that a synonym was wrong — warnings need judgement |
| `captions.py wordcheck` | lecture rebuild changed ≤ 2 % of words, all logged | that the captions were right |
| `assemble_book.py` variant scan | one spelling per name/term across the book | — |

## Manual, per chunk / post
0. **Arabic read-through — mandatory, before saving, sending or assembling any chunk or part.**
   The scripts only prove completeness; they cannot see a sentence an Arabic reader cannot follow.
   Read the chunk's Arabic alone, as an Arabic reader who has never seen the Russian, and fix each
   sentence that fails one of these questions:
   - **Is it a complete sentence?** A finished sentence has its main clause: «كنتُ قد تحدثتُ عن أنه
     لكي نتوجّه في العالم المحيط… عند تقييم أي حدث.» has no main verb. Find what the source says
     and write it whole. (An abandoned spoken sentence is different: lecture workflow §4.)
   - **Is the word order Arabic?** (style.md §3, «Word order inside the sentence is Arabic, always».)
   - **Is a Russian idiom or proverb copied word for word into nonsense?** (style.md §4.)
     «يطرح نفسه سؤال طبيعي» → «والسؤال الطبيعي هنا:»؛ «لا يُسقطكم من السرج» → «لا يزعزعكم».
   - **Does it contradict itself?** Often two different Russian words got the same Arabic term:
     «يتحوّل الاكتئاب إلى اكتئاب» (уныние, депрессия). See SKILL.md, «Two Russian words, one Arabic term».
   - **Does a sentence break across two blocks** so that neither half reads alone («والتعامل» /
     «معه باحترام»)? Keep it whole (style.md §3, «Translate whole sentences»).
   - **Are only Arabic words left?** No «[موسيقى]», «[يسعل]», English words or script status words
     («poor», «the source ends») in the text or in the doubts list; music marks are `♪`
     (lecture workflow §4), other sounds are left out or described in Arabic.
   Rewrite in Arabic inside the same block, keeping every piece of content, then check the
   rewritten sentence once against the source for meaning. A sentence that already reads clearly
   is left as it is (style.md §3). This pass is never skipped to save time or tokens.
1. **Back-translation spot check.** Take 2 random blocks plus every block flagged by the length
   check. Without looking at the source, render your Arabic back into Russian in your head, then
   compare with the source: negation, modality, who-does-what, numbers, causality, any dropped
   clause. Fix and move on.
2. **Read the warnings, not just the count.** For each `missing` term warning, look at the source
   block: either the term is there in another legitimate form, or fix it.
3. **Doubts go to `uncertain.md`** in the project/post folder — never into the translation itself:
   block ID | Russian phrase | chosen Arabic | why uncertain. Inferred glossary terms
   (status `inferred`) are always logged when used. `assemble_book.py … --doubts uncertain.md`
   copies it next to the internal assembled Markdown as «<name> – مواضع الشك.md». Export a separate styled HTML notes file as specified in `reading-output.md`, so the translation stays clean.
   Write doubts in Arabic, for the user, and **never name any translator** (no «سبلبل»), neither in
   the doubts file nor in the translation: say «لا يوجد مقابل ثابت في المسرد» instead.

## Deciding a term Sablabal never translated
1. `glossary.py --term <word>`; look for a related term in the glossary (same root, same field).
2. Choose the rendering that fits his system (e.g. field vocabulary stays «حقل/بنيات/طاقي»).
3. Record it in `book-glossary.tsv` (status `book`, evidence = your reasoning) so it stays stable.
4. Mention it to the user in the final report.
The core `glossary.tsv` is only changed deliberately (with evidence from a Sablabal text), never as a
side effect of one translation.

## User overrides
If the user insists on a rendering that differs from Sablabal's, say once (in Arabic) that
Sablabal uses X; if they still want theirs, add it to that project's `book-glossary.tsv` with
`note: user override` and use it consistently in that project only.

## Video colour direction
For requested video output, inspect the actual completed burned MP4 rather than infer success
from its SRT. Review all saved frames, including a mixed white/yellow cue with a multiword
inferred phrase when present, and any timestamp reported by the user. Separate SRT status
from encoding completion and visual review. These samples establish sampled display behaviour,
not full audio/transcript accuracy. Standalone SRT cannot force an old player's bidi settings;
keep `Encoding=-1` for burning, and do not reverse stored Arabic words to compensate.

## Reporting (Arabic)
State what was done and checked, what remains doubtful, where the files are. Never say the
translation is "verified accurate"; say it passed the completeness and terminology checks and
how many doubts are logged.

Final reading layout: use the approved Readex Pro Light/Bold typography, comfortable spacing, and matching A4 HTML/PDF sheets in `reading-output.md`.
