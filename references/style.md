# Sablabal's style — how the Arabic should read

Source of these rules: a study of four Lazarev books in M. Sablabal's Arabic translation
(«تشخيص الكارما 1»، «تشخيص الكارما 3 – الحب»، «شفاء النفس»، «التغلّب على التكبّر»).
Terminology lives in `glossary.tsv`; this file is about voice, syntax and layout.

## Contents
1. Authority and fidelity
2. Register
3. Syntax that follows the Russian (conditional, never mechanical)
4. Connectors and recurring phrasing
5. Dialogue, letters, quotations
6. Translator's notes «(… . من المترجم)»
7. Names, titles, numbers
8. Religion: God, Bible, other faiths
9. What not to copy
10. Markdown conventions

## 1. Authority and fidelity
- Sablabal's choices win over the user's, over other translators', and over your taste.
  Where he has no attested choice, decide in his spirit and log it (see `quality.md`).
- Translate **everything**: every sentence, repetition, aside, list item, footnote, epigraph,
  reader letter, signature. No summarizing, no smoothing away of awkward or extreme claims,
  no added disclaimers. Lazarev's medical and religious claims are rendered exactly, with his
  own hedges and certainty — nothing stronger, nothing weaker.
- For authored books and articles, keep the author's paragraphing one-to-one and preserve
  emphasis. Automatic transcript line breaks are caption fragments, not authored paragraphs;
  rebuild lecture paragraphs by meaning as described in §11.
- Keep negation, modality (может / должен / нужно), causality (поэтому / потому что) and who
  does what to whom. These are where fluent translations silently go wrong.

## 2. Register
Formal, modern standard Arabic, reflective and sermon-like in exposition; plainer and closer
to speech in dialogues and readers' letters. Selective vowel marks only where a word would be
ambiguous («الصِحَّة»، «الوِحدة»، «تُقَدَّر») — never full vocalization.

## 3. Syntax that follows the Russian — only where the Russian has it
Sablabal's Arabic keeps the shape of Lazarev's Russian. Reproduce these features **when the
source sentence has the matching feature**; do not inject them elsewhere.

| Russian feature | Sablabal does | Example |
|---|---|---|
| list without «и» | comma list without «و» | «الحقدُ، الزعلُ، الخوف، الاكتئاب» |
| list or pair with «и» | keeps «و» | «الصفح والتوبة» |
| «X — это Y» | usually **هو/هي**, sometimes a dash | «الصفحُ هو امتناعٌ…»؛ «الإنسان – منظومة معلوماتية-طاقية» |
| dash before a conclusion | keeps the dash | «توجد عدائية، تُزال العدائية – يزول المرض» |
| inverted «— ответил я» | pronoun after the verb | «- طبعاً، - أُجيب أنا.» |
| explicit «я / он» before a verb | pronoun before the verb | «أنا سأحاول…»، «هو يتعلّق بي» |
| present-tense narration | present tense | «تتصل إحدى معارفي… فأشرح لها…» |
| «свой» standing alone (свою судьбу) | **الخاص** once (≈190×), rarely خاصته | «تحسين المصير الخاص» |
| «свой» on several nouns in a row | a possessive suffix, **not** الخاص on each | «ترتيب نفسه، مصيره وصحَّته» (شفاء النفس ص7) — never «النفس الخاصة، والمصير الخاص والصحة الخاصة» |
| «собственный / родной / своего же» emphasis | natural Arabic emphasis | «قتل أخاه» / «قتل أخاه نفسه» — not «شقيقه بالذات» |
| compound adjectives | hyphenated | «معلوماتية-طاقية»، «المكانية-الزمانية» |

Late books («شفاء النفس»، «التغلّب على التكبّر») have fewer calques than the early
«تشخيص الكارما 1/3». Follow the source in front of you.

**The limit of calquing.** Sablabal keeps Russian *sentence shapes*, not Russian *word-by-word
mechanics*. A calque is right only if an Arabic reader would accept it in his books. Typical
over-literal slips to avoid: «فقط» for всего («всего 10–15 лет» → «بعد 10–15 سنة»), passive
«يُعطى لي» for «дано мне» when an active form reads better («بِمَ استحققتُ كل هذا؟»), «بالذات» for
every «именно/же», repeating الخاص, translating every «вот/же/ведь» particle in written text
(lectures are different: spoken particles are kept). When in doubt, reread the gold sentence
patterns in §4 and choose the shape Sablabal would print.

**Word order inside the sentence is Arabic, always.** Keeping a Russian *sentence shape* (dash,
comma list) never means keeping Russian *word positions*. Russian puts adverbs and qualifiers
where Arabic cannot; move them. Read every sentence once as Arabic only and fix any order a
native reader would stumble on. User-reported examples:

| Calqued order (wrong) | Natural Arabic |
|---|---|
| يصلون إلى البيت بالكاد أحياء (домой приходят едва живые) | **بالكاد** يصلون إلى البيت أحياء |

Fix word order **only where the Arabic is unclear or unnatural** (user rule). A sentence that
already reads clearly is left as it is — do not polish for its own sake. Approved by the user as
fine: «وهذا كافٍ لحرمانه من الترقية»، «يفكر الغرب بالنصف الأيسر من الدماغ: تفكيراً عينياً، محدّداً، منفصلاً».

Rules of thumb: «بالكاد / تقريباً / فقط / أيضاً / مجدداً» go next to the word they modify, usually
before the verb; time and place phrases follow the verb and its object, not the Russian slot;
a long Russian subject at the head of a sentence often reads better after the verb (VSO) in
narration; never split an إضافة or a verb from its preposition across a clause just because the
Russian did.

**Translate whole sentences, never caption fragments.** For timed lectures the cleaning step
gives one segment per sentence. Keep each Arabic sentence whole inside one segment: if a
sentence still straddles two segments, put the whole Arabic sentence in the segment where most
of it is spoken. Never leave «بل» or «لماذا لم تحمِ التقاليدُ» dangling at a segment end, and never
start a segment with «.» or «،». `captions.py build-srt` flags such cues.

## 4. Connectors and recurring phrasing
«لكن» (not «ولكن»)، «لدى»، «كونَ…» for поскольку/так как، «إلا أنَّ»، «من الضروري» / «يجب» for
нужно/необходимо، «إضافة لذلك» (Кроме того)، «بهذه الطريقة» (Таким образом)، «في الواقع»
(На самом деле / Дело в том)، «في جوهر الأمر» (по сути)، «كقاعدة عامة» (как правило)،
«في الوقت عينه» (в то же время)، «في المقام الأول / بالدرجة الأولى»، «حينها»، «إنما» (а / но)،
«فحسب… إنما…» (не только… но и)، «كلما… ازداد/اشتدّ…» (чем… тем)، «وإلى آخره» (и т. д.)،
«على فكرة» (кстати)، «مُجملاً / عموماً»، «تحديداً»، «مؤخراً»، «مجدداً».
Proverbs: literal with a label — «كما تقول الأمثولة الروسية: "…"». Idiomatic headings may be
naturalized: «Разговор по душам» → «حديثٌ من القلب إلى القلب».

## 5. Dialogue, letters, quotations
- **Dialogue** (Lazarev's consultations, phone calls): one line per speaker turn, opened with an
  en dash and a space «– », the speech tag set off by « – »:
  `– طبعاً، – أُجيب أنا. – كلما ازداد تعلّق الشخص، اشتدّت عدائيته.`
  (Never start a Markdown line with "- ": it renders as a bullet list.)
  Usual tags: أشرح، أُجيب، أُتابع، أشرتُ، تسأل هي، يعترف هو، تشاركت هي.
- **Readers' letters and the author's answers** (books and lazarev.ru):
  heading «الرسالة رقم 1» (or the post's own label), the letter as `> ` blockquote paragraphs
  keeping the writer's voice — emotion, apologies in brackets, colloquial flow — then the answer
  under «إجابتي». Greeting as in the source: «مرحبا، سيرغيي نيكولايفيتش».
- **Epigraphs and long quotations**: `> ` blockquote.

## 6. Translator's notes «(… . من المترجم)»
Inline, in round brackets, ending exactly with «. من المترجم)». Use them sparingly, only to:
- explain a transliterated Russian word or wordplay: «"تشايات" (هذه كلمة روسية. من المترجم)»;
- give the standard Arabic Bible wording when Lazarev quotes a verse in his own phrasing:
  «(في الترجمة العربية للإنجيل – "طوبى للجياع والعطاش إلى البر". من المترجم)»;
- offer the second sense of a word Sablabal renders two ways: «(أو "الطبقات". من المترجم)»;
- clarify what «في الداخل» etc. means: «(المقصود ب"في الداخل" – في النفس، بالمشاعر. من المترجم)».
Never use a note to comment on, correct, praise or warn about the author's ideas.
Notes do not name any translator. Do not add a translator's preface, and never reproduce
Sablabal's own preface, Lazarev's thanks to him, or the 2019 legal statement — translate only
what is in the source.

## 7. Names, titles, numbers
- Author: «سيرغيي نيكولايفيتش لازاريف»، short form «س. ن. لازاريف».
- Russian names: transliterate, keep name + patronymic, put place names and less-known proper
  names in quotes on first mention: «جادة "نيفسكيي"»، «"ي. ب. بلافاتسكايا"».
  Transliteration habits: й/ий → ي/يي (سيرغيي)، ж → ج، ч → تش، щ → شتش، х → خ، ы → ي، ц → تس.
- Titles of Lazarev's books: use the Arabic titles in `works.md`; other titles in «» or "".
- Digits: Western (1995, 40, 3–4 ساعات), as Sablabal writes them.
- Ages and dates as written: «عمري 37 سنة»، «في ال29 من حزيران».

## 8. Religion
- Бог / Господь / Творец → **الله / الخالق / العليّ**. «الإله» only for pagan gods
  («الإله إندرا») and inside Bible quotations («الرب الإله»).
- Bible: «الكتاب المقدس»، «العهد القديم/الجديد»، «الإنجيل/الأناجيل»، «موعظة الجبل»،
  «الطوبيات»، «الوصايا». Quote the standard Arabic (Van Dyck) wording only when you are sure
  which verse it is; otherwise translate Lazarev's wording and, if useful, add a note.
- Christian terms stay Christian (الخوري، القربان، التعميد، الدير، القديس). Do not islamize them,
  and do not import Islamic notions the source does not contain (الجن، المسّ، الرقية الشرعية).
  Exception attested in Sablabal: folk charms (заговоры) → «الرقية».

## 9. What not to copy
Sablabal's typos and agreement slips are not style: «أستقبلتُ» (→ استقبلتُ)، «بإسمي» (→ باسمي)،
«إذا» meaning «إذن»، «الخطئية»، masculine plural for abstract nouns («الزعل… لا يشكلون»).
Write correct Arabic with his vocabulary and his sentence shapes.

## 10. Markdown conventions
- Keep every `<!-- p0001 -->` / `<!-- s0001 … -->` marker exactly, one per block, in order.
- Headings: `#` book/part, `##` chapter, `###` section — same level as the source.
- Section separator `***` on its own line.
- Footnotes: keep `[^n]` markers and translate the definitions at the end.


## 11. Lecture reading layout
- Deliver a readable chapter: one `#` title on its own line, `##` headings at real topic changes,
  and `###` for a question or a narrower subsection when useful. Added topic headings must be
  neutral descriptions of the following material, not new claims or summaries replacing speech.
- Keep one developed idea per paragraph, usually 2–5 sentences. Split a long paragraph at a
  natural sentence boundary; do not turn every sentence into an isolated paragraph.
- Put each question on its own line or paragraph, preferably bold, followed by a blank line
  and its answer. Keep the full spoken question and any spoken introductions.
- Separate headings and paragraphs with blank lines. Keep dialogue turns, quoted passages,
  and non-speech cues such as `[موسيقى]` visibly distinct from running prose.
- **Timed captions (YouTube/srt/vtt): mark paragraph starts with `¶ `.** Caption segments are
  2–5 s fragments. Keep one Arabic block per segment (needed for checks and SRT) and begin a
  segment's text with `¶ ` where a new paragraph starts. On assembly, segments join into running
  prose until the next `¶`, heading, speaker label, quotation or cue; `¶` is removed and never
  reaches the SRT. Put a heading at a sentence start: if the topic changes mid-segment, split the
  segment's block with a blank line and put the heading after the sentence that ends there.
- Preserve the complete wording, repetitions, order, and alignment markers. Multiple paragraphs
  and topic headings may occur inside one source segment; never merge paragraphs just because
  they share a segment marker. Books with authored headings retain their original hierarchy.
- After assembly, inspect the beginning, a middle question/answer, and the ending. Confirm
  headings remain headings, answers start separately, paragraph breaks survive, and no title
  is joined to the opening text. Alignment/terminology checks do not establish layout quality.

Final reading layout: use the approved Readex Pro Light/Bold typography, comfortable spacing, and matching A4 HTML/PDF sheets in `reading-output.md`.
