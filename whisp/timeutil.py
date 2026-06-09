APPLE_EPOCH_OFFSET = 978307200  # 1970-01-01 -> 2001-01-01 in seconds


def unix_to_apple(unix_seconds: float) -> float:
    return unix_seconds - APPLE_EPOCH_OFFSET


def apple_to_unix(apple_seconds: float) -> float:
    return apple_seconds + APPLE_EPOCH_OFFSET
