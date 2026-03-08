import json
import os

from .diarize import assign_speakers
from .utils import setup_logging

logger = setup_logging()


def _merge_consecutive_turns(turns: list) -> list:
    """Merge consecutive turns that belong to the same speaker."""
    if not turns:
        return []

    merged = []
    current = dict(turns[0])

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


def _turn_to_entry(turn: dict) -> dict:
    """Convert an internal turn dict to the final transcript entry format."""
    text = " ".join(w.get("text", "") for w in turn["words"]).strip()
    return {
        "start": turn["start"],
        "end": turn["end"],
        "speaker": turn["speaker"],
        "text": text,
    }


def build_transcript(
    scribe_result: dict,
    speaker_timeline: list,
    participants: list,
    participant_events: list,
    output_dir: str,
) -> dict:
    """
    Build the final transcript JSON, write it to output_dir/transcript_final.json,
    and return it.
    """
    turns, speaker_map = assign_speakers(scribe_result, speaker_timeline)
    merged_turns = _merge_consecutive_turns(turns)

    transcript_entries = [_turn_to_entry(t) for t in merged_turns]

    unknown_segments_count = sum(1 for e in transcript_entries if e["speaker"] == "Unknown")

    # Derive meeting duration from last word end time
    all_words = scribe_result.get("words", [])
    if all_words:
        meeting_duration = all_words[-1].get("end", 0.0)
    else:
        meeting_duration = 0.0

    output = {
        "metadata": {
            "meeting_duration_seconds": meeting_duration,
            "total_turns": len(transcript_entries),
            "participants": participants,
            "participant_events": participant_events,
            "unknown_segments_count": unknown_segments_count,
        },
        "transcript": transcript_entries,
    }

    output_path = os.path.join(output_dir, "transcript_final.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    unique_speakers = {e["speaker"] for e in transcript_entries}

    logger.info("--- Summary ---")
    logger.info("Total turns    : %d", len(transcript_entries))
    logger.info("Unique speakers: %s", ", ".join(sorted(unique_speakers)))
    logger.info("Unknown segs   : %d", unknown_segments_count)
    logger.info("Output written : %s", output_path)

    return output
