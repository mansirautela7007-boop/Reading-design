#!/usr/bin/env python3
"""Generate voice-over audio for the reading prototype (macOS only).

Reads reading-prototype.html and writes vo/<key>.m4a for:
  - every line in the <script id="vo-lines"> block (instructions, questions, feedback)
  - every passage part (para-0, para-1, ...) for the Listen button
  - every word in the passage (w-<word>) for tap-to-pronounce
Then writes vo/manifest.json, which the page reads to know which files exist.

Run again after changing any text; only changed lines are re-recorded.
Usage:  python3 make_vo.py   [--voice "Tara (English (India))"]
"""
import json, re, subprocess, sys, tempfile, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "reading-prototype.html"
OUT = ROOT / "vo"
VOICE = "Tara (English (India))"
if "--voice" in sys.argv:
    VOICE = sys.argv[sys.argv.index("--voice") + 1]

NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five",
       "6": "six", "7": "seven", "8": "eight", "9": "nine", "10": "ten"}

def norm(w):  # must match norm() in the page
    w = w.lower().replace("’", "").replace("'", "")
    w = re.sub(r"[^a-z0-9]", "", w)
    w = NUM.get(w, w)
    return "mister" if w == "mr" else w

def strip_markup(s):
    return re.sub(r"\[\[(.+?)\|.+?\]\]", r"\1", s)

html = HTML.read_text(encoding="utf-8")
lines = json.loads(re.search(r'<script type="application/json" id="vo-lines">(.*?)</script>', html, re.S).group(1))
paras = [json.loads('"' + m + '"') for m in re.findall(r'\ben:"((?:[^"\\]|\\.)*)"', html)]
gloss = re.findall(r'\bw:"([^"]+)"', html)

items = {}  # key -> (text, words-per-minute)
for k, t in lines.items():
    items[k] = (t, 165)
for i, p in enumerate(paras):
    items[f"para-{i}"] = (strip_markup(p).replace("Mr.", "Mister"), 150)
    for tok in strip_markup(p).split():
        n = norm(tok)
        if n and f"w-{n}" not in items:
            spoken = "Mister" if n == "mister" else re.sub(r"^\W+|\W+$", "", tok)
            items[f"w-{n}"] = (spoken, 140)
for g in gloss:
    items.setdefault(f"w-{norm(g)}", (g, 140))

OUT.mkdir(exist_ok=True)
cache_file = OUT / ".cache.json"
cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
made = 0
with tempfile.TemporaryDirectory() as tmp:
    for key, (text, rate) in items.items():
        sig = hashlib.md5(f"{VOICE}|{rate}|{text}".encode()).hexdigest()
        dest = OUT / f"{key}.m4a"
        if dest.exists() and cache.get(key) == sig:
            continue
        aiff = Path(tmp) / "x.aiff"
        subprocess.run(["say", "-v", VOICE, "-r", str(rate), "-o", str(aiff), text], check=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", str(aiff), str(dest)], check=True)
        cache[key] = sig
        made += 1
        print(f"  {key}: {text[:60]}")

cache_file.write_text(json.dumps(cache, indent=1))
(OUT / "manifest.json").write_text(json.dumps(sorted(items.keys())))
print(f"Done. {made} recorded, {len(items)} total in vo/manifest.json")
