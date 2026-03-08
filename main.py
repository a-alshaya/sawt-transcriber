import argparse
import glob
import json
import os
import sys

from src.merge import build_transcript
from src.transcribe import transcribe
from src.utils import ensure_output_dir, setup_logging

logger = setup_logging()


def find_input_file(input_dir: str, prefix: str, label: str) -> str:
    """
    Find a file in input_dir whose name starts with prefix and ends with .json.
    Accepts both exact names (e.g. 'participants.json') and UUID-suffixed names
    (e.g. 'participants-c389a955-....json'). Exits with an error if not found.
    """
    pattern = os.path.join(input_dir, f"{prefix}*.json")
    matches = glob.glob(pattern)
    if not matches:
        logger.error("Missing input file (%s): no file matching '%s*.json' in %s", label, prefix, input_dir)
        sys.exit(1)
    if len(matches) > 1:
        logger.warning("Multiple files match '%s*.json' — using: %s", prefix, matches[0])
    return matches[0]


def find_audio_file(input_dir: str) -> str:
    """Find any .mp3 file in input_dir."""
    matches = glob.glob(os.path.join(input_dir, "*.mp3"))
    if not matches:
        logger.error("Missing audio file: no .mp3 found in %s", input_dir)
        sys.exit(1)
    if len(matches) > 1:
        logger.warning("Multiple .mp3 files found — using: %s", matches[0])
    return matches[0]


def load_json(path: str, label: str) -> object:
    if not os.path.exists(path):
        logger.error("Missing input file (%s): %s", label, path)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="sawt-transcriber: Re-transcribe meeting audio with ElevenLabs Scribe v2."
    )
    parser.add_argument(
        "--input-dir",
        default="./input",
        help="Directory containing input files (default: ./input)",
    )
    parser.add_argument(
        "--output-dir",
        default="./output",
        help="Directory for output files (default: ./output)",
    )
    parser.add_argument(
        "--skip-transcription",
        action="store_true",
        help="Skip the ElevenLabs API call and reuse output/scribe_raw.json if it exists.",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir

    ensure_output_dir(output_dir)

    # Auto-detect input files by prefix (supports plain and UUID-suffixed filenames)
    participants = load_json(find_input_file(input_dir, "participants", "participants"), "participants")
    speaker_timeline = load_json(find_input_file(input_dir, "speaker-timeline", "speaker-timeline"), "speaker-timeline")
    participant_events = load_json(find_input_file(input_dir, "participant-events", "participant-events"), "participant-events")
    recall_transcript = load_json(find_input_file(input_dir, "transcript", "recall transcript"), "recall transcript")

    audio_path = find_audio_file(input_dir)

    # Step 1: Transcribe with ElevenLabs Scribe v2
    scribe_result = transcribe(audio_path, output_dir, skip=args.skip_transcription)

    # Attach the original Recall transcript to the Scribe result for downstream passthrough
    scribe_result["recall_transcript_original"] = recall_transcript

    # Step 2 & 3: Diarize + merge → write output/transcript_final.json
    build_transcript(
        scribe_result=scribe_result,
        speaker_timeline=speaker_timeline,
        participants=participants,
        participant_events=participant_events,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
