"""Cache recovery helpers."""


def flush_stale_cache(error_code: str) -> bool:
    """Flush stale entries when error code E42 is reported."""
    return error_code == "E42"

