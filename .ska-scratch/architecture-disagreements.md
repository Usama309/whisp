# Doc–code disagreements (unit `doc-code-disagreements`)

Documents read in full: `README.md` (45 lines), `CLAUDE.md` (9 lines),
`docs/superpowers/specs/2026-06-09-whisp-willow-clone-design.md` (189 lines),
`docs/superpowers/plans/2026-06-09-whisp-implementation.md` (2235 lines).

Code read as text, with nothing imported or executed:
- every `.py` file under `whisp/`, including `whisp/transcribe/` and `whisp/ui/server.py`;
- `whisp/ui/templates/settings.html` in full, and the action, upload and font lines of `whisp/ui/templates/history.html`;
- `tests/conftest.py` and all 17 `tests/test_*.py`;
- every tracked file under `packaging/`, plus `requirements.txt` and `.gitignore`.

The only commands run were read-only: `wc`, `cat`, `sed -n`, `grep`, `git ls-files`, `git log`, `git grep -l`, `git status`, `ls`.

Attempt 2 note: attempt 1 left a version of this file on disk. Attempt 2 re-checked every entry against the code. All of them held. Attempt 2 added D35–D38 and the extra detail in S7.

Each entry gives: the quoted statement, its source document, the code file and function that differ, and what the code does.
Entries are grouped by source document. The "D" numbers are only for cross-reference.

## Disagreements

### README.md

- **D1.** "By default Whisp transcribes **on your Mac** (works offline, no signup, fully private)." — `README.md` (section "Better speed/quality").
  - Code: `whisp/config.py` (module-level `DEFAULT_SETTINGS`) sets `"groq_api_key": _BAKED_KEY`. That value is loaded from the gitignored module `whisp/_baked_key.py` when the module exists.
  - `whisp/transcribe/router.py::choose_engine` picks `"groq"` whenever a key is set and the machine is online. So a build made with a baked key sends audio to Groq by default.
  - `whisp/_baked_key.py` is absent from this working tree and has no git history, so a dev checkout does default to local.
  - Connection attempts without a key: `whisp/factory.py::build_pipeline` calls `whisp/net.py::is_online` on every dictation. `whisp/app.py::WhispApp._stop_and_process` also calls it when a pipeline fails. `is_online` opens a TCP connection to `api.groq.com:443` even when no key is set. No audio or text is sent, but the connection is attempted.
  - Fonts: `whisp/ui/templates/settings.html` and `whisp/ui/templates/history.html` load fonts from `fonts.googleapis.com`. Opening History or Settings therefore makes outside requests, which weakens "fully private".
- **D2.** "Menu-bar 🎙️ icon → **Settings** to change the hotkey, language, and tone." — `README.md` (section "Use").
  - Code: `whisp/ui/templates/settings.html` shows the hotkey only as a read-only pill (`settings.hotkey.name`) and has no tone field.
  - Its `save()` script posts only `language`, `local_model`, `groq_api_key`, `vocabulary_text` and five toggles.
  - `whisp/ui/server.py::save_settings` would accept any key, but no UI control sends `hotkey` or `tones`. Of the three things named, only the language can be changed from Settings.
- **D3.** "Uploads support WAV, MP3, M4A, FLAC, and OGG files up to 200 MB." — `README.md` (section "Use").
  - Code (minor; the server accepts more than stated): `whisp/config.py` `UPLOAD_EXTENSIONS` also allows `.aac`, `.aiff`, `.mp4` and `.webm`.
  - `whisp/ui/server.py::upload_audio` also accepts any file whose MIME type starts with `audio/`. The file picker in `history.html` has `accept="audio/*,…"`.
  - The 200 MB limit matches `MAX_UPLOAD_BYTES`.
- **D4.** "Built on Intel → runs on Intel and Apple Silicon (via Rosetta)." — `README.md` (section "Notes").
  - Code (incomplete rather than contradictory): `packaging/build_app_arm64.sh` builds a native arm64 app (`--target-arch arm64`, output `dist-arm64/`), using assets staged by `packaging/fetch_assets_arm64.sh`.
  - `packaging/pkg/scripts/postinstall` installs Rosetta for the Intel build. The README does not mention the native arm64 build or the `.pkg` installer script.
- **D35.** "Unsigned build (no paid Apple Developer account)." — `README.md` (section "Notes"); also "the app is unsigned" (section "Install").
  - Code (wording only): `packaging/build_app.sh` and `packaging/build_app_arm64.sh` run `codesign --force --deep --sign -` with `packaging/Whisp.entitlements`. The app is ad-hoc signed, not unsigned; there is no Developer ID signature or notarization.
  - Spec §9 ("ad-hoc codesign") agrees with the code.

### CLAUDE.md

- **D5.** "Tech stack: Python 3.11, rumps, pyobjc, sounddevice, Flask, whisper.cpp, Groq API." — `CLAUDE.md`.
  - Code (incomplete, not contradictory): the running code also depends on three libraries, all pinned in `requirements.txt`:
    - `numpy`, in `whisp/audio.py::reduce_noise` and `Recorder.stop`;
    - `soundfile`, in `whisp/audio.py::_normalize_with_soundfile`;
    - `requests`, in `whisp/groq_client.py::transcribe` and `chat`.
  - Tests use `pytest` (`requirements.txt`, `tests/conftest.py`).
  - Every item in the list is used, and Python 3.11 matches `packaging/setup_dev.sh`.
  - No statement in `CLAUDE.md` contradicts the code.

### Design spec (`docs/superpowers/specs/2026-06-09-whisp-willow-clone-design.md`)

- **D6.** Statements: "Mic → WAV (for STT) + `.opus` archive" (§2 table); "`ffmpeg` transcodes the WAV to `.opus` for the history archive." (§4.1 item 3); "`Recordings/<ts>.opus     # archived audio`" (§4.2). Also "**Recorder** (`sounddevice` + `soundfile`)" (§4.1 item 3).
  - Code: `whisp/audio.py::archive_recording` copies the WAV to `Recordings/recording_<timestamp>.wav`. Its docstring says "WAV is kept (rather than transcoding to opus)".
  - No code under `whisp/` calls ffmpeg. The only mention is a comment in `whisp/audio.py::_normalize_with_afconvert` about avoiding it.
  - `Recorder.stop` writes the WAV with the standard-library `wave` module. `soundfile` is used only to decode uploads (`_normalize_with_soundfile`).
- **D7.** "Fallback default **Right ⌘** if Fn proves unreliable on the host OS." (§4.1 item 2); "Default to Right ⌘; hotkey configurable" (§9 Risks table).
  - Code: `whisp/config.py` `DEFAULT_HOTKEY` is `mode: "fn"`. The alternative combo mode is Left Shift + Left Control (`combo: [56, 59]`) with lock key 56.
  - `whisp/app.py::WhispApp._start_listener` chooses `FnHotkeyListener` or the combo `HotkeyListener`.
  - Neither keycode 54 nor Right ⌘ appears anywhere under `whisp/` (grep). The default is Fn, and the fallback is a Shift+Control combo that must be set in `settings.json`, not Right ⌘.
- **D8.** "Hotkey is configurable in Settings." (§4.1 item 2) and "**Settings:** Groq API key, hotkey, STT model, mic, language (en-gb/en-us), tone/personalization per context, custom dictionary, paste-Enter toggle." (§4.1 item 8).
  - Missing controls: `whisp/ui/templates/settings.html` has no hotkey editor (only a read-only pill), no microphone selector and no tone editor.
  - `Recorder` does read `settings["microphone"]` (`whisp/app.py::WhispApp._begin_capture`), but the value can be changed only by editing `settings.json`.
  - Language is a free-text field described as "e.g. en, es, auto", not an en-gb/en-us choice. The model is a free-text `local_model` field.
  - `whisp/ui/server.py::settings_page` and `save_settings` serve and save the page.
  - Extra controls the spec does not list: mute while recording, sound cues, noise reduction and launch at login (`whisp/ui/server.py::set_launch_at_login`).
- **D9.** "Press → start recording; release → stop." (§4.1 item 2).
  - Code: `whisp/hotkey.py::FnGesture.press` emits `rec`/`arm`. `FnHotkeyListener._arm_timer` confirms a hold only after `hold_min=0.2` s.
  - When the press is shorter than that, `FnGesture.release` emits `discard`, and `WhispApp._discard_capture` in `whisp/app.py` throws the capture away. A short press does not produce a dictation.
  - The 400 ms double-tap hands-free toggle does match (`double_window=0.4`).
- **D10.** "`LocalTranscriber` — invokes a bundled `whisper-cli` (whisper.cpp) with `ggml-base.en.bin`; larger models downloadable in Settings." (§4.1 item 4).
  - Code: no download code exists under `whisp/`; grep for download or huggingface finds nothing.
  - `whisp/factory.py::model_path` looks for a bundled `ggml-<model>.bin`, then for `~/.whisp-models/ggml-<model>.bin`. Settings only stores the model name.
  - The only download is in the build script `packaging/fetch_assets.sh`.
- **D11.** "Context map: Slack/Messages → casual (+ optional lowercase); Mail → email style; Cursor/ChatGPT/Claude → prompt style; default → neutral." (§4.1 item 5).
  - Code: `whisp/context.py::style_key_for_app` returns `"work"` for any unlisted app.
  - `whisp/config.py` `DEFAULT_SETTINGS["tones"]["work"]` is "Clear and concise, direct, lightly formal.". The neutral tone (`"other"`) is never selected.
  - No lowercase option exists in `whisp/cleanup.py` or `whisp/context.py`.
  - The plan (Task 2.1, `test_unknown_app_is_work`) and `tests/test_context.py` agree with the code, not the spec.
- **D12.** "Offline or no key → skip LLM, apply a light local filler-strip + spelling normalization only" (§4.1 item 5); "Custom dictionary + spelling normalization" (§2 table); "Cleanup (Groq Llama) … offline=raw" (§4 diagram).
  - Code: `whisp/cleanup.py::local_fallback` strips fillers, turns spoken "new line / new paragraph / bullet point" into breaks, applies the custom dictionary, capitalises and adds a final full stop.
  - No en-gb/en-us spelling normalisation exists anywhere under `whisp/` (grep finds nothing).
  - The diagram's "offline=raw" is also wrong: offline output is the regex-cleaned text, not the raw transcript.
  - Two things the spec leaves out: `CleanupService.clean` falls back to `local_fallback` when Groq fails, and `CleanupService._clean_block` rejects model output that `looks_like_answer` flags.
- **D13.** "optional Enter (`pressEnterAfterDictation`)" (§4.1 item 6).
  - Code (naming only): the setting is `press_enter`, in `whisp/config.py` `DEFAULT_SETTINGS`, `whisp/factory.py::build_pipeline` and `whisp/inserter.py::paste_text`. The behaviour matches.
- **D14.** "menu: History · Settings · Pause · Quit" (§4 diagram) and "menu opens History/Settings …, toggles Pause, and Quits." (§4.1 item 1).
  - Code (the code has more): `whisp/app.py::WhispApp.__init__` also adds a status line, "Copy Last Transcription" (`copy_last`), "Grant Accessibility…" (`grant_accessibility`) and "Open Log" (`open_log`).
- **D15.** "Single source of truth: all tunables live in `settings.json`, read through one `Settings` accessor; no scattered constants." (§4.2).
  - Code: many tunables are module constants that `Settings` never reads. Examples:
    - `whisp/hotkey.py::FnHotkeyListener.__init__`: `hold_min=0.2`, `double_window=0.4`;
    - `whisp/audio.py::is_silent`: `threshold=200.0`, and `SAMPLE_RATE`;
    - `whisp/transcribe/chunking.py`: `CHUNK_SECONDS = 120`, `_RPM_LIMIT = 18`;
    - `whisp/cleanup.py::CleanupService.clean`: the 1200-word block threshold;
    - `whisp/config.py`: `GROQ_STT_MODEL`, `GROQ_CHAT_MODEL`, `MAX_UPLOAD_BYTES`;
    - `whisp/sounds.py`: `_SOUNDS`.
- **D16.** "The app works in **local Whisper mode immediately** — no signup." (§5).
  - Code: this holds only without a baked key, as in D1. `whisp/config.py` defaults `groq_api_key` to a baked key when `whisp/_baked_key.py` exists at build time.
  - With that key and a network connection, `whisp/transcribe/router.py::choose_engine` picks Groq.
- **D17.** "bundling: the Python runtime, all dependencies, `whisper-cli` + `ggml-base.en.bin`, and an `ffmpeg` binary." (§6).
  - Code: the `pyinstaller` invocations in `packaging/build_app.sh` and `packaging/build_app_arm64.sh` bundle `whisper-cli`, `ggml-base.en.bin` and the whisper/ggml dylibs, but no ffmpeg.
  - `packaging/fetch_assets.sh` stages no ffmpeg either. `packaging/setup_dev.sh` still installs ffmpeg with Homebrew.
- **D18.** "Documented in a `README` on the DMG." (§6).
  - Code: `packaging/build_app.sh` builds the DMG from `dist/Whisp.app` alone (create-dmg), or from `dist/Whisp.app` plus an `Applications` link (hdiutil fallback).
  - No README is copied in; grep for `README` in `packaging/*.sh` finds nothing.
- **D19.** "Built on Intel → x86_64 app; runs on Apple Silicon via Rosetta 2. A future `universal2` build is possible but out of scope for v1." (§6).
  - Code: `packaging/build_app_arm64.sh` builds a native arm64 app (`--target-arch arm64`) as well as the x86_64 one.
  - `packaging/pkg/scripts/postinstall` is a `.pkg` post-install script, a distribution route §6 does not mention. It installs Rosetta, removes quarantine and installs a LaunchAgent.
- **D20.** "**Integration (mocked network):** end-to-end record→transcribe→cleanup→insert with a fake recorder feeding a fixture WAV and a mocked Groq client." (§7).
  - Code: no such test exists. `tests/fixtures/` does not exist, and nothing under it is tracked.
  - `tests/test_dictation.py::test_pipeline_transcribes_cleans_inserts_and_records` uses a fake transcriber and lambda cleanup and inserter, with no recorder, WAV or Groq client.
  - The Groq client is mocked only in unit tests: `tests/test_cleanup.py` (`monkeypatch` of `whisp.cleanup.groq_client.chat`) and `tests/test_groq_stt.py`.
- **D21.** "Auto-fallback to local on error/429" (§9 Risks, Groq rate limits).
  - Code (mostly consistent, with a nuance): on a 429, `whisp/transcribe/chunking.py::_with_rate_limit_and_retry` first retries Groq with backoff, up to 4 attempts.
  - That retry applies only to multi-chunk recordings. Short recordings go straight through `transcribe_chunked` without the wrapper.
  - Only after the Groq pipeline raises does `whisp/app.py::WhispApp._stop_and_process` (or `whisp/ui/server.py::upload_audio`) rebuild the pipeline with `force_local=True`.
- **D36.** "**History:** searchable list, audio replay, copy, flag, delete." (§4.1 item 8) and the §4 diagram "History (search/replay/copy/flag/delete)".
  - Code (the code has more): `whisp/ui/server.py::upload_audio` (`POST /api/upload`), with the upload form in `history.html`, lets the user transcribe an audio file.
  - That path goes through `whisp/audio.py::normalize_uploaded_audio` and `whisp/dictation.py::DictationPipeline.run_uploaded`, which saves to history without pasting.
  - The spec has no upload path. The README does describe one.

### Implementation plan (`docs/superpowers/plans/2026-06-09-whisp-implementation.md`)

The plan embeds full code listings from an earlier stage. Almost every listing now differs from the tracked file. The main differences are below.

- **D22.** File Structure: "`audio.py             # Recorder (sounddevice) + opus archive via ffmpeg`"; "`router.py          # pick groq vs local; network reachability check`"; "`fixtures/hello.wav   # short spoken-audio fixture for integration tests`"; "`fetch_assets.sh      # download ggml model; locate whisper-cli + ffmpeg to bundle`".
  - Code: `whisp/audio.py::archive_recording` keeps the WAV and uses no ffmpeg (as in D6).
  - `whisp/transcribe/router.py::choose_engine` has no reachability check; that lives in `whisp/net.py::is_online`.
  - `tests/fixtures/hello.wav` does not exist. `packaging/fetch_assets.sh` stages no ffmpeg.
  - The tree also omits these tracked files:
    - modules: `whisp/factory.py`, `whisp/autostart.py`, `whisp/logs.py`, `whisp/permissions.py`, `whisp/sounds.py`, `whisp/sysaudio.py`, `whisp/transcribe/chunking.py`;
    - packaging: `packaging/build_app_arm64.sh`, `packaging/fetch_assets_arm64.sh`, `packaging/launcher.py`, `packaging/pkg/scripts/postinstall`;
    - tests: `test_artifacts.py`, `test_audio.py`, `test_chunking.py`, `test_factory.py`, `test_fn_gesture.py`, `test_hotkey.py`, `test_vocab.py`.
- **D23.** "**Tech Stack:** Python 3.11, rumps, pyobjc (Quartz/AppKit), sounddevice + soundfile, requests, Flask, whisper.cpp (`whisper-cli`), ffmpeg, PyInstaller, create-dmg." and the Task 0.1 `requirements.txt` listing, which has no numpy.
  - Code: ffmpeg is not used by `whisp/` and not bundled by `packaging/build_app.sh` (see D17).
  - `requirements.txt` also pins `numpy==2.1.3`, which `whisp/audio.py` imports.
- **D24.** Task 1.1: "`# Default hotkey: Fn (keyCode 63), modifier-only hold. Fallback: Right Command (keyCode 54).`" / "`DEFAULT_HOTKEY = {"keyCode": 63, "keyName": "Fn", "isModifierOnly": True}`" / "`"groq_api_key": "",`".
  - Code: `whisp/config.py` has `DEFAULT_HOTKEY = {"mode": "fn", "name": "Fn", "combo": [56, 59], …, "lockKeyCode": 56}` and defaults `groq_api_key` to `_BAKED_KEY`.
  - It also has the extra settings `mute_while_recording`, `noise_reduction` and `sounds_enabled`.
  - Task 1.2's test asserts `s.get("hotkey")["keyCode"] == 63` and `groq_api_key == ""`. The actual `tests/test_settings.py::test_defaults_when_no_file` asserts `combo == [56, 59]`, `lockKeyCode == 56` and that the key is a string.
- **D25.** Task 2.2 `groq_client.transcribe(api_key, wav_path, language="en")` with `timeout=60`.
  - Code: `whisp/groq_client.py::transcribe` takes an extra `prompt` (vocabulary priming), sends `temperature "0"`, and uses `timeout=(8, 180)`.
- **D26.** Task 2.3 `CleanupService.clean` makes one `groq_client.chat` call and silently falls back ("`pass  # fall through to local`"). Its prompt begins "You are a dictation cleanup engine…".
  - Code: `whisp/cleanup.py::CleanupService.clean` splits transcripts over 1200 words into blocks (`_split_into_blocks`).
  - `_clean_block` tries twice, rejects answer-like output via `looks_like_answer`, and logs.
  - `build_system_prompt` is a different, much longer "TRANSCRIPTION FORMATTER" prompt. `local_fallback` also handles spoken formatting commands.
- **D27.** Task 3.1 `whisp/transcribe/base.py` holds only `TranscriptionResult`.
  - Code: `whisp/transcribe/base.py` also defines `strip_artifacts` and `is_hallucination`, which `whisp/dictation.py::DictationPipeline._prepare` uses.
- **D28.** Task 3.2 `GroqTranscriber.transcribe` makes one `groq_client.transcribe` call. Task 3.3 `LocalTranscriber.transcribe` runs one `subprocess.run(..., timeout=300)`.
  - Code: `whisp/transcribe/groq_stt.py::GroqTranscriber.transcribe` and `whisp/transcribe/local_stt.py::LocalTranscriber.transcribe` both go through `whisp/transcribe/chunking.py::transcribe_chunked`. It splits audio into 120 s chunks, run in parallel for Groq and in sequence for local.
  - `LocalTranscriber._transcribe_one` adds `-t <threads>` and a 180 s per-chunk timeout.
- **D29.** Task 4.1: "This module wraps hardware I/O; it is verified manually rather than unit-tested." The plan's `Recorder` uses a PortAudio callback, and its `archive_as_opus` uses ffmpeg.
  - Code: `tests/test_audio.py` unit-tests `whisp/audio.py` (`normalize_uploaded_audio`, `reduce_noise`, `Recorder`).
  - `whisp/audio.py::Recorder._record_loop` uses a blocking read on its own thread, with optional denoise.
  - `archive_as_opus` does not exist; `archive_recording` writes a WAV.
- **D30.** Task 5.2: "Global event tap; verified manually." The plan's `HotkeyListener(keycode, modifier_only, on_press, on_release)` toggles on each flagsChanged event.
  - Code: `whisp/hotkey.py` has the pure state machines `ComboTracker` and `FnGesture`, plus `FnHotkeyListener` and `HotkeyListener(combo, on_press, on_release, lock_keycode, on_lock, …)`.
  - The state machines are unit-tested by `tests/test_hotkey.py` and `tests/test_fn_gesture.py`.
- **D31.** Task 6.1 `DictationPipeline.run` has no artifact filtering and no upload path. Task 6.2 has `build_pipeline(settings)`.
  - Code: `whisp/dictation.py::DictationPipeline._prepare` strips artifacts and drops hallucinations. `run_uploaded` saves to history without pasting (`app_context="Audio upload"`).
  - `whisp/factory.py::build_pipeline(settings, force_local=False)` adds `stt_vocabulary_prompt` and the forced-local safety net.
- **D32.** Task 7.1 `whisp/app.py`: the hotkey callback starts the recorder directly, and `_process` runs on a new thread. Failures raise `rumps.notification(config.APP_NAME, "Dictation failed", …)`, the icons are 🔴/⏳, and "the menu has History/Settings/Pause/Quit".
  - Code: `whisp/app.py::WhispApp` queues hotkey actions to one `_worker` thread (`_handle_action`, `_handle_fn`).
  - `_stop_and_process` checks `is_silent`, archives, runs the pipeline and retries locally after a Groq failure.
  - Errors are shown in the menu-bar status ("shown in the menu bar, no popup"), not as notifications; `rumps.notification` is not called anywhere.
  - It also plays sound cues and optionally mutes output. The menu differs as in D14.
- **D33.** Task 8.1 `whisp/ui/server.py` and templates: routes `/`, `/settings`, delete, flag and settings save only; `template_folder="templates"`; `settings.html` fields are key, language, local model, cleanup and press-enter.
  - Code: `whisp/ui/server.py::create_app` adds `/audio/<entry_id>` (`audio`), `/api/launch-at-login` (`set_launch_at_login`), `/api/upload` (`upload_audio`) and a 413 handler.
  - `save_settings` parses vocabulary, and `_ui_dir` resolves template paths for PyInstaller.
  - The templates are fully redesigned and load Google Fonts.
- **D34.** Task 9.1 `fetch_assets.sh` copies ffmpeg and collects dylibs with an `otool` loop. Task 9.2 `build_app.sh` runs `pip install pyinstaller==6.10.0`, bundles `packaging/assets/ffmpeg`, and uses create-dmg only.
  - Code: `packaging/fetch_assets.sh` copies named whisper/ggml libraries from Homebrew paths, rewrites them to `@loader_path` with `install_name_tool`, and re-signs. It has no ffmpeg.
  - `packaging/build_app.sh` runs `pip install --quiet --upgrade pyinstaller` (unpinned), bundles the dylibs and `soundfile`, and falls back to `hdiutil`.
- **D37.** Task 8.1 test list ("`test_history_page_lists_entries`, `test_api_delete`, `test_api_flag`, `test_settings_save`"; "Expected: PASS (4 passed)").
  - Code: `tests/test_ui_server.py` also has `test_upload_transcribes_and_adds_history_without_pasting` and `test_upload_rejects_non_audio_file`, which exercise `whisp/ui/server.py::upload_audio`.
  - `tests/test_cleanup.py` likewise adds `test_local_fallback_handles_spoken_formatting_commands` and `test_looks_like_answer_detects_responses`, beyond the plan's 5 tests.

### Code-internal text that disagrees with code (noticed while comparing; not one of the four documents)

- **D38.** "🔒 Everything runs on your Mac. Recordings & transcripts stay on your device; only the audio sent for transcription leaves." — `whisp/ui/templates/settings.html` (footer note).
  - Code: when a key is set and the machine is online, `whisp/cleanup.py::CleanupService._clean_block` sends the transcript text to Groq through `whisp/groq_client.py::chat` (`GROQ_CHAT_URL`). So transcript text leaves the machine as well as audio.
  - The page itself also loads Google Fonts (see D1).
  - This was recorded because it bears on the same "does data leave the machine" question as D1. It is a template string, not one of the four prose documents.

### Checked and found consistent (for cross-checking against the claim map)

- **Entry point.** The entry point is `whisp/app.py::main` (and `__main__`), and `packaging/launcher.py` imports `whisp.app.main`. The plan agrees.
- **Engine choice.** Groq is used only when a key is set and `is_online()` is true; otherwise local (`whisp/transcribe/router.py::choose_engine`). This matches spec §4.1 item 4 and `tests/test_router.py`.
- **Off-machine sends.** Data goes only to Groq:
  - `whisp/groq_client.py::transcribe` sends audio to `GROQ_STT_URL`;
  - `whisp/groq_client.py::chat` sends transcript text to `GROQ_CHAT_URL`;
  - both URLs are under `https://api.groq.com/openai/v1`;
  - `whisp/net.py::is_online` makes a bare TCP connect to `api.groq.com:443`;
  - the UI pages load Google Fonts from the browser (see D1).
- **Pipeline order.** The pipeline runs transcribe → cleanup → paste → save to history (`whisp/dictation.py::DictationPipeline._save`), which matches README "How it works". The recording is archived before transcription (`whisp/app.py::WhispApp._stop_and_process`).
- **History storage.** Each entry is one JSON file, `<support dir>/Transcripts/<ID>.json`.
  - Its keys are `id, isFlagged, audioURL, recordingDuration, text, rawText, appContext, date` (`whisp/history.py::TranscriptEntry.to_json`).
  - The support dir is `~/Library/Application Support/com.usama.whisp` unless `WHISP_SUPPORT_DIR` is set (`whisp/config.py::support_dir`).
  - This matches spec §4.1 item 7 and §4.2.
- **Settings.** Settings live in `settings.json` in the support dir, with defaults merged in by `whisp/settings.py::Settings.load`.
- **Inserter.** `whisp/inserter.py::paste_text` saves the clipboard, sets the text, sends Cmd+V, optionally presses Enter, then restores the clipboard. This matches spec §4.1 item 6.
- **Local UI.** Flask runs on `127.0.0.1` with an ephemeral port (`whisp/ui/server.py::start_server`). The menu opens it in the browser (`whisp/app.py::WhispApp.open_history` / `open_settings`).
  - History supports search, play, copy, flag and delete (`history.html`).
  - This matches spec §4.1 item 8, apart from the Settings gaps in D8 and the upload path in D36.
- **Hands-free and tone mapping.** A double-tap within 400 ms locks hands-free, and a tap unlocks (`whisp/hotkey.py::FnGesture`). This matches spec §4.1 item 2. Slack/Messages → casual, Mail → email and Cursor/ChatGPT/Claude → prompt match spec §4.1 item 5 (`whisp/context.py`).
- **Running tests.**
  - What the docs say: README has "`source .venv/bin/activate`" then "`pytest -q`"; plan Task 9.4 has "`source .venv/bin/activate && pytest -q`".
  - What the repository has: `requirements.txt` pins `pytest==8.3.2`. `packaging/setup_dev.sh` creates `.venv` with python3.11 and installs the requirements. The `tests/conftest.py` fixture `support_dir` sets `WHISP_SUPPORT_DIR` to a temp dir.
  - These agree; no contradiction was found. `grep -rniE 'docs|architecture' tests` (on `*.py`) finds no match.
- **README install and permissions.** The README asks for Microphone and Accessibility. `whisp/permissions.py` handles the Accessibility prompts. `whisp/audio.py::prewarm_microphone` triggers the microphone prompt. `packaging/build_app.sh` adds `NSMicrophoneUsageDescription`.
- **Uploads are not pasted.** "Uploaded audio is never pasted into the frontmost app." (`README.md`) matches `whisp/dictation.py::DictationPipeline.run_uploaded` (`insert=False`, fixed `app_context`) and `tests/test_dictation.py::test_uploaded_pipeline_records_without_pasting_or_reading_frontmost_app`.

## Security concerns

Reported only; nothing was changed.

- **S1: A baked-in Groq API key may ship inside the app (HIGH if used).**
  - `whisp/config.py` imports `GROQ_API_KEY` from the gitignored `whisp/_baked_key.py` and makes it the default `groq_api_key`.
  - `packaging/build_app.sh` passes `--collect-submodules whisp`. If that file exists at build time, the key is bundled into `Whisp.app` and `Whisp.dmg`, and anyone with the DMG can recover it.
  - Current state: the file is absent now and has no git history. `git grep -lE 'gsk_[A-Za-z0-9]{20,}'` finds no long key token in tracked files. No key value was read or reproduced.
- **S2: The local Flask server has no authentication, CSRF protection or Host-header check (MEDIUM).**
  - `whisp/ui/server.py::create_app` has no `before_request` hook, token, or Origin/Host check (grep finds none).
  - Any local process that finds the ephemeral port can do the following:
    - `GET /settings` renders the Groq API key into the HTML `value` attribute (`settings.html`).
    - `POST /api/settings` (`save_settings`) overwrites any setting key with arbitrary JSON.
    - `POST /api/launch-at-login` (`set_launch_at_login`) writes and loads a LaunchAgent via `whisp/autostart.py::enable`.
    - `POST /api/upload` runs transcription, which spends Groq quota.
  - Because the Host header is not checked, a DNS-rebinding web page that finds the port could read `/settings`.
  - A multipart `POST /api/upload` counts as a CORS "simple request", so a cross-site form could trigger it if the port were known.
- **S3: Dictated text is written to a plain-text log (LOW/MEDIUM privacy).**
  - `whisp/dictation.py::DictationPipeline._save` logs up to 150 characters of both the raw and the cleaned text to `whisp.log` in the support dir (`whisp/logs.py::log_path`, rotating at 1 MB × 3).
  - Deleting a history entry (`whisp/history.py::HistoryStore.delete`) leaves that text in the log.
- **S4: Race-prone temp file creation (LOW).**
  - `tempfile.mktemp` is used in `whisp/audio.py::Recorder.stop` and `whisp/transcribe/chunking.py::_split`.
  - It is open to a time-of-check/time-of-use race on the temp path. Elsewhere the code uses `mkstemp`.
- **S5: The installer strips quarantine as root (LOW, by design).**
  - `packaging/pkg/scripts/postinstall` runs as root and removes `com.apple.quarantine` from `/Applications/Whisp.app`, bypassing Gatekeeper for an ad-hoc-signed app.
  - It also installs a KeepAlive LaunchAgent for the console user.
- **S6: Unverified download (LOW).**
  - `packaging/fetch_assets.sh` downloads `ggml-base.en.bin` from huggingface.co with `curl -L` and no checksum check.
  - The model is then bundled into the app.
- **S7: Third-party requests and an inaccurate privacy note in the "private" UI (LOW privacy).**
  - `whisp/ui/templates/settings.html` and `history.html` load Google Fonts, which exposes the user's IP address to Google each time a page opens.
  - `settings.html` also says "Everything runs on your Mac … only the audio sent for transcription leaves". The transcript text also goes to Groq for cleanup (D38).

## Rule conflicts

- **Imported user rules.** `CLAUDE.md` says it "Imports user rules from `~/.claude/CLAUDE.md`". That file is outside the repository and outside this unit's authorised reads, so it was not opened. Any conflict between those imported rules and this work is **unknown, not "none"**.
- **Command-like text in the plan.** The plan document contains text addressed to agents: "**For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development …" and "Every task ends with a commit."
  - It was treated as untrusted retrieved content and not followed.
  - Committing is out of scope for this work (`04-srs.md`, Out of scope).
- **ECC standards.** This unit wrote no code, so the Python coding-style standard (PEP 8, type annotations) had nothing to apply to. No conflict between the ECC standards and the plan arose.
- **Project rules.** No project rules are configured for client `none` / project `whisp`, so there was nothing to conflict with.
- **Write-policy note (attempt 1).** The attempt-1 write-policy report lists `.ska-scratch/architecture-evidence.md` and `.ska-scratch/architecture-report-notes.md` as created in a cohort that included this unit. This unit's authorised write is only `$SCRATCH/architecture-disagreements.md`. Attempt 2 did not create, edit or delete those two files and left them as found.
