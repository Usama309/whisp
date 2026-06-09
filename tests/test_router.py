from whisp.transcribe.router import choose_engine


def test_groq_when_key_and_online():
    assert choose_engine(api_key="gsk_x", online=True) == "groq"


def test_local_when_no_key():
    assert choose_engine(api_key="", online=True) == "local"


def test_local_when_offline():
    assert choose_engine(api_key="gsk_x", online=False) == "local"
