"""Tests de configuración y lógica de notificaciones Telegram."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import storage


async def test_config_no_telegram(client, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    r = await client.get("/api/notifications/config")
    assert r.status_code == 200
    assert r.json()["telegram_configured"] is False


async def test_config_with_telegram(client, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    r = await client.get("/api/notifications/config")
    assert r.status_code == 200
    assert r.json()["telegram_configured"] is True


async def test_notifications_enabled_by_default(client):
    r = await client.get("/api/notifications/config")
    assert r.json()["enabled"] is True


async def test_due_today_bills_detected():
    """El job de notificaciones detecta facturas que vencen hoy."""
    import importlib
    import notifier
    importlib.reload(notifier)

    today = date.today().isoformat()
    bill = {
        "id": "test-notif-1",
        "name": "Vence Hoy",
        "category": "electricidad",
        "amount": 1000.0,
        "dueDate": today,
        "month": today[:7],
        "isPaid": False,
        "paidDate": None,
        "notes": None,
        "source": "manual",
        "createdAt": "2026-01-01T00:00:00+00:00",
    }
    storage.write_bills({"meta": {"notifications_enabled": True}, "bills": [bill]})

    sent = []

    async def mock_send(token, chat_id, text):
        sent.append(text)

    with patch("notifier._send_telegram", side_effect=mock_send), \
         patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}):
        await notifier.daily_notification_job()

    assert len(sent) == 1
    assert "Vence Hoy" in sent[0]


async def test_already_notified_today_skipped():
    """Facturas ya notificadas hoy no se notifican de nuevo."""
    import importlib
    import notifier
    importlib.reload(notifier)

    today = date.today().isoformat()
    bill_id = "test-notif-2"
    bill = {
        "id": bill_id,
        "name": "Ya notificada",
        "category": "gas",
        "amount": 500.0,
        "dueDate": today,
        "month": today[:7],
        "isPaid": False,
        "paidDate": None,
        "notes": None,
        "source": "manual",
        "createdAt": "2026-01-01T00:00:00+00:00",
    }
    storage.write_bills({"meta": {"notifications_enabled": True}, "bills": [bill]})

    import os
    notif_log_path = os.getenv("NOTIFICATIONS_LOG", "/data/notifications_log.json")
    storage.write_json(notif_log_path, {bill_id: today})

    sent = []

    async def mock_send(token, chat_id, text):
        sent.append(text)

    with patch("notifier._send_telegram", side_effect=mock_send), \
         patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}):
        await notifier.daily_notification_job()

    assert len(sent) == 0


async def test_notifications_disabled_skips_all():
    """Con notifications_enabled=false no se envía nada."""
    import importlib
    import notifier
    importlib.reload(notifier)

    storage.write_bills({"meta": {"notifications_enabled": False}, "bills": []})

    sent = []

    async def mock_send(token, chat_id, text):
        sent.append(text)

    with patch("notifier._send_telegram", side_effect=mock_send), \
         patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}):
        await notifier.daily_notification_job()

    assert len(sent) == 0


async def test_bills_due_more_than_3_days_not_notified():
    """Facturas que vencen en más de 3 días no se notifican."""
    import importlib
    import notifier
    importlib.reload(notifier)

    due = (date.today() + timedelta(days=5)).isoformat()
    bill = {
        "id": "future-bill",
        "name": "Factura Futura",
        "category": "agua",
        "amount": 300.0,
        "dueDate": due,
        "month": due[:7],
        "isPaid": False,
        "paidDate": None,
        "notes": None,
        "source": "manual",
        "createdAt": "2026-01-01T00:00:00+00:00",
    }
    storage.write_bills({"meta": {"notifications_enabled": True}, "bills": [bill]})

    sent = []

    async def mock_send(token, chat_id, text):
        sent.append(text)

    with patch("notifier._send_telegram", side_effect=mock_send), \
         patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}):
        await notifier.daily_notification_job()

    assert len(sent) == 0
