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
   **Smoothing has limits (user review, 2026-11-24)** — the read-through fixes the Arabic, never the
   content. **Three things never change while smoothing: who does what (the subject and the object),
   the negation, and the number of ideas.** If a sentence cannot be made smoother without changing one
   of them, it stays as it was. Every error in `known-errors.md` broke one of these three. Found in a
   re-translated lecture:
   - **It drops no spoken words.** Repetitions, «опять же» (مرة أخرى), «так сказать» (إن صحّ القول),
     «вот», a restarted «сказать, что…» and a short «что она» stay in the Arabic, rendered as speech
     (SKILL.md rule 2; lecture workflow §4). Making a sentence shorter than the source is a loss.
   - **It completes nothing without `{{…}}`.** A sentence the speaker leaves unfinished stays
     unfinished («…»), or its completion is coloured: «إذا أردنا أن نحدد شيئاً، {{أن نكون حذرين}}» —
     never plain «أن نكون حذرين», which the reader takes as the author's words.
   - **It keeps the established word.** «унижение» stays «الإذلال», as in Sablabal's «إذلال الذات»
     for самоуничижение (not «التحقير»); a smoother synonym is not a reason to change a term.
   - **Check every rewritten sentence against the source, clause by clause:** each Russian clause has
     its Arabic, nothing is added, and negation and «как / так же как» apply to the same words.
     «однозначного понятия, что ложь — это плохо, так же как [что] деньги — плохо, быть не может» →
     «لا يمكن الحكم قطعاً بأنَّ الكذب سيئ، كما لا يمكن الحكم بأنَّ المال سيئ» — not «كما لا يمكن أن
     يكون المال سيئاً», which moves the negation from the judgement to the money.
1. **Back-translation of every rewritten sentence (user rule, 2026-11-24).** Each sentence whose
   wording you changed in step 0, each sentence with `{{…}}`, every block flagged by the length check,
   and 2 random blocks: render the Arabic back into Russian **from the Arabic alone**, without looking
   at the source, then compare with the source on four points:
   - **Negation:** a «не / нет / ни» in one and not in the other («подражая ему» → «لم يقتدوا به» is wrong).
   - **Who does what:** the same subject asks, sees, gives, imitates. Ask «who does it?» for every verb
     («вы спрашиваете: "Кошелёк или жизнь?"» — *you* ask, not the man in the street).
   - **Condition and direction:** «если», «чтобы», «из / в», «начинает / перестаёт», «свои» (one's own)
     versus «его» keep their sense («входить в состояние» is not «выходить из него»).
   - **Number of ideas:** as many clauses and claims as the source, none added, none merged.
   Any difference is fixed before the block is saved or sent, then that block is read once more.
   Repetitions and stutters are compared too: «я, я, я думаю» is copied three times, not once
   and not four times (lecture workflow §4).
2. **Read the warnings, not just the count.** For each `missing` term warning, look at the source
   block: either the term is there in another legitimate form, or fix it.
3. **Doubts go to `uncertain.md`** in the project/post folder — never into the translation itself:
   block ID | Russian phrase | chosen Arabic | why uncertain. Inferred glossary terms
   (status `inferred`) are always logged when used. `assemble_book.py … --doubts uncertain.md`
   copies it next to the internal assembled Markdown as «<name> – مواضع الشك.md». Export a separate styled HTML notes file as specified in `reading-output.md`, so the translation stays clean.
   Write doubts in Arabic, for the user, and **never name any translator** (no «سبلبل»), neither in
   the doubts file nor in the translation: say «لا يوجد مقابل ثابت في المسرد» instead.

## Re-translating a text that was already translated
When an earlier translation of the same text is given (a re-run, or the user's corrected copy), it is
the starting point: **a sentence that was correct stays word for word**, and a sentence changes only
for a specific error you can name (a wrong term, a dropped clause, broken Arabic). «Smoother» is not
an error. Two reviewed regressions came from rewriting correct sentences: «قلّدوه» became
«لم يقتدوا به», and the asker in «المحفظة أم الحياة؟» was reversed (`known-errors.md`).

## Known errors: examples and the test after every skill change
`references/known-errors.md` lists errors found in reviewed translations: the Russian, the wrong
Arabic, the right Arabic, and the kind of error. Read it before a lecture or article. After any
change to this skill, translate the Russian of each entry again and check that none of the listed
errors comes back. Each new error found in a review is added there.

## Fixed renderings: never improvise these
- **Bible quotations** Lazarev quotes as verses: the common Arabic (Van Dyck) wording, as it is
  known: «плодитесь и размножайтесь» → «أثمروا واكثروا»; «Не нарушить пришёл Я, но исполнить» →
  «ما جئتُ لأنقض بل لأكمّل». Only when you are unsure which verse it is, follow style.md §8.
- **Church terms** from the glossary (religion topic), never a synonym that sounds better:
  «священник» is «الخوري» (plural «الخوارنة»), as Sablabal renders it, not «الكاهن» (user decision,
  2026-11-24).
- **Words the author contrasts on purpose** keep two different Arabic words in the whole text, even
  where the glossary has one: «корыстность» (natural self-interest, which he defends) and «корысть»
  (greed, «приоритет тела над душой») in «Ключ к помощи»: «المصلحة الذاتية» and «الطمع», never one
  word for both («تظهر المصلحة الذاتية فيما نسميه مصلحة ذاتية» is nonsense). Same idea as SKILL.md,
  «Two Russian words, one Arabic term».

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
