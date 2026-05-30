"""Tests de configuración y lógica de notificaciones Telegram (v2, Supabase)."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch


# ── Config endpoint ───────────────────────────────────────────────────────────

async def test_config_no_telegram(client, monkeypatch, fake_supabase):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    # Profile without telegram_chat_id
    from tests.conftest import TEST_USER_ID
    fake_supabase.seed_profiles([{
        "id": TEST_USER_ID, "email": "test@example.com",
        "notifications_enabled": True, "telegram_chat_id": None,
    }])
    r = await client.get("/api/notifications/config")
    assert r.status_code == 200
    assert r.json()["telegram_configured"] is False


async def test_config_with_telegram(client, monkeypatch, fake_supabase):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
    from tests.conftest import TEST_USER_ID
    fake_supabase.seed_profiles([{
        "id": TEST_USER_ID, "email": "test@example.com",
        "notifications_enabled": True, "telegram_chat_id": "12345",
    }])
    r = await client.get("/api/notifications/config")
    assert r.status_code == 200
    assert r.json()["telegram_configured"] is True


async def test_notifications_enabled_by_default(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    fake_supabase.seed_profiles([{
        "id": TEST_USER_ID, "email": "test@example.com",
        "notifications_enabled": True, "telegram_chat_id": None,
    }])
    r = await client.get("/api/notifications/config")
    assert r.json()["enabled"] is True


# ── Notifier job (v2, multi-usuario) ─────────────────────────────────────────

async def test_due_today_bills_detected(fake_supabase):
    """El job v2 detecta facturas que vencen hoy y envía Telegram al usuario."""
    import importlib
    from unittest.mock import patch as mpatch
    from tests.conftest import TEST_USER_ID

    today = date.today().isoformat()

    # Seed profile with telegram
    fake_supabase.seed_profiles([{
        "id": TEST_USER_ID, "email": "test@example.com",
        "notifications_enabled": True, "telegram_chat_id": "123",
    }])
    # Seed a bill due today
    fake_supabase.seed_bills([{
        "id": "notif-today", "user_id": TEST_USER_ID,
        "name": "Vence Hoy", "category": "electricidad", "amount": 1000.0,
        "due_date": today, "month": today[:7], "is_paid": False,
        "created_at": "2026-01-01T00:00:00+00:00",
    }])

    sent = []

    async def mock_send(token, chat_id, text):
        sent.append(text)

    with mpatch('supabase_client.supabase', fake_supabase):
        import notifier
        importlib.reload(notifier)
        with mpatch("notifier._send_telegram", side_effect=mock_send), \
             mpatch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok"}):
            await notifier.daily_notification_job()

    assert len(sent) == 1
    assert "Vence Hoy" in sent[0]


async def test_already_notified_today_skipped(fake_supabase):
    """Facturas ya en notification_logs para hoy no se notifican de nuevo."""
    import importlib
    from unittest.mock import patch as mpatch
    from tests.conftest import TEST_USER_ID

    today = date.today().isoformat()
    bill_id = "notif-dupl"

    fake_supabase.seed_profiles([{
        "id": TEST_USER_ID, "email": "test@example.com",
        "notifications_enabled": True, "telegram_chat_id": "123",
    }])
    fake_supabase.seed_bills([{
        "id": bill_id, "user_id": TEST_USER_ID,
        "name": "Ya notificada", "category": "gas", "amount": 500.0,
        "due_date": today, "month": today[:7], "is_paid": False,
        "created_at": "2026-01-01T00:00:00+00:00",
    }])
    # Pre-seed the notification log entry
    fake_supabase.seed_profiles([])  # already seeded above
    fake_supabase._stores.setdefault('notification_logs', []).append({
        "id": "log-1", "user_id": TEST_USER_ID,
        "bill_id": bill_id, "notified_at": today,
    })

    sent = []

    async def mock_send(token, chat_id, text):
        sent.append(text)

    with mpatch('supabase_client.supabase', fake_supabase):
        import notifier
        importlib.reload(notifier)
        with mpatch("notifier._send_telegram", side_effect=mock_send), \
             mpatch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok"}):
            await notifier.daily_notification_job()

    assert len(sent) == 0


async def test_notifications_disabled_skips_all(fake_supabase):
    """Con notifications_enabled=false no se envía nada a ese usuario."""
    import importlib
    from unittest.mock import patch as mpatch
    from tests.conftest import TEST_USER_ID

    today = date.today().isoformat()

    # Profile with notifications disabled
    fake_supabase.seed_profiles([{
        "id": TEST_USER_ID, "email": "test@example.com",
        "notifications_enabled": False, "telegram_chat_id": "123",
    }])
    fake_supabase.seed_bills([{
        "id": "disabled-notif", "user_id": TEST_USER_ID,
        "name": "No notificar", "category": "gas", "amount": 100.0,
        "due_date": today, "month": today[:7], "is_paid": False,
        "created_at": "2026-01-01T00:00:00+00:00",
    }])

    sent = []

    async def mock_send(token, chat_id, text):
        sent.append(text)

    with mpatch('supabase_client.supabase', fake_supabase):
        import notifier
        importlib.reload(notifier)
        with mpatch("notifier._send_telegram", side_effect=mock_send), \
             mpatch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok"}):
            await notifier.daily_notification_job()

    assert len(sent) == 0


async def test_bills_due_more_than_3_days_not_notified(fake_supabase):
    """Facturas que vencen en más de 3 días no se notifican."""
    import importlib
    from unittest.mock import patch as mpatch
    from tests.conftest import TEST_USER_ID

    due = (date.today() + timedelta(days=5)).isoformat()

    fake_supabase.seed_profiles([{
        "id": TEST_USER_ID, "email": "test@example.com",
        "notifications_enabled": True, "telegram_chat_id": "123",
    }])
    fake_supabase.seed_bills([{
        "id": "future-bill", "user_id": TEST_USER_ID,
        "name": "Factura Futura", "category": "agua", "amount": 300.0,
        "due_date": due, "month": due[:7], "is_paid": False,
        "created_at": "2026-01-01T00:00:00+00:00",
    }])

    sent = []

    async def mock_send(token, chat_id, text):
        sent.append(text)

    with mpatch('supabase_client.supabase', fake_supabase):
        import notifier
        importlib.reload(notifier)
        with mpatch("notifier._send_telegram", side_effect=mock_send), \
             mpatch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "tok"}):
            await notifier.daily_notification_job()

    assert len(sent) == 0
