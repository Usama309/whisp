import requests

from whisp import config


class GroqError(Exception):
    pass


def transcribe(api_key: str, wav_path: str, language: str = "en", prompt: str = None) -> str:
    with open(wav_path, "rb") as f:
        files = {"file": (wav_path, f, "audio/wav")}
        data = {"model": config.GROQ_STT_MODEL, "response_format": "json", "temperature": "0"}
        if language:
            data["language"] = language
        if prompt:
            data["prompt"] = prompt
        resp = requests.post(
            config.GROQ_STT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files=files,
            data=data,
            timeout=60,
        )
    if resp.status_code != 200:
        raise GroqError(f"STT {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("text", "").strip()


def chat(api_key: str, system: str, user: str) -> str:
    resp = requests.post(
        config.GROQ_CHAT_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": config.GROQ_CHAT_MODEL,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise GroqError(f"chat {resp.status_code}: {resp.text[:200]}")
    return resp.json()["choices"][0]["message"]["content"].strip()
