from whisp.transcribe.base import strip_artifacts


def test_strips_blank_audio_marker():
    assert strip_artifacts("[BLANK_AUDIO]") == ""
    assert strip_artifacts("[ BLANK_AUDIO ]") == ""
    assert strip_artifacts("[blank audio]") == ""


def test_strips_other_nonspeech_markers():
    assert strip_artifacts("(silence)") == ""
    assert strip_artifacts("[ Inaudible ]") == ""
    assert strip_artifacts("[MUSIC playing]") == ""


def test_keeps_real_speech_and_removes_inline_marker():
    assert strip_artifacts("Hello there [BLANK_AUDIO]") == "Hello there"
    assert strip_artifacts("Buy milk and eggs") == "Buy milk and eggs"


def test_collapses_whitespace():
    assert strip_artifacts("  hi   there  ") == "hi there"
