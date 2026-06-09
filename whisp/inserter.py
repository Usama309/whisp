import time

from AppKit import NSPasteboard, NSStringPboardType
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGEventFlagMaskCommand,
    kCGHIDEventTap,
)

V_KEYCODE = 9          # 'v'
RETURN_KEYCODE = 36


def _set_clipboard(text: str):
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSStringPboardType)


def _get_clipboard() -> str:
    pb = NSPasteboard.generalPasteboard()
    return pb.stringForType_(NSStringPboardType) or ""


def _key(keycode, command=False):
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    if command:
        CGEventSetFlags(down, kCGEventFlagMaskCommand)
        CGEventSetFlags(up, kCGEventFlagMaskCommand)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def copy_to_clipboard(text: str):
    if text:
        _set_clipboard(text)


def paste_text(text: str, press_enter: bool = False):
    if not text:
        return
    previous = _get_clipboard()
    _set_clipboard(text)
    time.sleep(0.05)
    _key(V_KEYCODE, command=True)
    if press_enter:
        time.sleep(0.05)
        _key(RETURN_KEYCODE)
    time.sleep(0.2)
    _set_clipboard(previous)
