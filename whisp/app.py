import threading
import time
import webbrowser

import rumps

from whisp import config, permissions
from whisp.audio import Recorder, archive_recording
from whisp.factory import build_pipeline
from whisp.hotkey import HotkeyListener
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
        self.menu = [
            rumps.MenuItem("History", callback=self.open_history),
            rumps.MenuItem("Settings", callback=self.open_settings),
            None,
            rumps.MenuItem("Grant Accessibility…", callback=self.grant_accessibility),
            rumps.MenuItem("Pause", callback=self.toggle_pause),
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]
        self._server_port = start_server(self.settings)
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
        combo = hk.get("combo") or [hk.get("keyCode", 56)]   # tolerate legacy single-key
        self.listener = HotkeyListener(
            combo=combo,
            lock_keycode=hk.get("lockKeyCode"),
            on_press=self._on_press,
            on_release=self._on_release,
            on_toggle_lock=self._on_toggle_lock,
        )
        self.listener.start()
        self._listener_started = True

    def grant_accessibility(self, _):
        permissions.prompt_accessibility()
        permissions.open_accessibility_settings()

    def _start_recording(self):
        self.title = RECORDING
        self.recorder = Recorder(device=self.settings.get("microphone"))
        self.recorder.start()

    def _stop_and_process(self):
        self.title = WORKING
        recorder, self.recorder = self.recorder, None
        threading.Thread(target=self._process, args=(recorder,), daemon=True).start()

    def _on_press(self):
        if self.paused or self.recorder is not None:
            return
        self._start_recording()

    def _on_release(self):
        # Releasing the combo stops push-to-talk, but never interrupts hands-free.
        if self.paused or self.recorder is None or self._hands_free:
            return
        self._stop_and_process()

    def _on_toggle_lock(self):
        if self.paused:
            return
        if self.recorder is None:
            self._hands_free = True
            self._start_recording()
        else:
            self._hands_free = False
            self._stop_and_process()

    def _process(self, recorder):
        try:
            wav_path, duration = recorder.stop()
            audio_url = archive_recording(wav_path)
            pipeline = build_pipeline(Settings.load())
            pipeline.run(wav_path=wav_path, duration=duration, audio_url=audio_url)
        except Exception as exc:  # surface, never crash the menubar
            rumps.notification(config.APP_NAME, "Dictation failed", str(exc)[:120])
        finally:
            self.title = IDLE

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
