import json
import os
from datetime import datetime, timezone, timedelta

from .diarize import assign_speakers
from .utils import setup_logging

logger = setup_logging()


def _get_meeting_start(participant_events: dict) -> datetime:
    """
    Extract the meeting start absolute datetime from participant-events.
    participant-events is keyed by participant id; each value is a list of events.
    We find the event with relative=0 to get the absolute start time.
    """
    for events in participant_events.values():
        for event in events:
            raw = event.get("raw_data", {})
            ts = raw.get("timestamp", {})
            if ts.get("relative", -1) == 0 and ts.get("absolute"):
                return datetime.fromisoformat(ts["absolute"].replace("Z", "+00:00"))
    # Fallback: use the earliest created_at across all events
    earliest = None
    for events in participant_events.values():
        for event in events:
            ts_str = event.get("created_at") or event.get("raw_data", {}).get("timestamp", {}).get("absolute")
            if ts_str:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if earliest is None or dt < earliest:
                    earliest = dt
    return earliest or datetime.now(timezone.utc)


def _to_absolute(meeting_start: datetime, relative_seconds: float) -> str:
    """Return ISO 8601 UTC string for meeting_start + relative_seconds."""
    dt = meeting_start + timedelta(seconds=relative_seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"


def _merge_consecutive_turns(turns: list) -> list:
    """Merge consecutive turns that belong to the same speaker."""
    if not turns:
        return []

    merged = []
    current = dict(turns[0])
    current["words"] = list(turns[0]["words"])

    for turn in turns[1:]:
        if turn["speaker"] == current["speaker"]:
            current["end"] = turn["end"]
            current["words"].extend(turn["words"])
        else:
            merged.append(current)
            current = dict(turn)
            current["words"] = list(turn["words"])

    merged.append(current)
    return merged


def _build_participant_lookup(participants: list) -> dict:
    """Return {name: participant_object} for fast lookup."""
    return {p["name"]: p for p in participants}


def _turn_to_recall_entry(turn: dict, participant_lookup: dict, meeting_start: datetime) -> dict:
    """
    Convert an internal turn into a Recall-compatible entry:
    { "participant": {...}, "words": [{"text", "start_timestamp", "end_timestamp"}] }
    """
    name = turn["speaker"]
    participant = participant_lookup.get(name, {"name": name})

    words = []
    for w in turn["words"]:
        if w.get("type") == "spacing":
            continue
        start_rel = w.get("start", 0.0)
        end_rel = w.get("end", 0.0)
        words.append({
            "text": w.get("text", ""),
            "start_timestamp": {
                "relative": start_rel,
                "absolute": _to_absolute(meeting_start, start_rel),
            },
            "end_timestamp": {
                "relative": end_rel,
                "absolute": _to_absolute(meeting_start, end_rel),
            },
        })

    return {"participant": participant, "words": words}


def build_transcript(
    scribe_result: dict,
    speaker_timeline: list,
    participants: list,
    participant_events: dict,
    output_dir: str,
) -> list:
    """
    Build the final transcript as a Recall-compatible array and write to
    output_dir/transcript_final.json.
    """
    turns, _ = assign_speakers(scribe_result, speaker_timeline)
    merged_turns = _merge_consecutive_turns(turns)

    meeting_start = _get_meeting_start(participant_events)
    participant_lookup = _build_participant_lookup(participants)

    transcript = [
        _turn_to_recall_entry(t, participant_lookup, meeting_start)
        for t in merged_turns
    ]

    unknown_count = sum(1 for t in merged_turns if t["speaker"] == "Unknown")
    unique_speakers = {t["speaker"] for t in merged_turns}

    output_path = os.path.join(output_dir, "transcript_final.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(transcript, f, ensure_ascii=False, indent=2)

    logger.info("--- Summary ---")
    logger.info("Total turns    : %d", len(transcript))
    logger.info("Unique speakers: %s", ", ".join(sorted(unique_speakers)))
    logger.info("Unknown segs   : %d", unknown_count)
    logger.info("Output written : %s", output_path)

    return transcript
