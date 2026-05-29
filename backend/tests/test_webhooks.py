"""Tests del servicio de webhooks salientes."""

from unittest.mock import AsyncMock, MagicMock, patch

import storage


async def test_fire_no_url_configured():
    """fire() no lanza si no hay URL configurada."""
    import webhook_service
    await webhook_service.fire("bill.created", {"id": "x"})  # no debe lanzar


async def test_fire_sends_request(monkeypatch):
    """fire() hace POST cuando WEBHOOK_URL está configurado."""
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/hook")
    monkeypatch.setenv("WEBHOOK_SECRET", "")

    sent = []

    mock_response = MagicMock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    import importlib
    import webhook_service
    importlib.reload(webhook_service)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await webhook_service.fire("test.event", {"key": "val"})

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert "https://example.com/hook" in call_kwargs[0]


async def test_webhook_hmac_signature(monkeypatch):
    """fire() incluye header X-Signature cuando hay secreto."""
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/hook")
    monkeypatch.setenv("WEBHOOK_SECRET", "mysecret")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    import importlib
    import webhook_service
    importlib.reload(webhook_service)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await webhook_service.fire("test.event", {})

    headers = mock_client.post.call_args[1]["headers"]
    assert "X-Signature" in headers
    assert headers["X-Signature"].startswith("sha256=")


async def test_webhooks_config_no_url(client):
    r = await client.get("/api/webhooks/config")
    assert r.status_code == 200
    assert r.json()["url_set"] is False


async def test_webhook_log_rotation(monkeypatch):
    """El log se mantiene con máximo 10 entradas."""
    import importlib
    import webhook_service
    importlib.reload(webhook_service)

    # Simular 15 entradas previas
    import os
    log_path = os.getenv("WEBHOOK_LOG", "/data/webhook_log.json")
    existing = [{"timestamp": f"2026-01-{i:02d}T00:00:00Z", "event": "old", "status_code": 200, "error": None} for i in range(1, 16)]
    storage.write_json(log_path, existing)

    # Disparar una más
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/hook")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    importlib.reload(webhook_service)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await webhook_service.fire("new.event", {})

    log = storage.read_json(log_path, default=[])
    assert len(log) <= 10


async def test_fire_on_exception_does_not_raise(monkeypatch):
    """fire() captura excepciones de red sin propagarlas."""
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/hook")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=Exception("connection refused"))

    import importlib
    import webhook_service
    importlib.reload(webhook_service)

    with patch("httpx.AsyncClient", return_value=mock_client):
        await webhook_service.fire("test.event", {})  # no debe lanzar
