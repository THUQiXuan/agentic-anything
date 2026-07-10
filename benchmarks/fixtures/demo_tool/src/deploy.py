"""Deployment helpers."""


def validate_canary(healthy_instances: int, total_instances: int) -> bool:
    """Validate a canary deployment before production promotion."""
    return total_instances > 0 and healthy_instances == total_instances

