"""Split long recordings into short segments and transcribe them, so audio of
any length (15 min, 1 hour, more) works without hitting upload-size limits or
timeouts. Short recordings pass straight through unchanged."""
import collections
import concurrent.futures
import os
import tempfile
import threading
import time
import wave

from whisp.logs import log

# ~2 min per chunk at 16 kHz mono 16-bit is ~3.8 MB: well under Groq's 25 MB
# limit and uploads quickly even on slow connections.
CHUNK_SECONDS = 120

# Stay safely under Groq's free-tier 20 requests/min for whisper-large-v3.
_RPM_LIMIT = 18
_rate_lock = threading.Lock()
_recent = collections.deque()   # monotonic timestamps of recent requests


def _rate_gate():
    """Block until starting another request keeps us under _RPM_LIMIT / minute."""
    while True:
        with _rate_lock:
            now = time.monotonic()
            while _recent and _recent[0] < now - 60:
                _recent.popleft()
            if len(_recent) < _RPM_LIMIT:
                _recent.append(now)
                return
            sleep_for = 60 - (now - _recent[0]) + 0.05
        time.sleep(max(0.1, sleep_for))


def _with_rate_limit_and_retry(transcribe_one):
    """Wrap a chunk transcriber with rate-limiting + a short backoff retry if it
    still gets throttled (429), so long recordings never fail on rate limits."""
    def wrapped(path):
        for attempt in range(4):
            _rate_gate()
            try:
                return transcribe_one(path)
            except Exception as exc:
                if "429" in str(exc) and attempt < 3:
                    log(f"CHUNK  rate-limited, backing off ({attempt + 1})")
                    time.sleep(5 * (attempt + 1))
                    continue
                raise
        return ""
    return wrapped


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
            fn = _with_rate_limit_and_retry(transcribe_one)
            workers = min(6, len(chunks))
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
                texts = list(ex.map(fn, chunks))
        else:
            texts = [transcribe_one(c) for c in chunks]
    finally:
        for c in chunks:
            try:
                os.remove(c)
            except OSError:
                pass
    return " ".join(t.strip() for t in texts if t and t.strip())
