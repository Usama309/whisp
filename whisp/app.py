import math
import queue
import threading
import time
import webbrowser

import rumps

from whisp import config, media, permissions, sounds, sysaudio
from whisp.audio import Recorder, archive_recording, prewarm_microphone, is_silent
from whisp.factory import build_pipeline
from whisp.net import is_online
from whisp.transcribe.router import choose_engine
from whisp.history import HistoryStore
from whisp.hotkey import HotkeyListener, FnHotkeyListener
from whisp.inserter import copy_to_clipboard
from whisp.logs import log, log_path
from whisp.settings import Settings
from whisp.ui.server import start_server

# Menu-bar animation
IDLE_ICON = "🎙"
SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
BLOCKS = "▁▂▃▄▅▆▇█"
ANIM_INTERVAL = 0.1

_STATUS = {
    "idle": "● Ready",
    "recording": "● Recording…",
    "processing": "⠿ Transcribing…",
    "nospeech": "○ No speech detected",
    "error": "⚠ Error",
    "paused": "‖ Paused",
    "needsperm": "⚠ Enable Accessibility in System Settings",
}
# transient states auto-revert to idle after this many animation ticks
_FLASH_TICKS = {"nospeech": 14, "error": 22}


class WhispApp(rumps.App):
    def __init__(self):
        super().__init__(config.APP_NAME, title=IDLE_ICON, quit_button=None)
        self.settings = Settings.load()
        self.recorder = None
        self.paused = False
        self.listener = None
        self._listener_started = False
        self._hands_free = False
        self._session = 0
        self._muted_by_us = False
        self._media_paused = False

        # animation state (rendered by a main-thread timer; workers only set it)
        self._anim_state = "idle"
        self._status_detail = None
        self._frame = 0
        self._flash_left = 0

        self._status_item = rumps.MenuItem("● Ready")   # disabled status line
        self._pause_item = rumps.MenuItem("Pause", callback=self.toggle_pause)
        self.menu = [
            self._status_item,
            None,
            rumps.MenuItem("Copy Last Transcription", callback=self.copy_last),
            rumps.MenuItem("History", callback=self.open_history),
            rumps.MenuItem("Settings", callback=self.open_settings),
            None,
            rumps.MenuItem("Grant Accessibility…", callback=self.grant_accessibility),
            rumps.MenuItem("Open Log", callback=self.open_log),
            self._pause_item,
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

        self._server_port = start_server(self.settings)
        self._actions = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()
        threading.Thread(target=prewarm_microphone, daemon=True).start()

        # Drive the menu-bar animation on the main run loop.
        self._anim_timer = rumps.Timer(self._animate, ANIM_INTERVAL)
        self._anim_timer.start()

        self._ensure_permission_then_listen()

    # ---------------- animation (main thread) ----------------
    def _set_state(self, state, detail=None):
        self._status_detail = detail
        self._frame = 0
        self._flash_left = _FLASH_TICKS.get(state, 0)
        self._anim_state = state

    def _animate(self, _):
        state = self._anim_state
        if state == "recording":
            self.title = self._equalizer()
        elif state == "processing":
            self.title = SPINNER[self._frame % len(SPINNER)]
        elif state == "nospeech":
            self.title = "◌"
        elif state == "error":
            self.title = "⚠️"
        elif state == "paused":
            self.title = "‖"
        elif state == "needsperm":
            self.title = "⚠️"
        else:
            self.title = IDLE_ICON

        status = _STATUS.get(state, "● Ready")
        if state == "error" and self._status_detail:
            status = f"⚠ {self._status_detail}"
        self._status_item.title = status

        self._frame += 1
        if self._flash_left:
            self._flash_left -= 1
            if self._flash_left == 0:
                self._anim_state = "paused" if self.paused else "idle"

    def _equalizer(self):
        level = getattr(self.recorder, "level", 0.0) if self.recorder else 0.0
        bars = ""
        for i in range(3):
            phase = (math.sin((self._frame + i * 3) * 0.7) + 1) / 2  # 0..1
            h = 0.15 + level * (0.6 + 0.8 * phase)
            bars += BLOCKS[max(0, min(7, int(h * 8)))]
        return bars

    # ---------------- permissions ----------------
    def _ensure_permission_then_listen(self):
        if permissions.is_trusted():
            self._start_listener()
            return
        permissions.prompt_accessibility()
        permissions.open_accessibility_settings()
        self._set_state("needsperm")
        threading.Thread(target=self._poll_permission, daemon=True).start()

    def _poll_permission(self):
        while not permissions.is_trusted():
            time.sleep(2)
        self._start_listener()
        self._set_state("idle")

    def _start_listener(self):
        if self._listener_started:
            return
        hk = self.settings.get("hotkey", config.DEFAULT_HOTKEY)
        if hk.get("mode") == "fn":
            self.listener = FnHotkeyListener(on_action=self._on_fn_action)
        else:
            combo = hk.get("combo") or [hk.get("keyCode", 56)]
            self.listener = HotkeyListener(
                combo=combo, lock_keycode=hk.get("lockKeyCode"),
                on_press=self._on_press, on_release=self._on_release, on_lock=self._on_lock,
            )
        self.listener.start()
        self._listener_started = True

    def grant_accessibility(self, _):
        permissions.prompt_accessibility()
        permissions.open_accessibility_settings()

    # ---------------- event-tap callbacks: enqueue only (instant) ----------------
    def _on_press(self):
        self._actions.put("press")

    def _on_release(self):
        self._actions.put("release")

    def _on_lock(self, kind):
        self._actions.put(("lock", kind))

    def _on_fn_action(self, action):
        self._actions.put(("fn", action))

    # ---------------- worker thread ----------------
    def _worker(self):
        while True:
            action = self._actions.get()
            try:
                self._handle_action(action)
            except Exception as exc:
                self.recorder = None
                self._hands_free = False
                self._resume_media()
                self._set_state("error", detail=str(exc)[:80])

    def _handle_action(self, action):
        if action == "press":
            if self.paused or self.recorder is not None:
                return
            self._start_recording()
        elif action == "release":
            if self.paused or self.recorder is None or self._hands_free:
                return
            self._stop_and_process()
        elif isinstance(action, tuple) and action[0] == "lock":
            kind = action[1]
            if self.paused:
                return
            if self._hands_free:
                self._hands_free = False
                if self.recorder is not None:
                    self._stop_and_process()
            elif kind == "double" and self.recorder is None:
                self._hands_free = True
                self._start_recording()
        elif isinstance(action, tuple) and action[0] == "fn":
            self._handle_fn(action[1])

    def _handle_fn(self, cmd):
        if self.paused:
            return
        if cmd == "rec":
            if self.recorder is None:
                self._begin_capture()
        elif cmd == "confirm":
            self._pause_media()
            self._mute_output_async()
            self._cue("start")
            self._set_state("recording")
        elif cmd == "process":
            self._hands_free = False
            self._stop_and_process()
        elif cmd == "discard":
            self._discard_capture()
        elif cmd == "lock":
            self._discard_capture()
            self._hands_free = True
            self._begin_capture()
            self._pause_media()
            self._mute_output_async()
            self._cue("start")
            self._set_state("recording")
        elif cmd == "unlock":
            self._hands_free = False
            self._stop_and_process()

    # ---------------- recording ----------------
    def _pause_media(self):
        # Only act if sound is genuinely playing.
        if not self.settings.get("pause_media_while_recording", True):
            return
        if not media.is_audio_playing():
            return
        media.play_pause()
        self._media_paused = True
        # The media key is a toggle. If "is_audio_playing" was a false positive
        # (e.g. a cue sound) over a PAUSED song, the key just STARTED it. Pausing
        # releases the output device within ~0.15s, so re-check shortly after: if
        # audio is still playing, we started a paused song -> undo it.
        threading.Thread(target=self._verify_media_pause,
                         args=(self._session,), daemon=True).start()

    def _verify_media_pause(self, session):
        time.sleep(0.35)
        if session != self._session:
            return   # recording already ended; resume is handled on stop
        if media.is_audio_playing():
            media.play_pause()        # we started a paused source -> re-pause it
            self._media_paused = False

    def _resume_media(self):
        if self._media_paused:
            media.play_pause()
            self._media_paused = False

    def _begin_capture(self):
        self.recorder = Recorder(device=self.settings.get("microphone"),
                                 denoise=self.settings.get("noise_reduction", True))
        self.recorder.start()

    def _discard_capture(self):
        if self.recorder is not None and not self._hands_free:
            recorder, self.recorder = self.recorder, None
            try:
                recorder.stop()
            except Exception:
                pass
        if getattr(self, "_muted_by_us", False):
            sysaudio.unmute_output()
            self._muted_by_us = False
        self._set_state("idle")

    def _cue(self, name):
        if self.settings.get("sounds_enabled", True):
            sounds.play(name)

    def _start_recording(self):
        self._session += 1
        self._pause_media()
        self._mute_output_async()
        self._cue("start")
        self.recorder = Recorder(device=self.settings.get("microphone"),
                                 denoise=self.settings.get("noise_reduction", True))
        self.recorder.start()
        self._set_state("recording")

    def _mute_output_async(self):
        # Mute the system output while recording so the mic can't pick up
        # playing audio. Done on a short delay so the "start" cue still plays.
        if not self.settings.get("mute_while_recording", False):
            return
        sid = self._session
        threading.Thread(target=self._delayed_mute, args=(sid,), daemon=True).start()

    def _delayed_mute(self, sid):
        time.sleep(0.25)
        if sid == self._session and self.recorder is not None and not sysaudio.is_output_muted():
            sysaudio.mute_output()
            self._muted_by_us = True

    def _stop_and_process(self):
        self._session += 1
        recorder, self.recorder = self.recorder, None
        if getattr(self, "_muted_by_us", False):
            sysaudio.unmute_output()   # unmute before the stop cue so it's audible
            self._muted_by_us = False
        self._cue("stop")
        self._set_state("processing")
        self._resume_media()      # restore any paused playback immediately on release
        entry = None
        try:
            log("STOP  stopping recorder...")
            wav_path, duration = recorder.stop()
            log(f"STOP  recorder stopped (dur={duration:.1f}s); checking silence...")
            if not is_silent(wav_path):
                audio_url = archive_recording(wav_path)
                log("STOP  archived; running pipeline...")
                settings = Settings.load()
                try:
                    pipeline = build_pipeline(settings)
                    entry = pipeline.run(wav_path=wav_path, duration=duration, audio_url=audio_url)
                except Exception as exc:
                    # Groq path failed (bad key, quota, outage). Retry on the
                    # bundled whisper.cpp so the dictation still completes.
                    if choose_engine(settings.get("groq_api_key", ""), is_online()) != "groq":
                        raise
                    log(f"PIPELINE  groq failed ({str(exc)[:80]}); retrying local whisper.cpp")
                    pipeline = build_pipeline(settings, force_local=True)
                    entry = pipeline.run(wav_path=wav_path, duration=duration, audio_url=audio_url)
        except Exception as exc:
            self._set_state("error", detail=str(exc)[:80])
            return
        if entry is not None:
            self._cue("done")
            self._set_state("idle")
        else:
            self._cue("empty")
            self._set_state("nospeech")   # shown in the menu bar, no popup

    # ---------------- menu ----------------
    def copy_last(self, _):
        entries = HistoryStore().list()
        if entries:
            copy_to_clipboard(entries[0].text)
            self._set_state("idle")
            self._status_item.title = "● Copied last transcription"

    def open_log(self, _):
        import subprocess
        subprocess.run(["open", "-R", str(log_path())], check=False)

    def open_history(self, _):
        webbrowser.open(f"http://127.0.0.1:{self._server_port}/")

    def open_settings(self, _):
        webbrowser.open(f"http://127.0.0.1:{self._server_port}/settings")

    def toggle_pause(self, item):
        self.paused = not self.paused
        item.title = "Resume" if self.paused else "Pause"
        self._set_state("paused" if self.paused else "idle")


def main():
    WhispApp().run()


if __name__ == "__main__":
    main()
