# Reading Comprehension Template: Prototype

A working prototype of a reading comprehension lesson for Grades 1–6. It shows how one passage plays out for a learner: reading the story with audio support, answering questions, summing up, and reflecting. The sample passage is **"The Water Drum"**.

---

## Run it

The prototype must be served from `localhost`. Opening the HTML file directly will not work, because the microphone (Read along) and the audio files need a local server.

```bash
cd "Reading design"
python3 -m http.server 8000
```

Then open **http://localhost:8000/** in **Chrome** or **Edge** and allow the microphone when asked.

| Browser | What works |
|---|---|
| Chrome / Edge | Everything, including Read along |
| Safari | Everything except Read along (speech recognition is unreliable) |
| Firefox | Everything except Read along (no speech recognition) |

Browsers block sound until the learner taps once, so the story page's spoken instructions may stay silent on first load. Everything after the first tap is spoken.

---

## Learner flow

| Step | Page | What the learner does |
|---|---|---|
| 1 | **Story** | Reads the passage, shown as two halves side by side, with read-aloud and word support |
| 2 | **Questions** (split screen) | The story moves to a scrolling pane on the left; 4 questions appear one at a time on the right, each labelled with the skill it checks |
| 3 | **Sum it up** (split screen) | Picks the sentence that best summarises the story, with the story still on the left |
| 4 | **Think back** | Writes how the story connects to their own life (optional) |
| 5 | **Finish** | Sees stars, results by skill, and how many words they read aloud clearly |

---

## Feature list

### While reading

| Feature | How it works | Priority |
|---|---|---|
| Opens on the story | The app starts on the passage, split into two halves shown side by side as plain text (stacked on phones). | Must-have |
| Read along | Press **Read aloud** and read out loud. Each word turns green when said correctly; skipped words get a red wavy line. **Pause** keeps the place, and earlier speech is never counted again after resuming. | Must-have |
| Tap a word to hear it | Any word in the story is spoken when tapped. | Must-have |
| Word meaning card | Words with a dashed underline open a small card on tap, attached to the word: meaning and a short example sentence. | Must-have |

### After reading

| Feature | How it works | Priority |
|---|---|---|
| Questions by skill | Four questions: find the fact, think and infer, word meaning, order of events. | Must-have |
| Answer check on tap | Options are radio-style. Choosing one marks it right or wrong immediately; wrong options are greyed out. **Next** unlocks once the answer is right. | Must-have |
| Split screen | Questions sit on the right and the story on the left. The story scrolls on its own, with ▲ ▼ buttons to move it up and down, and fades softly at the top or bottom edge while there is more text to scroll to. **Next** is at the bottom right. | Must-have |
| Look back hint | After a wrong answer, **Show me where to look** highlights the sentence with the answer in the story pane and scrolls to it. | Must-have |
| Order of events | Tap four events in the order they happened; it checks itself when all four are tapped. | Good-to-have |
| Best summary | Pick the summary that tells the whole story, not just details. | Good-to-have |
| Reflection | One open question linking the story to the learner's life. | Good-to-have |
| Stars and report | One star for each of the 4 questions and the summary answered right on the first try (5 in total), plus results by skill and read-aloud accuracy. | Good-to-have |

### On every page

| Feature | How it works | Priority |
|---|---|---|
| Voice-over | Every instruction, question, option and feedback line is spoken at normal speed. The speaker icon in the header turns it on or off. | Must-have |
| Hear the question again | The small speaker next to each quiz and summary question replays it. Tapping it while it plays stops it. | Must-have |
| Text size | **A−** and **A+** in the header change all text in five steps (85%–150%). The setting is remembered. | Must-have |

### Planned for later

| Feature | Notes |
|---|---|
| Easier and harder versions | The same story at two or three reading levels. |
| Highlight and notes | Older learners mark key lines and add notes. |

---

## Files

```
Reading design/
├── reading-prototype.html   The app (content, design and logic in one file)
├── index.html               Shortcut to reading-prototype.html, so localhost:8000/ opens the app
├── make_vo.py               Records all voice-over and story audio (macOS)
├── README.md                This file
└── vo/
    ├── *.m4a                One audio clip per voice line and per word in the story
    ├── manifest.json        List of clips and the playback speed of each
    └── .cache.json          Lets make_vo.py skip lines that have not changed
```

---

## Adding a new passage (content team)

Everything the content team writes is at the top of `reading-prototype.html`.

### 1. Passage: `P`

| Field | What to write |
|---|---|
| `title` | Story name |
| `meta` | Grade range and reading time, for example `Grades 1–6 · 8 min read` |
| `paras` | One entry per paragraph, each with `sec` (0 = first half, 1 = second half), `en` (English) and `hi` (Hindi translation). Split the story so both halves are about the same length. |

Mark tough words in `en` like this: `[[word as shown|key]]`. For example `[[rolled in|rolled]]` shows "rolled in" with a dashed underline and opens the `rolled` card. Aim for 4–8 tough words per passage.

### 2. Tough words: `GLOSS`

One entry per key used above:

```js
gutter:{ w:"gutter", m:"a channel on a roof edge that carries rainwater", hi:"परनाला", ex:"The gutter was full of leaves." }
```

`w` is the word, `m` a simple meaning, and `ex` a very short example sentence. (`hi`, a Hindi word, is optional and not shown.)

### 3. Questions: `QUESTIONS`

Four to six questions. Include at least one fact, one inference and one word-in-context question.

| Field | What to write |
|---|---|
| `type` | `"mcq"` or `"seq"` (order of events) |
| `skill` | The label shown to the learner, for example `Think and infer` |
| `q` | The question |
| `o` / `a` | Three options and the index of the right one (0, 1 or 2). Wrong options should be ones a real learner might pick |
| `items` / `order` | For `seq`: four events, and their correct order as indexes |
| `ref` / `quote` | Which paragraph holds the answer (0, 1, 2… counting through both halves) and the exact sentence to highlight for **Look back** |

### 4. Summary: `SUMMARY`

Three sentences: one correct, one that only lists details, one that is wrong. Give a short reason for each wrong one in `why`.

### 5. Voice-over lines: `vo-lines`

The JSON block near the top lists every line the app speaks, by key. Update the questions, options, summary and finish lines to match the new passage. `[[slnc 300]]` adds a 300 ms pause, which is useful before a title.

### 6. Record the audio

```bash
python3 make_vo.py
```

This re-records only lines that changed. Then hard-refresh the browser (Cmd+Shift+R).

---

## How the audio is made

All audio is recorded with the Mac's built-in Indian English voice **Tara**. It is free and runs on the computer, with no online service.

The Mac voice sometimes produces a broken take: it babbles, cuts off or garbles words, at random. `make_vo.py` guards against this:

1. **One sentence at a time.** Each sentence is recorded separately and joined with short pauses (300 ms).
2. **Two matching takes.** A clean recording comes out identical every time, while glitches are random. Each sentence is recorded until two takes match in length, and only that take is used.
3. **Normal speed.** Every clip plays at the voice's natural speed.

| Option | What it does |
|---|---|
| `python3 make_vo.py` | Record only new or changed lines |
| `python3 make_vo.py --force` | Re-record everything |
| `python3 make_vo.py --voice "Rishi"` | Use a different installed voice (Rishi is male Indian English) |

The pacing settings are at the top of `make_vo.py`: `PAUSE_LINE_MS`, `TARGET_WPM`, `WORD_SPEED` and `MIN_SPEED`.

---

## Known limits

- **Read along** uses Chrome's speech recognition. It needs internet, and Chrome sends the audio to Google to turn it into text. It works for Indian English but may miss names or fast speech. The app allows up to three skipped words before it loses its place.
- **On a phone**, the microphone needs an `https` address. The plain `localhost` link works only on the computer running the server.
- **Voice quality** is limited to the Mac's built-in voices. Swapping in professionally recorded audio only needs files with the same names in `vo/` and a matching `manifest.json`.
- **Progress** is not saved. Reloading the page starts the lesson again. Only text size and the voice-over on/off setting are remembered.
