from whisp.hotkey import ComboTracker, LEFT_SHIFT, LEFT_CONTROL


def tracker():
    return ComboTracker(combo=[LEFT_SHIFT, LEFT_CONTROL],
                        lock_keycode=LEFT_SHIFT, double_tap_seconds=0.4)


def test_holding_combo_fires_press_then_release():
    t = tracker()
    # shift down alone registers a lock "tap" (ignored by the app unless locked)
    assert t.on_flags_changed(LEFT_SHIFT, now=1.0) == ["tap"]
    assert t.on_flags_changed(LEFT_CONTROL, now=1.05) == ["press"]   # combo complete
    assert t.on_flags_changed(LEFT_CONTROL, now=1.5) == ["release"]  # combo broken
    assert t.on_flags_changed(LEFT_SHIFT, now=1.6) == []             # lifting shift


def test_double_tap_shift_alone_emits_double():
    t = tracker()
    assert t.on_flags_changed(LEFT_SHIFT, now=1.0) == ["tap"]   # first tap down
    assert t.on_flags_changed(LEFT_SHIFT, now=1.05) == []       # first tap up
    assert t.on_flags_changed(LEFT_SHIFT, now=1.2) == ["double"]  # second tap within window


def test_single_tap_emits_tap_for_unlock():
    t = tracker()
    # a lone, isolated shift tap emits "tap" (the app maps this to unlock when locked)
    assert t.on_flags_changed(LEFT_SHIFT, now=5.0) == ["tap"]


def test_holding_combo_does_not_double():
    t = tracker()
    t.on_flags_changed(LEFT_SHIFT, now=1.0)      # shift down -> tap
    t.on_flags_changed(LEFT_CONTROL, now=1.05)   # control cancels pending tap
    t.on_flags_changed(LEFT_CONTROL, now=1.5)    # control up
    t.on_flags_changed(LEFT_SHIFT, now=1.55)     # shift up
    # immediately start another push-to-talk; must NOT be read as a double-tap
    assert t.on_flags_changed(LEFT_SHIFT, now=1.7) == ["tap"]
    assert t.on_flags_changed(LEFT_CONTROL, now=1.72) == ["press"]


def test_two_shift_taps_too_far_apart_do_not_double():
    t = tracker()
    t.on_flags_changed(LEFT_SHIFT, now=1.0)
    t.on_flags_changed(LEFT_SHIFT, now=1.05)
    assert t.on_flags_changed(LEFT_SHIFT, now=2.0) == ["tap"]  # > 0.4s gap, not a double
