from unittest.mock import MagicMock

import pytest

import app.services.supabase_client as supabase_client_module


@pytest.fixture(autouse=True)
def reset_client_cache():
    supabase_client_module._supabase_client = None
    yield
    supabase_client_module._supabase_client = None


def test_get_supabase_client_raises_when_credentials_missing(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)

    with pytest.raises(RuntimeError, match="Supabase credentials are missing"):
        supabase_client_module.get_supabase_client()


def test_get_supabase_client_uses_service_key(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.setattr(supabase_client_module, "create_client", lambda url, key: fake_client)

    client = supabase_client_module.get_supabase_client()

    assert client is fake_client


def test_get_supabase_client_falls_back_to_anon_key(monkeypatch):
    fake_client = MagicMock()
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
    monkeypatch.setattr(supabase_client_module, "create_client", lambda url, key: fake_client)

    client = supabase_client_module.get_supabase_client()

    assert client is fake_client


def test_get_supabase_client_caches_client_instance(monkeypatch):
    created_clients = []

    def _create_client(_url, _key):
        mock_client = MagicMock()
        created_clients.append(mock_client)
        return mock_client

    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "service-key")
    monkeypatch.setattr(supabase_client_module, "create_client", _create_client)

    first = supabase_client_module.get_supabase_client()
    second = supabase_client_module.get_supabase_client()

    assert first is second
    assert len(created_clients) == 1
