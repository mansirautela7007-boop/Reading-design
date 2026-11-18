#!/usr/bin/env python3
"""Generate voice-over audio for the reading prototype (macOS only, no paid services).

Reads reading-prototype.html and writes vo/<key>.m4a for:
  - every line in the <script id="vo-lines"> block (instructions, questions, feedback)
  - every paragraph of the story (para-0, para-1, ...) for the Listen button
  - every word in the story (w-<word>) for tap-to-pronounce
Then writes vo/manifest.json: each clip's playback speed, so every line is heard
at a slow, steady pace for Grades 1-6.

How it avoids garbled audio: the Siri voices sometimes "babble" on long text, so
each sentence is recorded on its own, checked for a sensible length (re-recorded
if it is too long), and the sentences are joined with real pauses.

Run again after changing any text; only changed lines are re-recorded.
Usage:  python3 make_vo.py   [--voice "Tara (English (India))"]  [--force]
"""
import json, re, subprocess, sys, tempfile, hashlib, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "reading-prototype.html"
OUT = ROOT / "vo"
VOICE = "Tara (English (India))"
if "--voice" in sys.argv:
    VOICE = sys.argv[sys.argv.index("--voice") + 1]
FORCE = "--force" in sys.argv

# Pacing for young readers
PAUSE_LINE_MS = 300        # between sentences in instructions and questions
PAUSE_PARA_MS = 250        # between sentences in the story
TARGET_WPM = {"para": 1000, "line": 1000}   # 1000 = never slow down: play at the voice's natural speed
WORD_SPEED = 1.0           # single tapped words
MIN_SPEED = 0.6            # slower than this starts to sound stretched

NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
       "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten"}

def norm(w):  # must match norm() in the page
    w = w.lower().replace("’", "").replace("'", "")
    w = re.sub(r"[^a-z0-9]", "", w)
    w = NUM.get(w, w)
    return "mister" if w == "mr" else w

def strip_markup(s):
    return re.sub(r"\[\[(.+?)\|.+?\]\]", r"\1", s)

def segments(text, pause_ms):
    """Split into (sentence, pause-after-ms). [[slnc N]] in a line forces a pause there."""
    out = []
    for chunk in re.split(r"(\[\[slnc \d+\]\])", text):
        m = re.fullmatch(r"\[\[slnc (\d+)\]\]", chunk.strip())
        if m:
            if out: out[-1] = (out[-1][0], int(m.group(1)))
            continue
        for s in re.split(r'(?<=[.!?])["”]?\s+(?=\S)', chunk.strip()):
            if s.strip():
                out.append((s.strip(), pause_ms))
    if out: out[-1] = (out[-1][0], 0)
    return out

html = HTML.read_text(encoding="utf-8")
lines = json.loads(re.search(r'<script type="application/json" id="vo-lines">(.*?)</script>', html, re.S).group(1))
paras = [json.loads('"' + m + '"') for m in re.findall(r'\ben:"((?:[^"\\]|\\.)*)"', html)]
gloss = re.findall(r'\bw:"([^"]+)"', html)

items = {}  # key -> (text, pause between sentences)
for k, t in lines.items():
    items[k] = (t, PAUSE_LINE_MS)
for i, p in enumerate(paras):
    items[f"para-{i}"] = (strip_markup(p).replace("Mr.", "Mister"), PAUSE_PARA_MS)
    for tok in strip_markup(p).split():
        n = norm(tok)
        if n and f"w-{n}" not in items:
            spoken = "Mister" if n == "mister" else re.sub(r"^\W+|\W+$", "", tok)
            items[f"w-{n}"] = (spoken, 0)
for g in gloss:
    items.setdefault(f"w-{norm(g)}", (g, 0))

def say_wav(text, tmp, name):
    aiff, wav = Path(tmp) / f"{name}.aiff", Path(tmp) / f"{name}.wav"
    subprocess.run(["say", "-v", VOICE, "-o", str(aiff), text], check=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@22050", str(aiff), str(wav)], check=True)
    with wave.open(str(wav)) as w:
        return w.readframes(w.getnframes()), w.getnframes() / w.getframerate()

from array import array
def speech_bounds(data):
    """Seconds where speech starts and ends (ignores silence at both ends)."""
    a = array("h"); a.frombytes(data)
    loud = [i for i in range(0, len(a), 22) if abs(a[i]) > 400]   # check every ~1 ms
    if not loud: return 0.0, len(a) / 22050
    return loud[0] / 22050, loud[-1] / 22050

def plausible(speech_secs, n_words):
    """The voice sometimes babbles (too long) or cuts off / garbles (too short)."""
    return max(0.1, 0.15 * n_words) <= speech_secs <= 0.45 * n_words + 0.7

def take(text, tmp, name, tries=8):
    """Record until two takes match. A clean recording comes out identical every time,
    while glitches (babbling, cut-offs, garbled words) are random, so a matching pair
    is the clean version. Returns (data, speech_secs)."""
    n = len(text.split())
    seen = []
    for attempt in range(tries):
        data, _ = say_wav(text, tmp, f"{name}_{attempt}")
        s, e = speech_bounds(data)
        dur = e - s
        for _, d in seen:
            if abs(d - dur) <= 0.02 and plausible(dur, n):
                return data, dur
        seen.append((data, dur))
    ok = [x for x in seen if plausible(x[1], n)] or seen
    best = min(ok, key=lambda x: abs(x[1] - 0.32 * n))
    print(f"    ! no matching takes after {tries} tries, using {best[1]:.2f}s: {text[:50]}")
    return best

def word_starts(sentence, data, tmp):
    """Measure when each word of a sentence starts, in seconds from the start of `data`.
    Records the sentence from word k to the end, for every k. Those recordings end exactly
    like the full sentence, so (full length - tail length) is where word k starts."""
    words = sentence.split()
    lead, end = speech_bounds(data)
    full = end - lead
    starts = [lead]
    for k in range(1, len(words)):
        _, tail = take(" ".join(words[k:]), tmp, f"suf{k}")
        starts.append(lead + full - tail)
    # keep the times in order and inside the sentence
    for k in range(1, len(starts)):
        starts[k] = min(max(starts[k], starts[k - 1] + 0.06), end - 0.05 * (len(starts) - k))
    return starts


def smooth(times, words):
    """Fix the few words whose measured start got squeezed against the previous word:
    spread them between the nearest well-measured words, by word length."""
    t = list(times)
    bad = [False] + [t[k] - t[k - 1] < 0.08 for k in range(1, len(t))]
    weight = lambda w: len(re.sub(r"\W", "", w)) + 1.5 + (3 if re.search(r"[,;:.!?][\"\u201d]?$", w) else 0)
    k = 1
    while k < len(t):
        if not bad[k]: k += 1; continue
        a = k - 1                                   # last good word before the run
        while a > 0 and bad[a]: a -= 1
        b = k
        while b < len(t) and bad[b]: b += 1         # first good word after the run
        if b >= len(t): break
        span = sum(weight(words[i]) for i in range(a, b))
        acc = 0
        for i in range(a + 1, b):
            acc += weight(words[i - 1])
            t[i] = round(t[a] + (t[b] - t[a]) * acc / span, 3)
        k = b
    return t

def record(text, pause_ms, dest, tmp, timed=False):
    frames = b""
    times = []
    for n, (sentence, pause) in enumerate(segments(text, pause_ms)):
        best = take(sentence, tmp, f"s{n}")
        if timed:
            offset = len(frames) / 2 / 22050
            times += [round(offset + t, 3) for t in word_starts(sentence, best[0], tmp)]
        frames += best[0] + b"\x00\x00" * int(22050 * pause / 1000)
    wav = Path(tmp) / "joined.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050); w.writeframes(frames)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(wav), str(dest)], check=True)
    return len(frames) / 2 / 22050, times

OUT.mkdir(exist_ok=True)
cache_file = OUT / ".cache.json"
cache = json.loads(cache_file.read_text()) if cache_file.exists() and not FORCE else {}
durations = cache.get("_durations", {})
timings = cache.get("_timings", {})
made = 0
with tempfile.TemporaryDirectory() as tmp:
    for key, (text, pause) in items.items():
        timed = key.startswith("para-")
        sig = hashlib.md5(f"v7|{VOICE}|{pause}|{text}".encode()).hexdigest()
        dest = OUT / f"{key}.m4a"
        if dest.exists() and cache.get(key) == sig and key in durations and (not timed or key in timings):
            continue
        durations[key], t = record(text, pause, dest, tmp, timed)
        if timed:
            timings[key] = t
            if len(t) != len(text.split()):
                print(f"    ! word count mismatch in {key}: {len(t)} timings, {len(text.split())} words")
        cache[key] = sig
        made += 1
        shown = re.sub(r"\[\[.*?\]\]", "", text)[:60]
        print(f"  {key} ({durations[key]:.1f}s): {shown}")

# Remove clips that are no longer used
for f in OUT.glob("*.m4a"):
    if f.stem not in items:
        f.unlink(); cache.pop(f.stem, None); durations.pop(f.stem, None)

# Per-clip playback speed so every line is heard at the target pace
manifest = {}
for key, (text, _) in items.items():
    if key.startswith("w-"):
        manifest[key] = WORD_SPEED
        continue
    words = len(re.sub(r"\[\[.*?\]\]", "", text).split())
    wpm = 60 * words / durations[key]
    target = TARGET_WPM["para" if key.startswith("para-") else "line"]
    manifest[key] = round(max(MIN_SPEED, min(1.0, target / wpm)), 3)

cache["_durations"] = durations
cache["_timings"] = {k: v for k, v in timings.items() if k in items}
cache_file.write_text(json.dumps(cache, indent=1))
# When each word of the story starts in its audio (seconds), for exact highlighting
(OUT / "timings.json").write_text(json.dumps({k: smooth(v, items[k][0].split()) for k, v in cache["_timings"].items()}))
(OUT / "manifest.json").write_text(json.dumps(manifest, indent=0, sort_keys=True))
print(f"Done. {made} recorded, {len(items)} total in vo/manifest.json")
