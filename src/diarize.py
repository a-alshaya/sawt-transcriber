from typing import Optional

from .utils import overlap_duration, setup_logging

logger = setup_logging()


def _parse_recall_timeline(speaker_timeline: list) -> list:
    """Convert speaker-timeline.json entries into {name, start, end} dicts."""
    intervals = []
    for entry in speaker_timeline:
        name = entry["participant"]["name"]
        start = float(entry["start_timestamp"]["relative"])
        end = float(entry["end_timestamp"]["relative"])
        intervals.append({"name": name, "start": start, "end": end})
    return intervals


def _group_words_into_turns(words: list) -> list:
    """
    Group consecutive words that share the same Scribe speaker label into turns.
    Each turn: {scribe_speaker, start, end, words[]}
    """
    if not words:
        return []

    turns = []
    current_speaker = words[0].get("speaker_id") or words[0].get("speaker")
    current_words = [words[0]]

    for word in words[1:]:
        speaker = word.get("speaker_id") or word.get("speaker")
        if speaker == current_speaker:
            current_words.append(word)
        else:
            turns.append(_make_turn(current_speaker, current_words))
            current_speaker = speaker
            current_words = [word]

    turns.append(_make_turn(current_speaker, current_words))
    return turns


def _make_turn(scribe_speaker: str, words: list) -> dict:
    start = words[0].get("start", 0.0)
    end = words[-1].get("end", 0.0)
    return {
        "scribe_speaker": scribe_speaker,
        "start": start,
        "end": end,
        "words": words,
    }


def _resolve_speaker(turn: dict, recall_intervals: list) -> Optional[str]:
    """
    Return the Recall participant name with the most overlap with the turn window.
    Returns None if no overlap is found.
    """
    best_name: Optional[str] = None
    best_overlap = 0.0

    for interval in recall_intervals:
        ov = overlap_duration(turn["start"], turn["end"], interval["start"], interval["end"])
        if ov > best_overlap:
            best_overlap = ov
            best_name = interval["name"]

    return best_name


def build_speaker_map(scribe_result: dict, speaker_timeline: list) -> dict:
    """
    Return a mapping of Scribe speaker labels to real participant names.
    e.g. {"speaker_0": "Khaled Adaileh", "speaker_1": "Sara Ahmad"}
    """
    words = scribe_result.get("words", [])
    recall_intervals = _parse_recall_timeline(speaker_timeline)
    turns = _group_words_into_turns(words)

    # Accumulate overlap per (scribe_speaker, participant_name) pair
    overlap_scores: dict = {}  # {scribe_speaker: {name: total_overlap}}

    for turn in turns:
        label = turn["scribe_speaker"]
        if label not in overlap_scores:
            overlap_scores[label] = {}

        for interval in recall_intervals:
            ov = overlap_duration(turn["start"], turn["end"], interval["start"], interval["end"])
            if ov > 0:
                name = interval["name"]
                overlap_scores[label][name] = overlap_scores[label].get(name, 0.0) + ov

    speaker_map: dict = {}
    for label, name_scores in overlap_scores.items():
        if name_scores:
            best = max(name_scores, key=lambda n: name_scores[n])
            speaker_map[label] = best
        else:
            speaker_map[label] = "Unknown"

    # Warn about any labels that ended up as Unknown
    for label, name in speaker_map.items():
        if name == "Unknown":
            logger.warning("Scribe speaker '%s' could not be matched to any Recall participant.", label)

    return speaker_map


def assign_speakers(scribe_result: dict, speaker_timeline: list) -> tuple[list, dict]:
    """
    Return (turns_with_names, speaker_map).

    Each turn in turns_with_names has: {scribe_speaker, start, end, words[], speaker}
    where 'speaker' is the resolved real name (or 'Unknown').
    """
    words = scribe_result.get("words", [])
    recall_intervals = _parse_recall_timeline(speaker_timeline)
    turns = _group_words_into_turns(words)
    speaker_map = build_speaker_map(scribe_result, speaker_timeline)

    unknown_count = 0
    for turn in turns:
        label = turn["scribe_speaker"]
        name = speaker_map.get(label, "Unknown")
        turn["speaker"] = name
        if name == "Unknown":
            unknown_count += 1
            logger.warning(
                "Unknown speaker at %.2fs–%.2fs (Scribe label: %s)",
                turn["start"],
                turn["end"],
                label,
            )

    return turns, speaker_map
