import queue
import threading
import time
import webbrowser

import rumps

from whisp import config, permissions, sounds, sysaudio
from whisp.audio import Recorder, archive_recording, prewarm_microphone, is_silent
from whisp.factory import build_pipeline
from whisp.hotkey import HotkeyListener, FnHotkeyListener
from whisp.settings import Settings
from whisp.ui.server import start_server

IDLE = "🎙️"
RECORDING = "🔴"
WORKING = "⏳"


class WhispApp(rumps.App):
    def __init__(self):
        super().__init__(config.APP_NAME, title=IDLE, quit_button=None)
        self.settings = Settings.load()
        self.recorder = None
        self.paused = False
        self.listener = None
        self._listener_started = False
        self._hands_free = False
        self._session = 0
        self._muted_by_us = False
        self.menu = [
            rumps.MenuItem("History", callback=self.open_history),
            rumps.MenuItem("Settings", callback=self.open_settings),
            None,
            rumps.MenuItem("Grant Accessibility…", callback=self.grant_accessibility),
            rumps.MenuItem("Pause", callback=self.toggle_pause),
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]
        self._server_port = start_server(self.settings)
        # All recording work runs on this single worker, never on the event-tap
        # thread — so a slow/failing mic open can never disable the global hotkey.
        self._actions = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(target=prewarm_microphone, daemon=True).start()
        self._ensure_permission_then_listen()

    def _ensure_permission_then_listen(self):
        if permissions.is_trusted():
            self._start_listener()
            return
        # Not trusted yet: show the system prompt, open the settings pane, then
        # poll until the user flips the switch and start the hotkey automatically.
        permissions.prompt_accessibility()
        permissions.open_accessibility_settings()
        self.title = "⚠️"
        rumps.notification(
            config.APP_NAME, "Turn on Whisp to enable dictation",
            "System Settings → Privacy & Security → Accessibility → enable Whisp.",
        )
        threading.Thread(target=self._poll_permission, daemon=True).start()

    def _poll_permission(self):
        while not permissions.is_trusted():
            time.sleep(2)
        self._start_listener()
        self.title = IDLE
        rumps.notification(config.APP_NAME, "Whisp is ready 🎙️",
                           "Hold your hotkey, speak, and let go.")

    def _start_listener(self):
        if self._listener_started:
            return
        hk = self.settings.get("hotkey", config.DEFAULT_HOTKEY)
        if hk.get("mode") == "fn":
            self.listener = FnHotkeyListener(on_action=self._on_fn_action)
        else:
            combo = hk.get("combo") or [hk.get("keyCode", 56)]   # tolerate legacy single-key
            self.listener = HotkeyListener(
                combo=combo,
                lock_keycode=hk.get("lockKeyCode"),
                on_press=self._on_press,
                on_release=self._on_release,
                on_lock=self._on_lock,
            )
        self.listener.start()
        self._listener_started = True

    def grant_accessibility(self, _):
        permissions.prompt_accessibility()
        permissions.open_accessibility_settings()

    # --- event-tap callbacks: do NOTHING but enqueue (must be instant) ---
    def _on_press(self):
        self._actions.put("press")

    def _on_release(self):
        self._actions.put("release")

    def _on_lock(self, kind):
        self._actions.put(("lock", kind))

    def _on_fn_action(self, action):
        self._actions.put(("fn", action))

    # --- worker thread: owns all recording state and heavy work ---
    def _worker(self):
        while True:
            action = self._actions.get()
            try:
                self._handle_action(action)
            except Exception as exc:
                self.recorder = None
                self._hands_free = False
                self.title = IDLE
                rumps.notification(config.APP_NAME, "Dictation error", str(exc)[:120])

    def _handle_action(self, action):
        if action == "press":
            if self.paused or self.recorder is not None:
                return
            self._start_recording()
        elif action == "release":
            # Releasing the combo stops push-to-talk, but never interrupts hands-free.
            if self.paused or self.recorder is None or self._hands_free:
                return
            self._stop_and_process()
        elif isinstance(action, tuple) and action[0] == "lock":
            kind = action[1]   # "tap" or "double"
            if self.paused:
                return
            if self._hands_free:
                # Locked: any single tap (or double) of the lock key unlocks/stops.
                self._hands_free = False
                if self.recorder is not None:
                    self._stop_and_process()
            elif kind == "double" and self.recorder is None:
                # Double-tap locks: start hands-free recording.
                self._hands_free = True
                self._start_recording()
        elif isinstance(action, tuple) and action[0] == "fn":
            self._handle_fn(action[1])

    def _handle_fn(self, cmd):
        if self.paused:
            return
        if cmd == "rec":                 # begin tentative capture (silent)
            if self.recorder is None:
                self._begin_capture()
        elif cmd == "confirm":           # genuine hold -> show recording + cue
            self._cue("start")
            self.title = RECORDING
        elif cmd == "process":           # hold released -> transcribe
            self._hands_free = False
            self._stop_and_process()
        elif cmd == "discard":           # it was a tap -> drop the capture silently
            self._discard_capture()
        elif cmd == "lock":              # double-tap -> hands-free recording
            self._discard_capture()
            self._hands_free = True
            self._begin_capture()
            self._cue("start")
            self.title = RECORDING
        elif cmd == "unlock":            # tap while locked -> transcribe
            self._hands_free = False
            self._stop_and_process()

    def _begin_capture(self):
        self.recorder = Recorder(device=self.settings.get("microphone"))
        self.recorder.start()

    def _discard_capture(self):
        if self.recorder is not None and not self._hands_free:
            recorder, self.recorder = self.recorder, None
            try:
                recorder.stop()
            except Exception:
                pass
        self.title = IDLE

    def _cue(self, name):
        if self.settings.get("sounds_enabled", True):
            sounds.play(name)

    def _start_recording(self):
        # Keep this instant: cue + recorder start only. No sleeps, no osascript.
        self._session += 1
        self._cue("start")
        self.recorder = Recorder(device=self.settings.get("microphone"))
        self.recorder.start()
        self.title = RECORDING
        if self.settings.get("mute_while_recording", False):
            sid = self._session
            threading.Thread(target=self._delayed_mute, args=(sid,), daemon=True).start()

    def _delayed_mute(self, sid):
        # Mute slightly after start (off the hot path) so the start cue is audible
        # and the keypress feels instant. Guarded so a finished session never sticks.
        time.sleep(0.25)
        if sid == self._session and self.recorder is not None and not sysaudio.is_output_muted():
            sysaudio.mute_output()
            self._muted_by_us = True

    def _stop_and_process(self):
        self._session += 1                      # invalidate any pending delayed mute
        recorder, self.recorder = self.recorder, None
        self._cue("stop")                       # immediate "you released" feedback
        self.title = WORKING
        if getattr(self, "_muted_by_us", False):
            sysaudio.unmute_output()
            self._muted_by_us = False
        entry = None
        try:
            wav_path, duration = recorder.stop()
            if is_silent(wav_path):
                entry = None   # held the key but didn't speak -> skip (no hallucination)
            else:
                audio_url = archive_recording(wav_path)
                pipeline = build_pipeline(Settings.load())
                entry = pipeline.run(wav_path=wav_path, duration=duration, audio_url=audio_url)
        except Exception as exc:  # surface, never crash the menubar
            rumps.notification(config.APP_NAME, "Dictation failed", str(exc)[:120])
        finally:
            self.title = IDLE
        if entry is not None:
            self._cue("done")
        else:
            self._cue("empty")
            rumps.notification(config.APP_NAME, "No speech detected", "Nothing was transcribed.")

    def open_history(self, _):
        webbrowser.open(f"http://127.0.0.1:{self._server_port}/")

    def open_settings(self, _):
        webbrowser.open(f"http://127.0.0.1:{self._server_port}/settings")

    def toggle_pause(self, item):
        self.paused = not self.paused
        item.title = "Resume" if self.paused else "Pause"
        self.title = "⏸️" if self.paused else IDLE


def main():
    WhispApp().run()


if __name__ == "__main__":
    main()
