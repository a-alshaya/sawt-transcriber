import argparse
import json
import os
import sys

from src.merge import build_transcript
from src.transcribe import transcribe
from src.utils import ensure_output_dir, setup_logging

logger = setup_logging()


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

    # Load input files
    participants = load_json(os.path.join(input_dir, "participants.json"), "participants")
    speaker_timeline = load_json(os.path.join(input_dir, "speaker-timeline.json"), "speaker-timeline")
    participant_events = load_json(os.path.join(input_dir, "participant-events.json"), "participant-events")

    # Load Recall transcript for reference only — included in output as-is
    recall_transcript = load_json(os.path.join(input_dir, "transcript.json"), "recall transcript")

    audio_path = os.path.join(input_dir, "meeting.mp3")

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
