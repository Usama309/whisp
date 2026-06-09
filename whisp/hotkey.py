import threading
import time

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

# macOS virtual key codes for the modifiers we use
LEFT_SHIFT = 56
LEFT_CONTROL = 59
RIGHT_SHIFT = 60
RIGHT_CONTROL = 62


class ComboTracker:
    """Pure state machine for modifier combos + double-tap lock (no Quartz).

    Feed it flagsChanged transitions (keycode + monotonic timestamp). It returns
    the high-level events that result: "press"/"release" for the held combo and
    "lock" when the lock key is double-tapped on its own.
    """

    def __init__(self, combo, lock_keycode=None, double_tap_seconds=0.4):
        self.combo = set(combo)
        self.lock_keycode = lock_keycode
        self.double_tap_seconds = double_tap_seconds
        self.down = set()
        self.active = False
        self.last_lock_tap = None

    def on_flags_changed(self, keycode, now):
        events = []
        if keycode in self.down:
            self.down.discard(keycode)
            going_down = False
        else:
            self.down.add(keycode)
            going_down = True

        other_combo = self.combo - {self.lock_keycode}

        # Starting any other combo key cancels a pending lock tap, so holding the
        # full combo never accidentally counts as a double-tap.
        if going_down and keycode in other_combo:
            self.last_lock_tap = None

        # Double-tap the lock key *alone* (no other combo key held) toggles lock.
        if (going_down and keycode == self.lock_keycode
                and not (other_combo & self.down)):
            if self.last_lock_tap is not None and (now - self.last_lock_tap) <= self.double_tap_seconds:
                self.last_lock_tap = None
                events.append("lock")
            else:
                self.last_lock_tap = now

        combo_held = self.combo.issubset(self.down)
        if combo_held and not self.active:
            self.active = True
            events.append("press")
        elif not combo_held and self.active:
            self.active = False
            events.append("release")
        return events


class HotkeyListener:
    """Global hold-to-talk listener: hold the combo to talk, double-tap the lock
    key for hands-free. Requires Accessibility permission.
    """

    def __init__(self, combo, on_press, on_release,
                 lock_keycode=None, on_toggle_lock=None, double_tap_seconds=0.4):
        self._tracker = ComboTracker(combo, lock_keycode, double_tap_seconds)
        self._on_press = on_press
        self._on_release = on_release
        self._on_toggle_lock = on_toggle_lock
        self._tap = None
        self._thread = None

    def _dispatch(self, event):
        if event == "press":
            self._on_press()
        elif event == "release":
            self._on_release()
        elif event == "lock" and self._on_toggle_lock:
            self._on_toggle_lock()

    def _handle(self, proxy, etype, event, refcon):
        if etype == kCGEventFlagsChanged:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            for ev in self._tracker.on_flags_changed(keycode, time.monotonic()):
                self._dispatch(ev)
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
