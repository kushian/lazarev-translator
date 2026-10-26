"""Burn the Arabic subtitles into the video picture (needs ffmpeg).

Usage:
  python embed_subtitles.py VIDEO.mp4 SUBS.srt --out-dir النهائي
                            [--height 720] [--crf 23] [--font-size 19] [--ffmpeg PATH]

Output: "<stem> – ترجمة مدمجة.mp4" — subtitles drawn into the picture with the skill's Readex Pro
Bold font, white text on a translucent dark box, H.264 + AAC, faststart: plays on any phone,
WhatsApp, Telegram. Re-encodes the video (a few minutes); --height 720 keeps files small.
The deliverable set for a video is: the original video (Russian audio), the Arabic .srt, and this
burned-in .mp4 (a separate MKV with a switchable track is not produced — user decision).
Checks with ffprobe that the duration matches; saves beginning/middle/end sample frames,
plus up to two mixed-colour samples when present, in النهائي/_frames/. Inspect every
saved frame before reporting completion, then delete the folder.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from _common import SKILL_DIR, die

FONTS = SKILL_DIR / "assets" / "fonts"


def find_tool(name: str, explicit: str | None) -> str:
    cands = [explicit] if explicit else []
    cands += [shutil.which(name) or ""]
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        cands.append(str(Path(local) / "Microsoft" / "WinGet" / "Links" / f"{name}.exe"))
    for c in cands:
        if c and Path(c).exists():
            return c
    die(f"{name} not found. Ask the user, then install it (Windows: winget install Gyan.FFmpeg)")


def probe(ffprobe: str, path: Path) -> dict:
    out = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                          "format=duration:stream=index,codec_type,codec_name,width,height:stream_tags=language",
                          "-of", "json", str(path)], capture_output=True, text=True, encoding="utf-8")
    return json.loads(out.stdout or "{}")


def run(cmd: list[str], cwd: str | None = None) -> None:
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        die("ffmpeg failed:\n" + res.stderr[-1500:])


def hard(ffmpeg, video: Path, srt: Path, out: Path, height: int, crf: int, size: int) -> None:
    # libass needs plain paths: work in a temp dir with ASCII names (Arabic/colons break the filter)
    tmp = Path(tempfile.mkdtemp(prefix="lzr-subs-"))
    try:
        # close every Arabic line with RLM too, so trailing punctuation (، . ؟) stays at the line end
        lines = srt.read_text(encoding="utf-8-sig").split("\n")
        lines = [ln.rstrip("\r") + "‏" if ln.startswith("‏") and not ln.rstrip("\r").endswith("‏")
                 else ln.rstrip("\r") for ln in lines]
        (tmp / "subs.srt").write_text("\n".join(lines), encoding="utf-8")
        fonts = tmp / "fonts"
        fonts.mkdir()
        for f in FONTS.glob("*.ttf"):
            shutil.copy(f, fonts / f.name)
        # Encoding=-1 makes libass detect the base direction per line; without it every line is
        # laid out left-to-right: Arabic words in reverse order and the period on the wrong side.
        # BorderStyle=4 = ONE translucent box behind the whole cue. BorderStyle=3 draws a box per
        # line; on two-line cues the boxes overlap and leave a darker band between the lines.
        style = (f"FontName=Readex Pro,Bold=1,FontSize={size},PrimaryColour=&H00FFFFFF,"
                 "BorderStyle=4,Outline=1,Shadow=0,BackColour=&H80000000,OutlineColour=&H80000000,"
                 "MarginV=30,Alignment=2,Encoding=-1")
        vf = f"scale=-2:{height},subtitles=subs.srt:fontsdir=fonts:charenc=UTF-8:force_style='{style}'"
        run([ffmpeg, "-v", "error", "-y", "-i", str(video.resolve()), "-vf", vf,
             "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str((tmp / "out.mp4"))], cwd=str(tmp))
        shutil.move(str(tmp / "out.mp4"), out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _frame_samples(text: str) -> list[tuple[float, float]]:
    """Choose ordinary coverage plus explicit multiword mixed-colour examples."""
    import re
    stamp = re.compile(r"(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})")
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        match = stamp.search(block)
        if not match:
            continue
        c = match.groups()
        start = int(c[0]) * 3600 + int(c[1]) * 60 + int(c[2]) + int(c[3]) / 1000
        end = int(c[4]) * 3600 + int(c[5]) * 60 + int(c[6]) + int(c[7]) / 1000
        body = block[match.end():]
        spans = re.findall(r'<font\b[^>]*>(.*?)</font>', body, re.I | re.S)
        outside = re.sub(r'<font\b[^>]*>.*?</font>', '', body, flags=re.I | re.S)
        outside = re.sub(r'<[^>]+>', '', outside).replace("\u200f", "").strip()
        multiword = any(len(re.sub(r'<[^>]+>', '', span).split()) >= 2 for span in spans)
        cues.append((start, end, bool(outside and multiword)))
    if not cues:
        return []
    picks = [len(cues) // 10, len(cues) // 2, len(cues) - (2 if len(cues) > 1 else 1)]
    mixed = [i for i, cue in enumerate(cues) if cue[2]]
    if mixed:
        picks.extend([mixed[0], mixed[len(mixed) // 2]])
    return [(cues[i][0], cues[i][1]) for i in dict.fromkeys(picks)]


def frames(ffmpeg, video: Path, srt: Path, outdir: Path) -> list[Path]:
    """Capture the actual burned video, including mixed white/coloured Arabic cues."""
    picks = _frame_samples(srt.read_text(encoding="utf-8-sig"))
    if not picks:
        return []
    outdir.mkdir(parents=True, exist_ok=True)
    res = []
    for i, (start, end) in enumerate(picks, 1):
        p = outdir / f"frame{i}.png"
        run([ffmpeg, "-v", "error", "-y", "-ss", f"{(start + end) / 2:.2f}", "-i", str(video), "-frames:v", "1", str(p)])
        res.append(p)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("srt")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--crf", type=int, default=23)
    ap.add_argument("--font-size", type=int, default=19)
    ap.add_argument("--ffmpeg")
    a = ap.parse_args()

    ffmpeg = find_tool("ffmpeg", a.ffmpeg)
    ffprobe = find_tool("ffprobe", str(Path(ffmpeg).with_name("ffprobe" + Path(ffmpeg).suffix)))
    video, srt, out = Path(a.video), Path(a.srt), Path(a.out_dir)
    for p in (video, srt):
        if not p.exists():
            die(f"not found: {p}")
    out.mkdir(parents=True, exist_ok=True)
    stem = srt.stem
    src_dur = float(probe(ffprobe, video).get("format", {}).get("duration", 0))
    problems = []

    o = out / f"{stem} – ترجمة مدمجة.mp4"
    print(f"... burning subtitles at {a.height}p (re-encoding, this takes a few minutes)")
    hard(ffmpeg, video, srt, o, a.height, a.crf, a.font_size)
    info = probe(ffprobe, o)
    dur = float(info.get("format", {}).get("duration", 0))
    if src_dur and abs(dur - src_dur) > 1.5:
        problems.append(f"hard: duration {dur:.1f}s differs from source {src_dur:.1f}s")
    shots = frames(ffmpeg, o, srt, out / "_frames")
    print(f"ok: burned-in subtitles -> {o}  [{o.stat().st_size // 1048576} MB]")
    if shots:
        print("   check these frames by eye: " + ", ".join(str(s) for s in shots))

    for p in problems:
        print("  PROBLEM " + p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
