from whisp.timeutil import apple_to_unix, unix_to_apple

APPLE_EPOCH_OFFSET = 978307200  # seconds between 1970-01-01 and 2001-01-01


def test_round_trip():
    unix = 1_700_000_000.0
    assert apple_to_unix(unix_to_apple(unix)) == unix


def test_known_offset():
    assert unix_to_apple(APPLE_EPOCH_OFFSET) == 0.0
    assert apple_to_unix(0.0) == APPLE_EPOCH_OFFSET
