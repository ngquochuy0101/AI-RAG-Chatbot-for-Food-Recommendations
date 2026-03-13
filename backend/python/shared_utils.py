import logging
import os
from typing import Optional

MIN_TORCH_VERSION = (2, 4, 0)


def configure_logging(default_level: str = "INFO") -> None:
    """Configure process-wide logging once."""
    level_name = os.getenv("LOG_LEVEL", default_level).upper()
    level = getattr(logging, level_name, logging.INFO)

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    else:
        logging.getLogger().setLevel(level)


def parse_version_tuple(raw_version: str) -> tuple[int, int, int]:
    """Convert version string to comparable numeric tuple."""
    clean = raw_version.split("+", 1)[0]
    parts = clean.split(".")
    values = []

    for part in parts[:3]:
        digits = "".join(char for char in part if char.isdigit())
        values.append(int(digits) if digits else 0)

    while len(values) < 3:
        values.append(0)

    return tuple(values)


def get_torch_version() -> Optional[str]:
    """Return installed torch version if available."""
    try:
        import torch

        return torch.__version__
    except ImportError:
        return None


def is_torch_compatible(
    min_version: tuple[int, int, int] = MIN_TORCH_VERSION,
) -> tuple[bool, Optional[str]]:
    """Check whether installed torch meets minimum requirement."""
    current_version = get_torch_version()
    if not current_version:
        return False, None

    return parse_version_tuple(current_version) >= min_version, current_version


def min_version_label(min_version: tuple[int, int, int]) -> str:
    """Format version tuple to x.y.z label."""
    return ".".join(str(item) for item in min_version)
