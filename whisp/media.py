"""Pause/resume whatever media is playing (video, music) while recording, so the
mic doesn't capture it and the user doesn't miss anything.

- is_audio_playing(): CoreAudio check — is the default output device actually in
  use right now? Used to avoid pressing Play when nothing is playing.
- play_pause(): simulate the keyboard Play/Pause media key (works for Music,
  Spotify, Safari/Chrome video, QuickTime, etc.).
"""
import ctypes

from AppKit import NSEvent
from Quartz import CGEventPost, kCGHIDEventTap

NSSystemDefined = 14
NX_KEYTYPE_PLAY = 16


def _fourcc(code: str) -> int:
    return (ord(code[0]) << 24) | (ord(code[1]) << 16) | (ord(code[2]) << 8) | ord(code[3])


class _Addr(ctypes.Structure):
    _fields_ = [("mSelector", ctypes.c_uint32),
                ("mScope", ctypes.c_uint32),
                ("mElement", ctypes.c_uint32)]


def is_audio_playing() -> bool:
    """True if the default output device is currently rendering audio."""
    try:
        ca = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreAudio.framework/CoreAudio")
        ca.AudioObjectGetPropertyData.restype = ctypes.c_int32

        # default output device id
        dev = ctypes.c_uint32(0)
        size = ctypes.c_uint32(4)
        addr = _Addr(_fourcc("dOut"), _fourcc("glob"), 0)
        if ca.AudioObjectGetPropertyData(1, ctypes.byref(addr), 0, None,
                                         ctypes.byref(size), ctypes.byref(dev)) != 0 or not dev.value:
            return False

        # is that device running somewhere (i.e. something is playing)?
        running = ctypes.c_uint32(0)
        size2 = ctypes.c_uint32(4)
        addr2 = _Addr(_fourcc("gone"), _fourcc("glob"), 0)
        if ca.AudioObjectGetPropertyData(dev.value, ctypes.byref(addr2), 0, None,
                                         ctypes.byref(size2), ctypes.byref(running)) != 0:
            return False
        return running.value != 0
    except Exception:
        return False


def _post(key: int, is_down: bool) -> None:
    flags = 0xA00 if is_down else 0xB00
    data1 = (key << 16) | ((0xA if is_down else 0xB) << 8)
    ev = NSEvent.otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_(
        NSSystemDefined, (0.0, 0.0), flags, 0, 0, None, 8, data1, -1)
    CGEventPost(kCGHIDEventTap, ev.CGEvent())


def play_pause() -> None:
    """Toggle play/pause on the system's current media."""
    try:
        _post(NX_KEYTYPE_PLAY, True)
        _post(NX_KEYTYPE_PLAY, False)
    except Exception:
        pass
