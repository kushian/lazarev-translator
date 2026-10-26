"""Lecture captions: clean YouTube/auto captions, keep timing, check edits, build Arabic SRT.

Usage:
  python captions.py clean INPUT.vtt|.srt --out SOURCE_DIR [--max-seg 40] [--gap 3.0]
      -> SOURCE_DIR/raw-segments.md   words exactly as captioned (rolling duplicates removed),
                                      grouped into whole-sentence timed segments <!-- s0001 00:00:01.000-00:00:14.500 -->
         SOURCE_DIR/cleaning-report.json
  python captions.py align PUNCTUATED.txt --words SOURCE_DIR/words.json --out SOURCE_DIR
      -> for captions WITHOUT punctuation: you write the whole lecture punctuated (same words,
         same order, speaker labels, logged fixes); this aligns it to the caption timings and
         writes whole-sentence cleaned.md + matching raw-segments.md for wordcheck.
  python captions.py wordcheck SOURCE_DIR/raw-segments.md SOURCE_DIR/cleaned.md [--max-change 0.02]
      -> compares the words of every segment (punctuation/case ignored). Every changed word must be
         logged in asr-fixes.md; fails if more than 2% of words changed overall.
  python captions.py build-srt TRANSLATED.md --out FILE.srt [--width 36]
      -> Arabic SRT (no full stop at line ends; --keep-periods to keep) from translated segments (same <!-- sNNNN start-end --> markers): text split into
         cues of max 2 lines, time shared by length, RLM at each line start, UTF-8 BOM, CRLF.
  python captions.py validate FILE.srt
  python captions.py quality INPUT.vtt|raw-segments.md [--report OUT.json]
      -> good / usable / poor: punctuation density, mid-sentence segments, odd fragments.
         Run it first: "poor" means propose Whisper (with cost) or ask for a transcript.
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path

from _common import die, read_json, read_text, write_json, write_text

TS = r"(\d{1,2}:)?\d{1,2}:\d{2}[.,]\d{3}"
CUE_LINE = re.compile(rf"^\s*({TS})\s*-->\s*({TS})")
TAG = re.compile(r"<[^>]+>")
SEG_MARK = re.compile(r"<!--\s*(s\d{4,6})\s+([\d:.,]+)-([\d:.,]+)\s*-->")
RLM = "‏"


def to_sec(ts: str) -> float:
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    parts = [0.0] * (3 - len(parts)) + [float(p) for p in parts]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def fmt(sec: float, srt: bool = False) -> str:
    sec = max(0.0, sec)
    h, rem = divmod(int(round(sec * 1000)), 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{',' if srt else '.'}{ms:03d}"


def parse_cues(text: str) -> list[tuple[float, float, str]]:
    cues, cur = [], None
    for line in text.replace("\r\n", "\n").split("\n"):
        m = CUE_LINE.match(line)
        if m:
            if cur:
                cues.append(cur)
            cur = [to_sec(m.group(1)), to_sec(m.group(3)), []]
            continue
        if cur is None:
            continue
        if not line.strip():
            cues.append(cur)
            cur = None
            continue
        if re.fullmatch(r"\d+", line.strip()):
            continue
        cur[2].append(TAG.sub("", line).strip())
    if cur:
        cues.append(cur)
    return [(s, e, " ".join(x for x in lines if x)) for s, e, lines in cues if any(lines)]


INLINE_TS = re.compile(r"<(\d{2}:\d{2}:\d{2}\.\d{3})>")


def parse_timed_words(text: str) -> list[tuple[float, float, str]] | None:
    """YouTube auto-captions carry a timestamp for every word (<00:00:01.240><c> word</c>).

    Each spoken cue shows the previous line, then a last line with only the NEW words and their
    times; the 10 ms "settled" cues repeat text and are skipped. Returns None for other files.
    """
    if not INLINE_TS.search(text):
        return None
    words: list[tuple[float, float, str]] = []
    cur = None
    blocks = []
    for line in text.replace("\r\n", "\n").split("\n"):
        m = CUE_LINE.match(line)
        if m:
            cur = [to_sec(m.group(1)), to_sec(m.group(3)), []]
            blocks.append(cur)
        elif cur is not None:
            cur[2].append(line)
    for start, end, lines in blocks:
        lines = [x for x in lines if x.strip()]
        if end - start < 0.05 or not lines:
            continue
        last = lines[-1]
        if len(lines) == 1 and words and not INLINE_TS.search(last):
            continue                                   # plain repeat of the previous line
        parts = INLINE_TS.split(last)                  # text, ts, text, ts, text ...
        times = [start] + [to_sec(x) for x in parts[1::2]]
        texts = parts[0::2]
        for k, chunk in enumerate(texts):
            toks = TAG.sub("", chunk).split()
            t0 = times[k]
            t1 = times[k + 1] if k + 1 < len(times) else end
            step = (t1 - t0) / max(1, len(toks))
            for n, w in enumerate(toks):
                words.append((t0 + n * step, t0 + (n + 1) * step, w))
    # the next word's start closes each word (a gap is silence, not speech)
    out = []
    for n, (s, e, w) in enumerate(words):
        nxt = words[n + 1][0] if n + 1 < len(words) else e
        out.append((s, max(s + 0.05, min(e, nxt)), w))
    return out or None

def cmd_clean(a):
    cues = parse_cues(read_text(a.input))
    if not cues:
        die("no cues found")
    words: list[tuple[float, float, str]] = []   # (start, end, word)
    raw_count = 0
    dup_cues = 0
    timed = parse_timed_words(read_text(a.input))
    if timed:
        words = timed                     # exact per-word times; no rolling duplicates in them
        raw_count = sum(len(x.split()) for _, _, x in cues)
    for start, end, text in ([] if timed else cues):
        toks = text.split()
        raw_count += len(toks)
        # rolling captions: the cue repeats the tail of what was already emitted
        k = 0
        emitted = [w for _, _, w in words[-60:]]
        for size in range(min(len(toks), len(emitted)), 0, -1):
            if emitted[-size:] == toks[:size]:
                k = size
                break
        if k == len(toks):
            dup_cues += 1
        new = toks[k:]
        # spread the cue's time over its new words, so two sentences in one cue get distinct times
        step = (end - start) / max(1, len(new))
        for j, w in enumerate(new):
            words.append((start + j * step, start + (j + 1) * step, w))
    # Segments are whole sentences (translation units), not caption fragments: YouTube cuts
    # every 2-3 s mid-sentence, and translating fragments breaks Arabic word order and leaves
    # cut-off subtitle lines. Close a segment at sentence end; a very long sentence is cut at
    # its last comma; a long real silence (> --gap s) also closes it.
    segs, cur = [], []
    sentence_end = re.compile(r"[.!?…»\"]$")
    for i, (t0, t1, w) in enumerate(words):
        if cur and t0 - cur[-1][1] > a.gap and len(cur) >= 4:
            segs.append(cur)
            cur = []
        cur.append((t0, t1, w))
        if sentence_end.search(w) and len(cur) >= 4:
            segs.append(cur)
            cur = []
        elif len(cur) >= a.max_seg:
            cut = max((j for j, (_, _, x) in enumerate(cur[:-3]) if x.endswith((",", ";", ":", "—"))), default=None)
            if cut is not None and cut >= 8:
                segs.append(cur[:cut + 1])
                cur = cur[cut + 1:]
            else:
                segs.append(cur)
                cur = []
    if cur:
        if segs and len(cur) < 4:
            segs[-1].extend(cur)
        else:
            segs.append(cur)
    out = Path(a.out)
    lines = []
    for n, seg in enumerate(segs, 1):
        start = seg[0][0]
        end = segs[n][0][0] if n < len(segs) else cues[-1][1]
        lines.append(f"<!-- s{n:04d} {fmt(start)}-{fmt(end)} -->\n" + " ".join(w for _, _, w in seg))
    write_text(out / "raw-segments.md", "\n\n".join(lines) + "\n")
    rep = {"cues": len(cues), "caption_words": raw_count, "kept_words": len(words),
           "word_times": "per-word (caption timestamps)" if timed else "spread inside each cue",
           "rolling_duplicate_cues": dup_cues, "segments": len(segs),
           "duration": fmt(cues[-1][1])}
    write_json(out / "cleaning-report.json", rep)
    write_json(out / "words.json", [[round(s, 3), round(e, 3), w] for s, e, w in words])
    print(f"ok: {len(cues)} cues, {raw_count} caption words -> {len(words)} words after removing rolling "
          f"duplicates, {len(segs)} segments -> {out / 'raw-segments.md'}")


def _norm_word(w: str) -> str:
    return re.sub(r"[^\w-]", "", w.lower().replace("ё", "е")).strip("-")


def cmd_align(a):
    """Unpunctuated auto-captions: align a punctuated rebuild to the caption word timings.

    The punctuated file is the whole lecture in Russian with punctuation, capitals, speaker
    labels (**Ведущий:**), logged word fixes and [неразборчиво: …] — no words moved or removed.
    Output: cleaned.md split into whole-sentence timed segments, and raw-segments.md with the
    original caption words regrouped into the same segments (so `wordcheck` can audit edits).
    """
    words = read_json(a.words)
    raw = [w for _, _, w in words]
    text = read_text(a.punctuated).replace("\r\n", "\n")
    toks = re.findall(r"\*\*[^*]+\*\*|\[неразборчиво:[^\]]*\]|\S+", text)
    # match word by word: a [неразборчиво: a b c] token contributes its words a, b, c, so a sentence
    # that starts with garble still starts at its own first caption word
    flat, owner = [], []
    for j, tk in enumerate(toks):
        if tk.startswith("**"):
            continue                              # label: not speech
        inner = tk.split(":", 1)[1] if tk.startswith("[неразборчиво:") else tk
        for w in inner.split():
            if _norm_word(w):
                flat.append(_norm_word(w))
                owner.append(j)
    has_words = set(owner)
    norm_p = ["x" if j in has_words else "" for j in range(len(toks))]
    norm_r = [_norm_word(w) for w in raw]
    sm = difflib.SequenceMatcher(a=norm_r, b=flat, autojunk=False)
    p2r = {}
    matched = 0
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            p2r.setdefault(owner[blk.b + k], blk.a + k)   # first matched caption word of the token
            matched += 1
    if matched < 0.9 * len(raw):
        die(f"only {matched}/{len(raw)} caption words found in the punctuated text — words were moved or dropped")
    # sentence segments over punctuated tokens
    segs, cur = [], []
    end_rx = re.compile(r"[.!?…]+[»\")]*$")
    for i, tk in enumerate(toks):
        if tk.startswith("**") and cur:
            segs.append(cur)
            cur = []
        cur.append(i)
        words_in = sum(1 for j in cur if norm_p[j])
        if end_rx.search(tk) and words_in >= 3:
            segs.append(cur)
            cur = []
        elif words_in >= a.max_seg and tk.endswith((",", ";", ":", "—")):
            segs.append(cur)
            cur = []
    if cur:
        segs.append(cur)
    # raw index where each segment starts (first matched token), monotonic
    starts = []
    last = 0
    for sg in segs:
        r = next((p2r[j] for j in sg if j in p2r), None)
        r = last if r is None else max(r, last)
        starts.append(r)
        last = r
    starts[0] = 0
    out = Path(a.out)
    clean_lines, raw_lines = [], []
    for n, sg in enumerate(segs):
        r0 = starts[n]
        r1 = starts[n + 1] if n + 1 < len(segs) else len(raw)
        t0 = words[min(r0, len(words) - 1)][0]
        t1 = words[r1][0] if r1 < len(words) else words[-1][1]
        if t1 <= t0:
            t1 = t0 + 0.5
        mark = f"<!-- s{n + 1:04d} {fmt(t0)}-{fmt(t1)} -->"
        clean_lines.append(mark + "\n" + " ".join(toks[j] for j in sg))
        raw_lines.append(mark + "\n" + " ".join(raw[r0:r1]))
    write_text(out / "cleaned.md", "\n\n".join(clean_lines) + "\n")
    write_text(out / "raw-segments.md", "\n\n".join(raw_lines) + "\n")
    print(f"ok: {len(segs)} sentence segments, {matched}/{len(raw)} caption words aligned "
          f"-> {out / 'cleaned.md'} (+ regrouped raw-segments.md for wordcheck)")


def _seg_words(text: str) -> dict[str, list[str]]:
    res = {}
    parts = re.split(r"<!--\s*(s\d{4,6})[^>]*-->", text)
    for i in range(1, len(parts), 2):
        body = re.sub(r"(?m)^\s*#{1,6}\s.*$", " ", parts[i + 1])  # topic headings are layout, not speech
        body = body.replace("¶", " ")
        body = re.sub(r"\[غير واضح[^\]]*\]", " ", body)
        body = re.sub(r"\*\*[^*]+:\*\*|\*\*[^*]+\*\*:", " ", body)  # speaker labels (**Лазарев:** / **Лазарев**:)
        body = re.sub(r"\[неразборчиво:", " ", body)  # marker word; its content stays
        toks = re.findall(r"[\wёЁ'-]+", body.lower().replace("ё", "е"))
        res[parts[i]] = [t for t in toks if t.strip("-")]  # a bare dash is punctuation
    return res


def cmd_wordcheck(a):
    raw = _seg_words(read_text(a.raw))
    new = _seg_words(read_text(a.cleaned))
    missing = [s for s in raw if s not in new]
    total = sum(len(v) for v in raw.values()) or 1
    changed = 0
    report = []
    for sid, rw in raw.items():
        nw = new.get(sid, [])
        sm = difflib.SequenceMatcher(a=rw, b=nw, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != "equal":
                changed += max(i2 - i1, j2 - j1)
                report.append({"segment": sid, "op": op, "raw": " ".join(rw[i1:i2]), "new": " ".join(nw[j1:j2])})
    frac = changed / total
    write_json(Path(a.cleaned).with_suffix(".wordcheck.json"),
               {"total_words": total, "changed_words": changed, "fraction": round(frac, 4),
                "missing_segments": missing, "changes": report})
    ok = not missing and frac <= a.max_change
    print(f"{'ok' if ok else 'FAIL'}: {changed}/{total} words changed ({frac:.1%}), "
          f"{len(missing)} segments missing. Every change must be in asr-fixes.md.")
    for r in report[:30]:
        print(f"  {r['segment']} {r['op']}: «{r['raw']}» -> «{r['new']}»")
    sys.exit(0 if ok else 1)


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


CLAUSE = re.compile(r"(?<=[،,.؛;:؟?!…])\s+|\s+(?=[–—]\s)")


def _cues_for(body: str, width: int) -> list[list[str]]:
    """Split one sentence-segment into readable cues of at most 2 lines.

    Prefer clause boundaries (after ، . ؟ ! ؛ : or before a dash); only a clause longer than
    two lines is wrapped mid-clause. Never start a cue with punctuation, never leave a tiny tail.
    """
    clauses = [c.strip() for c in CLAUSE.split(body) if c and c.strip()]
    cues: list[list[str]] = []
    cur = ""
    for c in clauses:
        trial = (cur + " " + c).strip()
        if len(_wrap(trial, width)) <= 2:
            cur = trial
            continue
        if cur:
            cues.append(_wrap(cur, width))
        lines = _wrap(c, width)
        while len(lines) > 2:
            cues.append(lines[:2])
            lines = lines[2:]
        cur = " ".join(lines)
    if cur:
        cues.append(_wrap(cur, width))
    if len(cues) > 1 and len(" ".join(cues[-1])) < 18:
        merged = _wrap(" ".join(cues[-2]) + " " + " ".join(cues[-1]), width)
        if len(merged) <= 2:            # attach a tiny tail only if the cue stays 2 lines
            cues[-2:] = [merged]
    return cues


def cmd_build(a):
    text = read_text(a.translated)
    parts = SEG_MARK.split(text)
    if len(parts) < 4:
        die("no <!-- sNNNN start-end --> markers in the translated file")
    segs = []
    for i in range(1, len(parts), 4):
        start, end = to_sec(parts[i + 1]), to_sec(parts[i + 2])
        body = re.sub(r"<!--.*?-->", "", parts[i + 3])
        body = re.sub(r"^\s*#{1,6} .*$", "", body, flags=re.M)  # section headings are not speech
        body = body.replace("¶", "")  # paragraph-start marks are layout, not speech
        # translator notes stay out of timed speech (a note may itself contain one level of brackets)
        body = re.sub(r"\s*\((?:[^()]|\([^()]*\))*من المترجم\)", "", body)
        # garble never reaches the screen: an old «[غير واضح: …]» becomes a coloured «…»
        body = re.sub(r"\[غير واضح(?::[^\]]*)?\]", "{{…}}", body)
        # Mark inferred words internally before wrapping; _colour_line groups adjacent
        # marked words into a single colour tag AFTER line breaks are chosen.
        body = re.sub(r"\{\{(.+?)\}\}", lambda m: " ".join(INF_MARK + w for w in m.group(1).split()), body)
        body = re.sub(r"\s+", " ", body.replace("**", "")).strip()
        body = re.sub(r"\s+([،.؛:؟!])", r"\1", body)
        if body:
            segs.append([start, end, body])
    # a segment too short to read (a false start «وكنت…» of half a second) joins the next one on
    # screen; the reading text keeps it as it is
    merged = []
    for k, sg in enumerate(segs):
        if merged and merged[-1][1] - merged[-1][0] < 0.7 and merged[-1][2].endswith("…"):
            prev = merged.pop()
            sg = [prev[0], sg[1], prev[2] + " " + sg[2]]
        merged.append(sg)
    cues = []
    for start, end, body in merged:
        groups = _cues_for(body, a.width)
        # time shared by length inside the segment; each cue at least 1.2 s when possible
        total = sum(len(" ".join(g)) for g in groups) or 1
        span = max(end - start, 0.5)
        t = start
        roomy = span >= 1.2 * len(groups)   # enough time to give every cue at least 1.2 s
        for k, g in enumerate(groups):
            dur = span * len(" ".join(g)) / total
            if k == len(groups) - 1:
                e = end
            elif roomy:
                left = len(groups) - k - 1
                e = min(t + max(dur, 1.2), end - 1.2 * left)
            else:
                e = t + dur
            cues.append((t, e, g))
            t = e
    out_lines = []
    for n, (s, e, g) in enumerate(cues, 1):
        if e <= s:
            e = s + 1.0
        if not a.keep_periods:   # user rule: no full stop at the end of a subtitle line
            g = [x[:-1].rstrip() if x.endswith(".") and not x.endswith("..") else x for x in g]
        g = [_colour_line(x, a.inferred_color) for x in g]
        out_lines += [str(n), f"{fmt(s, True)} --> {fmt(e, True)}", *[RLM + x for x in g], ""]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\r\n".join(out_lines), encoding="utf-8-sig", newline="")
    print(f"ok: {len(cues)} Arabic cues -> {a.out}")
    _validate(Path(a.out))


INF_MARK = "\ue000"   # private-use char marking a word completed from context

def _colour_line(text: str, colour: str) -> str:
    # Keep adjacent inferred words in ONE styled run per line. Separate colour tags
    # reverse word runs in legacy Arabic subtitle renderers. Mixed-colour placement
    # still needs an RTL-aware renderer (embed_subtitles uses Encoding=-1).
    pattern = INF_MARK + r"\S+(?:[ \t]+" + INF_MARK + r"\S+)*"
    return re.sub(pattern, lambda m: '<font color="' + colour + '">' +
                  m.group(0).replace(INF_MARK, "") + '</font>', text)



COMPLETE_ENDING = re.compile(r"(حد|حدّ|شيء|نوعاً|نوعا|يوماً|يوما|جانب|وقت|مكان|بطريقة|بشكل|حلم|أمر|سبب|شخص|موقف)\s+ما$|(نعم|أم|إما|وإما)\s+لا$")  # «إلى حدّ ما» is complete
DANGLING = re.compile(r"(?:^|\s)(من|إلى|الى|في|على|عن|لم|لن|أن|ان|إنَّ|أنَّ|بل|و|ف|لا|ما|التي|الذي|الذين|حين|كي|لكي|مع|بين)$")


def _validate(path: Path) -> None:
    cues = parse_cues(path.read_text(encoding="utf-8-sig"))
    problems = []
    prev_end = 0.0
    for n, (s, e, t) in enumerate(cues, 1):
        if e <= s:
            problems.append(f"cue {n}: end <= start")
        if s < prev_end - 0.001:
            problems.append(f"cue {n}: overlaps previous")
        if e - s < 0.7:
            problems.append(f"cue {n}: shorter than 0.7 s")
        txt = t.replace("\u200f", "").strip()
        if re.match(r"[،,.؛:؟!]", txt):
            problems.append(f"cue {n}: starts with punctuation «{txt[:20]}»")
        if DANGLING.search(txt) and not COMPLETE_ENDING.search(txt):
            problems.append(f"cue {n}: ends on a dangling word «{txt[-25:]}» (sentence cut)")
        prev_end = e
    print(f"{'ok' if not problems else 'WARN'}: {len(cues)} cues validated" + ("" if not problems else f", {len(problems)} problems"))
    for p in problems[:20]:
        print("  " + p)


RU_SHORT_OK = set("а б в во да до же за и из к ко ли на не ни но о об от по с со то у уж я ты он мы вы их ей им ее её мне нас вас тот там тут как так что кто где чем вот ну бы же ли нет да все всё это эти".split())


def cmd_quality(a):
    """Is this auto-transcript good enough to translate from, or should Whisper be proposed?"""
    text = read_text(a.input)
    if re.search(CUE_LINE.pattern, text, re.M):  # raw .vtt/.srt: drop rolling repeats first, as `clean` does
        kept: list[str] = []
        for _, _, cue in parse_cues(text):
            toks = cue.split()
            k = next((s for s in range(min(len(toks), len(kept[-60:])), 0, -1) if kept[-s:] == toks[:s]), 0)
            kept.extend(toks[k:])
        text = " ".join(kept)
    bodies = [b for b in re.split(r"<!--[^>]*-->", text) if b.strip()] or [text]
    body = "\n".join(bodies)
    words = re.findall(r"[А-Яа-яЁёA-Za-z]+(?:-[А-Яа-яЁё]+)?", body)
    n = max(1, len(words))
    ends = len(re.findall(r"[.!?…]", body))
    commas = body.count(",")
    caps_after_end = len(re.findall(r"[.!?…]\s+[А-ЯЁA-Z]", body))
    seg_mid = sum(1 for b in bodies if not re.search(r"[.!?…»\"]\s*$", b.strip())) / max(1, len(bodies))
    # broken-looking tokens: odd short fragments, Latin inside Russian, glued/uncommon fragments
    odd = [w for w in words if (len(w) <= 2 and w.lower() not in RU_SHORT_OK)
           or (re.search(r"[A-Za-z]", w) and re.search(r"[А-Яа-яЁё]", w))]
    music = len(re.findall(r"\[(?:музыка|аплодисменты|смех|music|applause)\]", body, re.I))
    m = {"words": len(words), "sentence_marks_per_100_words": round(100 * ends / n, 1),
         "commas_per_100_words": round(100 * commas / n, 1),
         "capital_after_sentence_end": round(caps_after_end / max(1, ends), 2),
         "segments_ending_mid_sentence": round(seg_mid, 2),
         "odd_fragments_per_1000_words": round(1000 * len(odd) / n, 1),
         "odd_examples": sorted(set(odd))[:15], "non_speech_tags": music}
    punctuated = m["sentence_marks_per_100_words"] >= 3 and m["commas_per_100_words"] >= 2
    if punctuated and m["odd_fragments_per_1000_words"] <= 8:
        verdict, advice = "good", "translate from these captions (rebuild + log fixes as usual)"
    elif punctuated:
        verdict, advice = "usable", "usable, but expect many [غير واضح]: offer Whisper to the user (cost first)"
    else:
        verdict, advice = "poor", ("no punctuation: sentences must be rebuilt by hand and errors will be frequent — "
                                   "propose Whisper on the ORIGINAL Russian audio, or ask the user for a transcript")
    m.update({"verdict": verdict, "advice": advice})
    if a.report:
        write_json(a.report, m)
    print(f"{verdict}: {m['words']} words, {m['sentence_marks_per_100_words']} sentence marks/100 words, "
          f"{m['commas_per_100_words']} commas/100, {m['odd_fragments_per_1000_words']} odd fragments/1000, "
          f"{int(100 * m['segments_ending_mid_sentence'])}% segments end mid-sentence")
    print("  advice: " + advice)
    if m["odd_examples"]:
        print("  odd fragments: " + ", ".join(m["odd_examples"]))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("quality")
    p.add_argument("input", help="raw .vtt/.srt or raw-segments.md")
    p.add_argument("--report")
    p = sub.add_parser("clean")
    p.add_argument("input")
    p.add_argument("--out", required=True)
    p.add_argument("--max-seg", type=int, default=40)
    p.add_argument("--gap", type=float, default=3.0)
    p = sub.add_parser("align")
    p.add_argument("punctuated")
    p.add_argument("--words", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--max-seg", type=int, default=40)
    p = sub.add_parser("wordcheck")
    p.add_argument("raw")
    p.add_argument("cleaned")
    p.add_argument("--max-change", type=float, default=0.02)
    p = sub.add_parser("build-srt")
    p.add_argument("translated")
    p.add_argument("--out", required=True)
    p.add_argument("--width", type=int, default=36)
    p.add_argument("--keep-periods", action="store_true", help="keep the full stop at line ends")
    p.add_argument("--inferred-color", default="#FFC857",
                   help="colour of {{…}} text; standalone players need RTL-aware mixed-colour rendering")
    p = sub.add_parser("validate")
    p.add_argument("srt")
    a = ap.parse_args()
    if a.cmd == "quality":
        cmd_quality(a)
    elif a.cmd == "clean":
        cmd_clean(a)
    elif a.cmd == "align":
        cmd_align(a)
    elif a.cmd == "wordcheck":
        cmd_wordcheck(a)
    elif a.cmd == "build-srt":
        cmd_build(a)
    else:
        _validate(Path(a.srt))


if __name__ == "__main__":
    main()
