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
    kCGEventTapDisabledByTimeout,
    kCGEventTapDisabledByUserInput,
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

        # Lock-key presses *alone* (no other combo key held) emit "tap" for a
        # single press and "double" for the second of a double-tap. The app uses
        # "double" to lock (start hands-free) and any tap to unlock (stop).
        if (going_down and keycode == self.lock_keycode
                and not (other_combo & self.down)):
            if self.last_lock_tap is not None and (now - self.last_lock_tap) <= self.double_tap_seconds:
                self.last_lock_tap = None
                events.append("double")
            else:
                self.last_lock_tap = now
                events.append("tap")

        combo_held = self.combo.issubset(self.down)
        if combo_held and not self.active:
            self.active = True
            events.append("press")
        elif not combo_held and self.active:
            self.active = False
            events.append("release")
        return events


FN_KEYCODE = 63
FN_FLAG_MASK = 0x800000  # kCGEventFlagMaskSecondaryFn


class FnGesture:
    """Pure state machine for a single Fn key doing hold / double-tap / single-tap.

    Emits high-level actions the app executes:
      - "rec"     : begin capturing audio now (silent; may be discarded)
      - "arm"     : start the hold-confirm timer
      - "confirm" : the press is a genuine hold -> push-to-talk (cue + recording UI)
      - "process" : hold released -> stop and transcribe
      - "discard" : it was a tap, not a hold -> throw away the tentative capture
      - "lock"    : double-tap -> start hands-free recording
      - "unlock"  : tap while locked -> stop and transcribe
    """

    IDLE, PENDING, PUSH, LOCKED = range(4)

    def __init__(self, double_window=0.4):
        self.double_window = double_window
        self.state = self.IDLE
        self.last_tap = None

    def press(self, now):
        if self.state == self.LOCKED:
            return []          # a press while locked unlocks on release
        if self.state == self.IDLE:
            self.state = self.PENDING
            return ["rec", "arm"]
        return []

    def confirm(self):
        if self.state == self.PENDING:
            self.state = self.PUSH
            return ["confirm"]
        return []

    def release(self, now):
        if self.state == self.LOCKED:
            self.state = self.IDLE
            return ["unlock"]
        if self.state == self.PUSH:
            self.state = self.IDLE
            self.last_tap = None
            return ["process"]
        if self.state == self.PENDING:
            actions = ["discard"]
            if self.last_tap is not None and (now - self.last_tap) <= self.double_window:
                self.last_tap = None
                self.state = self.LOCKED
                actions.append("lock")
            else:
                self.last_tap = now
                self.state = self.IDLE
            return actions
        return []


class FnHotkeyListener:
    """Global Fn-key listener implementing hold/double-tap/single-tap via FnGesture.
    Detects Fn through the secondary-Fn event flag. Requires Accessibility.
    """

    def __init__(self, on_action, hold_min=0.2, double_window=0.4):
        self._on_action = on_action          # callable(action_str)
        self._hold_min = hold_min
        self._gesture = FnGesture(double_window)
        self._lock = threading.Lock()
        self._timer = None
        self._tap = None
        self._thread = None

    def _emit(self, actions):
        for a in actions:
            if a == "arm":
                self._arm_timer()
            else:
                self._on_action(a)

    def _arm_timer(self):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(self._hold_min, self._confirm)
        self._timer.daemon = True
        self._timer.start()

    def _confirm(self):
        with self._lock:
            self._emit(self._gesture.confirm())

    def _press(self, now):
        with self._lock:
            self._emit(self._gesture.press(now))

    def _release(self, now):
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._emit(self._gesture.release(now))

    def _handle(self, proxy, etype, event, refcon):
        try:
            if etype in (kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput):
                if self._tap is not None:
                    CGEventTapEnable(self._tap, True)
                return event
            if etype == kCGEventFlagsChanged:
                keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                if keycode == FN_KEYCODE:
                    from Quartz import CGEventGetFlags
                    fn_down = bool(CGEventGetFlags(event) & FN_FLAG_MASK)
                    now = time.monotonic()
                    if fn_down:
                        self._press(now)
                    else:
                        self._release(now)
        except Exception:
            pass
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


class HotkeyListener:
    """Global hold-to-talk listener: hold the combo to talk, double-tap the lock
    key for hands-free. Requires Accessibility permission.
    """

    def __init__(self, combo, on_press, on_release,
                 lock_keycode=None, on_lock=None, double_tap_seconds=0.4):
        self._tracker = ComboTracker(combo, lock_keycode, double_tap_seconds)
        self._on_press = on_press
        self._on_release = on_release
        self._on_lock = on_lock          # callable(kind) where kind is "tap"/"double"
        self._tap = None
        self._thread = None

    def _dispatch(self, event):
        if event == "press":
            self._on_press()
        elif event == "release":
            self._on_release()
        elif event in ("tap", "double") and self._on_lock:
            self._on_lock(event)

    def _handle(self, proxy, etype, event, refcon):
        # This runs on the event-tap thread. It must NEVER block or raise, or
        # macOS disables the tap. Re-enable it if macOS ever does.
        try:
            if etype in (kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput):
                if self._tap is not None:
                    CGEventTapEnable(self._tap, True)
                return event
            if etype == kCGEventFlagsChanged:
                keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                for ev in self._tracker.on_flags_changed(keycode, time.monotonic()):
                    self._dispatch(ev)
        except Exception:
            pass
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
