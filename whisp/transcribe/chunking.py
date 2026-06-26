"""Split long recordings into short segments and transcribe them, so audio of
any length (15 min, 1 hour, more) works without hitting upload-size limits or
timeouts. Short recordings pass straight through unchanged."""
import concurrent.futures
import os
import tempfile
import wave

from whisp.logs import log

# ~2 min per chunk at 16 kHz mono 16-bit is ~3.8 MB: well under Groq's 25 MB
# limit and uploads quickly even on slow connections.
CHUNK_SECONDS = 120


def duration_seconds(wav_path: str) -> float:
    try:
        with wave.open(wav_path, "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:
        return 0.0


def _split(wav_path: str, chunk_secs: int):
    paths = []
    with wave.open(wav_path, "rb") as w:
        fr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        chunk_frames = int(chunk_secs * fr)
        i = 0
        while i < n:
            w.setpos(i)
            data = w.readframes(min(chunk_frames, n - i))
            p = tempfile.mktemp(suffix=".wav", prefix="whisp_chunk_")
            with wave.open(p, "wb") as o:
                o.setnchannels(ch)
                o.setsampwidth(sw)
                o.setframerate(fr)
                o.writeframes(data)
            paths.append(p)
            i += chunk_frames
    return paths


def transcribe_chunked(wav_path, transcribe_one, parallel=True, chunk_secs=CHUNK_SECONDS):
    """Transcribe a recording of any length.

    transcribe_one(path) -> str. Returns the full transcript (chunks joined in
    order). Recordings shorter than one chunk are sent through in a single call.
    """
    if duration_seconds(wav_path) <= chunk_secs:
        return transcribe_one(wav_path)

    chunks = _split(wav_path, chunk_secs)
    log(f"CHUNK  split into {len(chunks)} segments of ~{chunk_secs}s")
    try:
        if parallel:
            workers = min(8, len(chunks))
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                texts = list(ex.map(transcribe_one, chunks))
        else:
            texts = [transcribe_one(c) for c in chunks]
    finally:
        for c in chunks:
            try:
                os.remove(c)
            except OSError:
                pass
    return " ".join(t.strip() for t in texts if t and t.strip())
