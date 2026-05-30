"""Tests de seguridad y autenticación."""

from datetime import datetime, timedelta, timezone


# ── Sin autenticación ───────────────────────────────────────────────────────

async def test_unauthenticated_request_rejected(client_no_auth):
    ac, _ = client_no_auth
    r = await ac.get("/api/bills")
    assert r.status_code in (401, 422)


async def test_invalid_token_rejected(client_no_auth):
    ac, fake_sb = client_no_auth
    fake_sb.set_auth_invalid()
    r = await ac.get("/api/bills", headers={"Authorization": "Bearer token_invalido"})
    assert r.status_code == 401


async def test_missing_bearer_prefix_rejected(client_no_auth):
    ac, fake_sb = client_no_auth
    fake_sb.set_auth_invalid()
    r = await ac.get("/api/bills", headers={"Authorization": "not-a-bearer-token"})
    assert r.status_code == 401


async def test_health_is_public(client_no_auth):
    ac, _ = client_no_auth
    r = await ac.get("/api/health")
    assert r.status_code == 200


# ── Aislamiento entre usuarios ──────────────────────────────────────────────

async def test_user_only_sees_own_bills(client, fake_supabase):
    """Factura de otro usuario no aparece en GET /api/bills."""
    from tests.conftest import TEST_USER_ID, TEST_USER_ID_B

    # Sembrar una factura de cada usuario
    from datetime import date
    today = date.today().isoformat()
    fake_supabase.seed_bills([
        {"id": "aaa-001", "user_id": TEST_USER_ID,   "name": "MiBill",  "category": "gas",
         "amount": 1000.0, "due_date": today, "month": today[:7], "is_paid": False,
         "created_at": "2026-01-01T00:00:00+00:00"},
        {"id": "bbb-001", "user_id": TEST_USER_ID_B, "name": "OtroBill","category": "gas",
         "amount": 2000.0, "due_date": today, "month": today[:7], "is_paid": False,
         "created_at": "2026-01-01T00:00:00+00:00"},
    ])

    r = await client.get("/api/bills")
    assert r.status_code == 200
    names = [b["name"] for b in r.json()]
    assert "MiBill" in names
    assert "OtroBill" not in names


async def test_user_cannot_delete_other_user_bill(client, fake_supabase):
    """DELETE de factura de otro usuario retorna 404."""
    from tests.conftest import TEST_USER_ID_B
    from datetime import date
    today = date.today().isoformat()

    fake_supabase.seed_bills([
        {"id": "bbb-delete", "user_id": TEST_USER_ID_B, "name": "AjenaBill",
         "category": "gas", "amount": 500.0, "due_date": today,
         "month": today[:7], "is_paid": False, "created_at": "2026-01-01T00:00:00+00:00"},
    ])

    r = await client.delete("/api/bills/bbb-delete")
    assert r.status_code == 404


async def test_user_cannot_update_other_user_bill(client, fake_supabase):
    """PUT en factura de otro usuario retorna 404."""
    from tests.conftest import TEST_USER_ID_B
    from datetime import date
    today = date.today().isoformat()

    fake_supabase.seed_bills([
        {"id": "bbb-update", "user_id": TEST_USER_ID_B, "name": "AjenaUpdate",
         "category": "gas", "amount": 500.0, "due_date": today,
         "month": today[:7], "is_paid": False, "created_at": "2026-01-01T00:00:00+00:00"},
    ])

    r = await client.put("/api/bills/bbb-update", json={"name": "Hackeado"})
    assert r.status_code == 404


async def test_user_cannot_toggle_other_user_bill(client, fake_supabase):
    """PATCH toggle de factura de otro usuario retorna 404."""
    from tests.conftest import TEST_USER_ID_B
    from datetime import date
    today = date.today().isoformat()

    fake_supabase.seed_bills([
        {"id": "bbb-toggle", "user_id": TEST_USER_ID_B, "name": "AjenaToggle",
         "category": "gas", "amount": 500.0, "due_date": today,
         "month": today[:7], "is_paid": False, "created_at": "2026-01-01T00:00:00+00:00"},
    ])

    r = await client.patch("/api/bills/bbb-toggle/toggle-paid")
    assert r.status_code == 404
