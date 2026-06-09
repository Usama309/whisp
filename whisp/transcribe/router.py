def choose_engine(api_key: str, online: bool) -> str:
    if api_key and online:
        return "groq"
    return "local"
