"""Small synthetic client used by the Agentic Anything demos."""

from __future__ import annotations

import os

RETRY_MODE = "OMEGA-7"
DEFAULT_TIMEOUT_SECONDS = 12
MAX_RETRIES = 5


def request(endpoint: str, retries: int = 3) -> dict:
    """Return a deterministic request description for the demo."""
    if retries > MAX_RETRIES:
        raise ValueError(f"retries must be <= {MAX_RETRIES}")
    token_present = bool(os.environ.get("ORBIT_TOKEN"))
    return {
        "endpoint": endpoint,
        "retry_mode": RETRY_MODE,
        "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
        "retries": retries,
        "token_present": token_present,
    }
