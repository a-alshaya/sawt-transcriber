# sawt-transcriber

A CLI tool for re-transcribing meeting recordings using ElevenLabs Scribe v2. It takes Recall.ai's structured meeting metadata (participants, speaker timeline) and raw meeting audio, produces a bilingual Arabic-English transcript with real participant names resolved via speaker diarization matching, and writes a clean JSON output file.

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your ElevenLabs API key
```

---

## Input files

Place the following files inside the `input/` directory:

| File | Description |
|------|-------------|
| `meeting.mp3` | Raw meeting audio |
| `participants.json` | Array of participant objects from Recall.ai |
| `speaker-timeline.json` | Recall.ai speaker activity windows (relative timestamps) |
| `participant-events.json` | Join/leave events from Recall.ai |
| `transcript.json` | Recall.ai's original transcript (kept for reference only; not used for text) |

Example schemas are provided in `input/` as a reference.

---

## Usage

### Full run (calls ElevenLabs API)

```bash
python main.py
```

### Reuse cached transcription (skip API call)

After a successful run, `output/scribe_raw.json` is cached. On subsequent runs you can skip the API call:

```bash
python main.py --skip-transcription
```

If no cache exists yet, the tool will print:

```
ERROR  No cached transcription found at output/scribe_raw.json. Run without --skip-transcription first.
```

### Custom directories

```bash
python main.py --input-dir /path/to/input --output-dir /path/to/output
```

---

## Output

The tool writes two files to `output/`:

- `scribe_raw.json` — raw ElevenLabs Scribe v2 API response (cache)
- `transcript_final.json` — final clean transcript

### `transcript_final.json` schema

```json
{
  "metadata": {
    "meeting_duration_seconds": 121.4,
    "total_turns": 12,
    "participants": [ ... ],
    "participant_events": [ ... ],
    "unknown_segments_count": 0
  },
  "transcript": [
    {
      "start": 0.5,
      "end": 8.2,
      "speaker": "Fahad Saad",
      "text": "أهلاً وسهلاً، let's get started."
    },
    {
      "start": 9.0,
      "end": 15.7,
      "speaker": "Sara Ahmad",
      "text": "شكراً، I'll share the update now."
    }
  ]
}
```

Arabic text is preserved as proper Unicode (not escaped).

---

## Notes

- **Phase 1** (this tool): manual input workflow — place files in `input/` and run locally.
- **Phase 2** (planned): automated pipeline that fetches Recall.ai data via API, triggers transcription, and stores results without manual file handling.
