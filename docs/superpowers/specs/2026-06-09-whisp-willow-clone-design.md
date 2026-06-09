# Whisp — Free Willow Voice Clone (Design Spec)

**Date:** 2026-06-09
**Status:** Approved (design), pending implementation plan
**Owner:** Usama
**Working name:** Whisp (rename anytime)

---

## 1. Purpose

A personal, mostly-free macOS dictation app that replicates the productivity of
[Willow Voice](https://willowvoice.com/). Hold a hotkey, speak in any app, and the
spoken words are transcribed by a Whisper model, cleaned up by an LLM in the user's
own style, and pasted at the cursor. Every dictation is saved to a searchable history.

It must be **packageable as a single `.dmg`** that the user can hand to a friend, who
can run it on any Mac with **zero setup and no signup** (local Whisper out of the box),
optionally upgrading to cloud quality by pasting a free Groq API key.

## 2. Reverse-engineered Willow strategy (the thing we are replicating)

Confirmed by inspecting the installed app (`/Applications/Willow Voice.app`,
`com.seewillow.WillowMac`, v2.1.13) and its data:

| Aspect | Willow's implementation | Our replica |
|---|---|---|
| Trigger | Hold **Fn** (keyCode 63), global event tap; double-tap = hands-free | Hold Fn via CGEventTap; double-tap hands-free; configurable |
| Audio | Mic → **Opus** files in `Recordings/` | Mic → WAV (for STT) + `.opus` archive |
| Transcription | **Whisper** — cloud (`api.willowvoice.com`) + bundled local `whisper.cpp` offline mode | Groq `whisper-large-v3` (cloud) + bundled `whisper.cpp` local fallback |
| Cleanup | LLM pass (`TranscriptCleanupMonitor`, `llm_input_text`/`llm_output_text`), tone + app context aware | Groq `llama-3.3-70b` cleanup, tone + frontmost-app context |
| Insertion | Clipboard → simulated **Cmd+V** (`smartTextInsertion`) | NSPasteboard → CGEvent Cmd+V, restore prior clipboard |
| History | One JSON per dictation: `Transcripts/<UUID>.json` `{id, isFlagged, audioURL, recordingDuration, text, date}` | Same schema + `rawText`, `appContext` |
| Personalization | `personalization_preferences.json` (work/email/casual tone + tweaks) | Same idea, stored in our settings |
| Post-processing | Auto-dictionary, spelling normalization (en-gb/en-us) | Custom dictionary + spelling normalization |

Willow's *server* model is private, but the engine is the **Whisper family** plus an
**LLM cleanup pass**. We match the quality with free Whisper (Groq) + a free LLM
(Groq Llama), and ship the **same local-whisper offline fallback** Willow itself bundles.

## 3. User decisions (locked)

- **STT:** Groq `whisper-large-v3` primary + local `whisper.cpp` fallback.
- **Cleanup:** Replicate Willow's behavior, performed by Groq Llama-3.3-70B.
- **Form factor:** Python menu-bar app, packaged as an easy `.dmg` for sharing.
- **History import:** None — start fresh.

## 4. Architecture

Each component is small, single-purpose, and independently testable.

```
                    ┌──────────────────────────────────────────────┐
                    │            Menu-bar shell (rumps)            │
                    │   idle / recording / transcribing status     │
                    │   menu: History · Settings · Pause · Quit    │
                    └───────────────┬──────────────────────────────┘
                                    │
   ┌────────────────┐   hold/release│
   │ Hotkey listener│───────────────┤
   │ CGEventTap (Fn)│               ▼
   └────────────────┘     ┌───────────────────┐  WAV   ┌─────────────────────────┐
                          │ Recorder          │───────▶│ Transcriber (router)    │
                          │ sounddevice 16kHz │        │  Groq whisper-large-v3  │
                          └───────────────────┘        │   else whisper.cpp local│
                                                        └───────────┬─────────────┘
                                                          raw text   │
                                                                     ▼
                                                        ┌─────────────────────────┐
                                                        │ Cleanup (Groq Llama)    │
                                                        │  tone + frontmost-app   │
                                                        │  context; offline=raw   │
                                                        └───────────┬─────────────┘
                                              cleaned text          │
                          ┌───────────────────┐◀────────────────────┤
                          │ Inserter          │                     ▼
                          │ NSPasteboard+Cmd-V│           ┌─────────────────────┐
                          └───────────────────┘           │ History store (JSON)│
                                                          └─────────────────────┘
                    ┌──────────────────────────────────────────────┐
                    │     Local Flask UI (opened in browser)        │
                    │     History (search/replay/copy/flag/delete)  │
                    │     Settings (key, hotkey, model, tone, lang)  │
                    └──────────────────────────────────────────────┘
```

### 4.1 Components

1. **Menu-bar shell** (`rumps`) — always-on host process; mic icon reflects state;
   menu opens History/Settings (launches the Flask UI in the default browser), toggles
   Pause, and Quits.
2. **Hotkey listener** (`pyobjc` Quartz `CGEventTap`) — global listener for the
   hold-to-talk key (default **Fn**, keyCode 63). Press → start recording; release →
   stop. Double-tap within 400 ms → toggle hands-free (record until next tap).
   Requires Accessibility permission. Fallback default **Right ⌘** if Fn proves
   unreliable on the host OS. Hotkey is configurable in Settings.
3. **Recorder** (`sounddevice` + `soundfile`) — opens an input stream on the selected
   mic at 16 kHz mono, accumulates frames while active, writes a temp WAV. `ffmpeg`
   transcodes the WAV to `.opus` for the history archive.
4. **Transcriber** (strategy/router):
   - `GroqTranscriber` — POST to `https://api.groq.com/openai/v1/audio/transcriptions`,
     model `whisper-large-v3`, returns text.
   - `LocalTranscriber` — invokes a bundled `whisper-cli` (whisper.cpp) with
     `ggml-base.en.bin`; larger models downloadable in Settings.
   - `Router` — use Groq if a key is set and the network is reachable; otherwise local.
5. **Cleanup** (`CleanupService`, Groq `llama-3.3-70b`) — replicates Willow:
   - Inputs: raw transcript, frontmost app name, user tone/style for that context.
   - System prompt: clean dictation only (strip fillers "um/uh/like", fix
     punctuation & capitalization, format for the target app), apply the user's tone,
     **never** answer questions or add content, output only cleaned text.
   - Context map: Slack/Messages → casual (+ optional lowercase); Mail → email style;
     Cursor/ChatGPT/Claude → prompt style; default → neutral.
   - Offline or no key → skip LLM, apply a light local filler-strip + spelling
     normalization only (mirrors Willow's "skipping cleanup" offline behavior).
6. **Inserter** (`pyobjc` NSPasteboard + CGEvent) — save current clipboard, set cleaned
   text, send Cmd+V, restore prior clipboard after a short delay; optional Enter
   (`pressEnterAfterDictation`). Requires Accessibility permission.
7. **History store** (`HistoryStore`) — one JSON file per dictation in
   `~/Library/Application Support/com.usama.whisp/Transcripts/<uuid>.json`:
   `{id, text, rawText, audioURL, recordingDuration, date, isFlagged, appContext}`.
   Audio archived in `Recordings/`.
8. **Local UI** (`Flask`, bound to `127.0.0.1` on an ephemeral port) — opened in the
   default browser from the menu:
   - **History:** searchable list, audio replay, copy, flag, delete.
   - **Settings:** Groq API key, hotkey, STT model, mic, language (en-gb/en-us),
     tone/personalization per context, custom dictionary, paste-Enter toggle.

### 4.2 Config & data layout

```
~/Library/Application Support/com.usama.whisp/
  settings.json            # key, hotkey, model, mic, language, tone, dictionary
  Transcripts/<uuid>.json  # history entries (Willow-compatible schema)
  Recordings/<ts>.opus     # archived audio
```

Single source of truth: all tunables live in `settings.json`, read through one
`Settings` accessor; no scattered constants.

## 5. Permissions & first-run

On first launch, guide the user (like Willow's onboarding) to grant **Microphone**
and **Accessibility**. The app works in **local Whisper mode immediately** — no signup.
Settings offers an optional free-Groq-key field to enable cloud speed/quality.

## 6. Packaging & distribution

- Build with **PyInstaller** → `Whisp.app`, bundling: the Python runtime, all
  dependencies, `whisper-cli` + `ggml-base.en.bin`, and an `ffmpeg` binary.
- Wrap in **`Whisp.dmg`** via `create-dmg` (drag-to-Applications layout).
- **Unsigned** (no $99 Apple Developer account): first open via **right-click → Open**
  to clear Gatekeeper. Documented in a `README` on the DMG.
- Built on Intel → x86_64 app; runs on Apple Silicon via Rosetta 2. A future
  `universal2` build is possible but out of scope for v1.

## 7. Testing

- **Unit:** Settings round-trip; HistoryStore read/write & schema; CleanupService prompt
  building & offline path; Transcriber router selection (key/online → Groq; else local).
- **Integration (mocked network):** end-to-end record→transcribe→cleanup→insert with a
  fake recorder feeding a fixture WAV and a mocked Groq client.
- **Manual:** real hold-to-talk dictation into TextEdit, Slack, and Mail; verify paste,
  history entry, audio replay, and the offline fallback (toggle Wi-Fi off).

## 8. Out of scope (v1, YAGNI)

- Cloud sync / accounts / teams.
- Notarized signing.
- Windows build.
- Hands-free "command mode" voice commands (only basic hands-free record toggle is in).
- Importing the 70 existing Willow transcripts.

## 9. Risks

| Risk | Mitigation |
|---|---|
| Fn-key global capture unreliable on macOS 26 | Default to Right ⌘; hotkey configurable; CGEventTap handles modifier-only triggers |
| Gatekeeper friction for friend | Documented right-click → Open; ad-hoc codesign |
| Intel local Whisper latency | Default `base.en` (fast); Groq is primary for speed/quality |
| Groq free-tier rate limits | Auto-fallback to local on error/429 |
| PyInstaller bundling native dylibs (portaudio/ffmpeg/whisper) | Verify bundled binaries run on a clean Mac before shipping the DMG |

## 10. Success criteria

1. Hold hotkey → speak → cleaned text appears at the cursor in any app.
2. Output quality is subjectively comparable to Willow (fillers gone, well formatted).
3. Every dictation appears in searchable history with audio replay.
4. App runs from a `.dmg` on a clean Mac with no signup (local mode).
5. Adding a free Groq key visibly improves speed/quality.
