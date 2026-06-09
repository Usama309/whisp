from whisp.hotkey import FnGesture


def test_hold_is_push_to_talk():
    g = FnGesture(double_window=0.4)
    assert g.press(0.0) == ["rec", "arm"]      # start capture + arm hold timer
    assert g.confirm() == ["confirm"]          # held past threshold -> real hold
    assert g.release(1.5) == ["process"]       # release -> transcribe


def test_quick_tap_then_tap_locks():
    g = FnGesture(double_window=0.4)
    assert g.press(0.0) == ["rec", "arm"]
    assert g.release(0.1) == ["discard"]       # too short to be a hold -> tap
    assert g.press(0.2) == ["rec", "arm"]
    assert g.release(0.28) == ["discard", "lock"]   # second tap within window -> lock


def test_single_tap_while_locked_unlocks():
    g = FnGesture(double_window=0.4)
    # get into locked state via a double-tap
    g.press(0.0); g.release(0.1)
    g.press(0.2); g.release(0.28)
    assert g.state == FnGesture.LOCKED
    # a press+release now unlocks
    assert g.press(2.0) == []                  # press alone does nothing while locked
    assert g.release(2.1) == ["unlock"]


def test_two_taps_far_apart_do_not_lock():
    g = FnGesture(double_window=0.4)
    g.press(0.0); assert g.release(0.1) == ["discard"]
    g.press(1.0); assert g.release(1.1) == ["discard"]   # gap > window, no lock
    assert g.state == FnGesture.IDLE


def test_confirm_after_release_does_nothing():
    g = FnGesture(double_window=0.4)
    g.press(0.0)
    g.release(0.1)            # released before confirm -> back to idle/tap
    assert g.confirm() == []  # a late timer firing must not start recording
