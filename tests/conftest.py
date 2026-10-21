"""No developer/provider environment may silently turn a test into a network call."""
import pytest
from adler.config import ENV_FIELDS


@pytest.fixture(autouse=True)
def isolated_adler_environment(monkeypatch):
    for name in [*ENV_FIELDS, 'ADLER_CONFIG_FILE']:
        monkeypatch.delenv(name, raising=False)
