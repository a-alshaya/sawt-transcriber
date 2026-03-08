import json
import os
import sys

import requests
from dotenv import load_dotenv

from .utils import ensure_output_dir, setup_logging

logger = setup_logging()

ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"


def _load_api_key() -> str:
    load_dotenv()
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        logger.error("ELEVENLABS_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)
    return key


def transcribe(audio_path: str, output_dir: str, skip: bool) -> dict:
    """
    Return the ElevenLabs Scribe v2 transcription result as a dict.

    If skip=True and the cache file exists, load from cache.
    If skip=True and the cache file is missing, print an error and exit.
    Otherwise, call the API, save the raw response to cache, and return it.
    """
    ensure_output_dir(output_dir)
    cache_path = os.path.join(output_dir, "scribe_raw.json")

    if skip:
        if os.path.exists(cache_path):
            logger.info("--skip-transcription set: loading cached transcription from %s", cache_path)
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            logger.error(
                "No cached transcription found at %s. "
                "Run without --skip-transcription first.",
                cache_path,
            )
            sys.exit(1)

    api_key = _load_api_key()

    if not os.path.exists(audio_path):
        logger.error("Audio file not found: %s", audio_path)
        sys.exit(1)

    logger.info("Uploading %s to ElevenLabs Scribe v2 ...", audio_path)

    with open(audio_path, "rb") as audio_file:
        files = {"file": ("meeting.mp3", audio_file, "audio/mpeg")}
        data = {
            "model_id": "scribe_v2",
            "diarize": "true",
            "timestamps_granularity": "word",
        }
        headers = {"xi-api-key": api_key}

        response = requests.post(ELEVENLABS_STT_URL, headers=headers, files=files, data=data)

    if not response.ok:
        logger.error(
            "ElevenLabs API error %s: %s",
            response.status_code,
            response.text,
        )
        sys.exit(1)

    result = response.json()

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    logger.info("Raw Scribe response saved to %s", cache_path)
    return result
