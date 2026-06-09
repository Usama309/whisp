import tempfile

import pytest


@pytest.fixture()
def support_dir(monkeypatch):
    d = tempfile.mkdtemp(prefix="whisp-test-")
    monkeypatch.setenv("WHISP_SUPPORT_DIR", d)
    return d
