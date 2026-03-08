import logging
import os


def overlap_duration(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    """Return the duration of overlap between two time intervals."""
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def setup_logging() -> logging.Logger:
    """Configure and return a logger with clean terminal formatting."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s  %(message)s",
    )
    return logging.getLogger("sawt")


def ensure_output_dir(path: str) -> None:
    """Create the output directory if it does not exist."""
    os.makedirs(path, exist_ok=True)
