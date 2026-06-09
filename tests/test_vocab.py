from whisp.ui.server import parse_vocab, vocab_to_text
from whisp.factory import stt_vocabulary_prompt


def test_parse_plain_words_map_to_themselves():
    d = parse_vocab("grocery list\nGroq\nKubernetes")
    assert d == {"grocery list": "grocery list", "Groq": "Groq", "Kubernetes": "Kubernetes"}


def test_parse_correction_arrows():
    d = parse_vocab("groh => Groq\ngross release => grocery list")
    assert d["groh"] == "Groq"
    assert d["gross release"] == "grocery list"


def test_round_trip_text():
    text = "Groq\ngroh => Groq"
    assert vocab_to_text(parse_vocab(text)) == text


def test_stt_prompt_lists_unique_terms():
    p = stt_vocabulary_prompt({"groh": "Groq", "Kubernetes": "Kubernetes"})
    assert "Groq" in p and "Kubernetes" in p and "groh" in p


def test_stt_prompt_empty_dictionary_is_none():
    assert stt_vocabulary_prompt({}) is None
