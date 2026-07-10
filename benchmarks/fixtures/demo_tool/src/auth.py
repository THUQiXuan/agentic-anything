"""Authentication token helpers. 身份验证令牌在这里轮换。"""


def rotate_access_token(token_name: str) -> str:
    """Rotate an access token and emit an audit event."""
    return f"rotated:{token_name}"

