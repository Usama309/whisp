import threading

from Quartz import (
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRun,
    CGEventTapCreate,
    CGEventTapEnable,
    kCGEventFlagsChanged,
    kCGEventKeyDown,
    kCGEventKeyUp,
    kCGEventTapOptionListenOnly,
    kCGHeadInsertEventTap,
    kCGSessionEventTap,
    CGEventGetIntegerValueField,
    kCGKeyboardEventKeycode,
    kCFRunLoopCommonModes,
)

FN_KEYCODE = 63


class HotkeyListener:
    """Calls on_press()/on_release() while the configured key is held.

    For modifier-only keys (Fn, keyCode 63) we watch flagsChanged transitions.
    For normal keys we watch keyDown/keyUp.
    """

    def __init__(self, keycode: int, modifier_only: bool, on_press, on_release):
        self._keycode = keycode
        self._modifier_only = modifier_only
        self._on_press = on_press
        self._on_release = on_release
        self._held = False
        self._tap = None
        self._thread = None

    def _handle(self, proxy, etype, event, refcon):
        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        if self._modifier_only:
            if etype == kCGEventFlagsChanged and keycode == self._keycode:
                # toggle: first flagsChanged = press, next = release
                if not self._held:
                    self._held = True
                    self._on_press()
                else:
                    self._held = False
                    self._on_release()
        else:
            if etype == kCGEventKeyDown and keycode == self._keycode and not self._held:
                self._held = True
                self._on_press()
            elif etype == kCGEventKeyUp and keycode == self._keycode and self._held:
                self._held = False
                self._on_release()
        return event

    def _run(self):
        mask = (
            (1 << kCGEventKeyDown)
            | (1 << kCGEventKeyUp)
            | (1 << kCGEventFlagsChanged)
        )
        self._tap = CGEventTapCreate(
            kCGSessionEventTap, kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly, mask, self._handle, None,
        )
        if self._tap is None:
            raise RuntimeError("Failed to create event tap (grant Accessibility permission).")
        source = CFMachPortCreateRunLoopSource(None, self._tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)
        CGEventTapEnable(self._tap, True)
        CFRunLoopRun()

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
