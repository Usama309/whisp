# Whisp architecture

This page describes commit `6dc9f06` (2026-09-14) of this repository.

## What the app does

Whisp is a voice dictation app that lives in the Mac menu bar. By default you
hold the Fn key, speak and let go. Whisp turns the speech into text
(transcription), tidies the wording, pastes it where your cursor is and saves
it to a history. Transcription uses the Groq online AI service when a Groq
key is set and the service can be reached, and otherwise runs on the Mac.
History and settings pages come from a small web server on your own Mac.

## Modules and folders

- `packaging/launcher.py` is the start file. It calls `whisp/app.py`, which
  loads settings, starts the web server, a worker thread (a background line
  of work) and the key listener, then runs the menu-bar app.
- `whisp/` holds the app. `whisp/hotkey.py` watches the key,
  `whisp/audio.py` records to a WAV audio file, `whisp/factory.py` builds
  the steps, `whisp/dictation.py` runs them, `whisp/cleanup.py` tidies text,
  `whisp/inserter.py` pastes and `whisp/history.py` saves.
  `whisp/groq_client.py` sends requests to Groq; `whisp/net.py` checks it
  can be reached. `whisp/settings.py` loads saved choices over the defaults
  and folder locations in `whisp/config.py`.
- `whisp/transcribe/` turns audio into text: `whisp/transcribe/router.py`
  picks an engine, `whisp/transcribe/groq_stt.py` uses Groq and
  `whisp/transcribe/local_stt.py` runs the whisper-cli speech program.
- `whisp/ui/` is the local web server, `whisp/ui/server.py`, and its page
  templates, which load web fonts from an online font service.
- `tests/` holds the automated tests and shared setup, `tests/conftest.py`.
- `packaging/` holds scripts that prepare a developer machine, fetch the
  speech model and build the installable app.

## How data moves

1. `whisp/hotkey.py` sees the Fn key held, released or tapped twice and
   hands each gesture to `whisp/app.py`, which queues it for the worker.
2. The worker starts a recorder from `whisp/audio.py`. When you let go it
   stops it, gets a WAV file, skips silent audio, copies the file to the
   recordings folder and asks `whisp/factory.py` for a pipeline (the chain
   of processing steps).
3. `whisp/factory.py` reads the settings. If the groq_api_key setting holds
   a key and `whisp/net.py` reaches Groq, `whisp/transcribe/router.py` picks
   Groq, otherwise the local engine. The parts go to `whisp/dictation.py`.
4. `whisp/dictation.py` asks the engine for text. The Groq engine,
   `whisp/transcribe/groq_stt.py`, sends the audio off the Mac to Groq via
   `whisp/groq_client.py`; `whisp/transcribe/local_stt.py` keeps it local.
   Non-speech markers and phrases invented on silence are removed.
5. `whisp/cleanup.py` tidies the text. With a key, cleanup switched on and a
   connection, it sends the text off the Mac to Groq via
   `whisp/groq_client.py`; otherwise it applies local text rules.
6. `whisp/inserter.py` pastes the result through the clipboard, and
   `whisp/history.py` saves it as a JSON (plain text data) file.

If a Groq step fails, `whisp/app.py` reruns the pipeline on the local engine.
Audio uploaded on the history page takes the same steps through
`whisp/ui/server.py`, but is saved without being pasted.

## Running the tests

The tests use pytest, a Python test runner. From the repository root:

```bash
packaging/setup_dev.sh
source .venv/bin/activate
pytest -q
```

- The one-time setup script needs internet: it installs tools with Homebrew
  (a Mac package manager) and the Python packages in `requirements.txt`.
- Tests need macOS and those packages; several load Mac system bindings or
  sounddevice, which needs the PortAudio sound library. None opens the mic.
- Groq calls, the connection check and whisper-cli are replaced by fakes, so
  no Groq key, connection or speech model download is needed.
- `tests/conftest.py` points the WHISP_SUPPORT_DIR environment variable at a
  temporary folder, so tests using it leave your real app folder alone.
