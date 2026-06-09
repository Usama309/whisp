from whisp.hotkey import ComboTracker, LEFT_SHIFT, LEFT_CONTROL


def tracker():
    return ComboTracker(combo=[LEFT_SHIFT, LEFT_CONTROL],
                        lock_keycode=LEFT_SHIFT, double_tap_seconds=0.4)


def test_holding_combo_fires_press_then_release():
    t = tracker()
    assert t.on_flags_changed(LEFT_SHIFT, now=1.0) == []        # shift down
    assert t.on_flags_changed(LEFT_CONTROL, now=1.05) == ["press"]  # control down -> combo
    assert t.on_flags_changed(LEFT_CONTROL, now=1.5) == ["release"]  # control up -> broken
    # lifting the remaining shift produces nothing
    assert t.on_flags_changed(LEFT_SHIFT, now=1.6) == []


def test_double_tap_shift_alone_locks():
    t = tracker()
    # tap 1: down then up
    assert t.on_flags_changed(LEFT_SHIFT, now=1.0) == []
    assert t.on_flags_changed(LEFT_SHIFT, now=1.05) == []
    # tap 2 within window -> lock
    assert t.on_flags_changed(LEFT_SHIFT, now=1.2) == ["lock"]


def test_holding_combo_does_not_lock():
    t = tracker()
    t.on_flags_changed(LEFT_SHIFT, now=1.0)      # shift down
    t.on_flags_changed(LEFT_CONTROL, now=1.05)   # control down (combo)
    t.on_flags_changed(LEFT_CONTROL, now=1.5)    # control up
    t.on_flags_changed(LEFT_SHIFT, now=1.55)     # shift up
    # immediately start another push-to-talk; control cancels any pending lock
    assert "lock" not in t.on_flags_changed(LEFT_SHIFT, now=1.7)
    assert t.on_flags_changed(LEFT_CONTROL, now=1.72) == ["press"]


def test_two_shift_taps_too_far_apart_do_not_lock():
    t = tracker()
    t.on_flags_changed(LEFT_SHIFT, now=1.0)
    t.on_flags_changed(LEFT_SHIFT, now=1.05)
    assert t.on_flags_changed(LEFT_SHIFT, now=2.0) == []  # > 0.4s gap
