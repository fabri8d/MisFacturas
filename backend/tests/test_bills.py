"""Tests de CRUD de facturas y resumen histórico (v2, Supabase)."""

from datetime import date, timedelta


def _due(days=10):
    return (date.today() + timedelta(days=days)).isoformat()


def _month(days=10):
    return _due(days)[:7]


# ── Creación ──────────────────────────────────────────────────────────────────

async def test_create_bill_valid(client, sample_bill):
    r = await client.post("/api/bills", json=sample_bill)
    assert r.status_code == 201
    b = r.json()
    assert b["id"]
    assert b["month"] == sample_bill["dueDate"][:7]
    assert b["createdAt"]
    assert b["source"] == "manual"


async def test_create_bill_missing_name(client, sample_bill):
    r = await client.post("/api/bills", json={**sample_bill, "name": ""})
    assert r.status_code == 422


async def test_create_bill_missing_amount(client, sample_bill):
    payload = {k: v for k, v in sample_bill.items() if k != "amount"}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 422


async def test_create_bill_missing_due_date(client, sample_bill):
    payload = {k: v for k, v in sample_bill.items() if k != "dueDate"}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 422


async def test_create_bill_invalid_category_coerced(client, sample_bill):
    r = await client.post("/api/bills", json={**sample_bill, "category": "inexistente"})
    assert r.status_code == 201
    assert r.json()["category"] == "otro"


async def test_create_bill_negative_amount(client, sample_bill):
    r = await client.post("/api/bills", json={**sample_bill, "amount": -100})
    assert r.status_code == 422


async def test_create_bill_zero_amount(client, sample_bill):
    r = await client.post("/api/bills", json={**sample_bill, "amount": 0})
    assert r.status_code == 422


async def test_create_bill_duplicate_returns_409(client, sample_bill):
    r1 = await client.post("/api/bills", json=sample_bill)
    assert r1.status_code == 201
    r2 = await client.post("/api/bills", json=sample_bill)
    assert r2.status_code == 409
    detail = r2.json()["detail"]
    assert "message" in detail
    assert "existing" in detail


# ── Listado ───────────────────────────────────────────────────────────────────

async def test_list_bills_empty(client):
    r = await client.get("/api/bills")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_bills_returns_created(client, sample_bill):
    await client.post("/api/bills", json=sample_bill)
    r = await client.get("/api/bills")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == sample_bill["name"]


async def test_list_bills_filter_by_month(client, sample_bill, fake_supabase):
    from tests.conftest import TEST_USER_ID
    today = date.today()
    this_month = today.strftime("%Y-%m")
    last_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    fake_supabase.seed_bills([
        {"id": "aaa-1", "user_id": TEST_USER_ID, "name": "EsteMes", "category": "gas",
         "amount": 1000.0, "due_date": f"{this_month}-10", "month": this_month,
         "is_paid": False, "created_at": "2026-01-01T00:00:00+00:00"},
        {"id": "aaa-2", "user_id": TEST_USER_ID, "name": "MesPasado", "category": "gas",
         "amount": 500.0, "due_date": f"{last_month}-10", "month": last_month,
         "is_paid": False, "created_at": "2026-01-01T00:00:00+00:00"},
    ])

    r = await client.get("/api/bills", params={"month": this_month})
    assert r.status_code == 200
    names = [b["name"] for b in r.json()]
    assert "EsteMes" in names
    assert "MesPasado" not in names


# ── Actualización ─────────────────────────────────────────────────────────────

async def test_update_bill(client, sample_bill):
    created = (await client.post("/api/bills", json=sample_bill)).json()
    r = await client.put(f"/api/bills/{created['id']}", json={"name": "Modificado"})
    assert r.status_code == 200
    assert r.json()["name"] == "Modificado"


async def test_update_bill_not_found(client):
    r = await client.put("/api/bills/nonexistent-id", json={"name": "X"})
    assert r.status_code == 404


# ── Eliminación ───────────────────────────────────────────────────────────────

async def test_delete_bill(client, sample_bill):
    created = (await client.post("/api/bills", json=sample_bill)).json()
    r = await client.delete(f"/api/bills/{created['id']}")
    assert r.status_code == 204


async def test_delete_bill_not_found(client):
    r = await client.delete("/api/bills/nonexistent-id")
    assert r.status_code == 404


# ── Toggle paid ───────────────────────────────────────────────────────────────

async def test_toggle_paid_to_true(client, sample_bill):
    created = (await client.post("/api/bills", json=sample_bill)).json()
    r = await client.patch(f"/api/bills/{created['id']}/toggle-paid")
    assert r.status_code == 200
    assert r.json()["isPaid"] is True
    assert r.json()["paidDate"] is not None


async def test_toggle_paid_to_false(client, sample_bill):
    created = (await client.post("/api/bills", json={**sample_bill, "isPaid": True})).json()
    r = await client.patch(f"/api/bills/{created['id']}/toggle-paid")
    assert r.status_code == 200
    assert r.json()["isPaid"] is False
    assert r.json()["paidDate"] is None


async def test_toggle_not_found(client):
    r = await client.patch("/api/bills/nonexistent-id/toggle-paid")
    assert r.status_code == 404


# ── Summary por año ────────────────────────────────────────────────────────────

async def test_summary_returns_12_months(client):
    r = await client.get("/api/summary", params={"year": 2026})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 12


async def test_summary_months_are_sequential(client):
    r = await client.get("/api/summary", params={"year": 2026})
    months = [item["month"] for item in r.json()]
    assert months == [f"2026-{str(m).zfill(2)}" for m in range(1, 13)]


async def test_summary_labels_spanish(client):
    r = await client.get("/api/summary", params={"year": 2026})
    labels = [item["label"] for item in r.json()]
    expected = [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    assert labels == expected


async def test_summary_empty_months_have_zero(client):
    r = await client.get("/api/summary", params={"year": 2099})
    data = r.json()
    assert all(item["total"] == 0 for item in data)
    assert all(item["paid"] == 0 for item in data)


async def test_summary_paid_vs_total(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    fake_supabase.seed_bills([
        {"id": "s-1", "user_id": TEST_USER_ID, "name": "PagadaTest", "category": "gas",
         "amount": 1000.0, "due_date": "2026-03-10", "month": "2026-03",
         "is_paid": True, "created_at": "2026-03-01T00:00:00+00:00"},
        {"id": "s-2", "user_id": TEST_USER_ID, "name": "NoPagadaTest", "category": "gas",
         "amount": 500.0, "due_date": "2026-03-20", "month": "2026-03",
         "is_paid": False, "created_at": "2026-03-01T00:00:00+00:00"},
    ])

    r = await client.get("/api/summary", params={"year": 2026})
    assert r.status_code == 200
    march = next(m for m in r.json() if m["month"] == "2026-03")
    assert march["total"] == 1500.0
    assert march["paid"] == 1000.0


async def test_summary_year_isolation(client, fake_supabase):
    from tests.conftest import TEST_USER_ID
    fake_supabase.seed_bills([
        {"id": "y25", "user_id": TEST_USER_ID, "name": "En2025", "category": "gas",
         "amount": 999.0, "due_date": "2025-06-10", "month": "2025-06",
         "is_paid": False, "created_at": "2025-06-01T00:00:00+00:00"},
        {"id": "y26", "user_id": TEST_USER_ID, "name": "En2026", "category": "gas",
         "amount": 777.0, "due_date": "2026-06-10", "month": "2026-06",
         "is_paid": False, "created_at": "2026-06-01T00:00:00+00:00"},
    ])

    r25 = await client.get("/api/summary", params={"year": 2025})
    june_25 = next(m for m in r25.json() if m["month"] == "2025-06")
    assert june_25["total"] == 999.0

    r26 = await client.get("/api/summary", params={"year": 2026})
    june_26 = next(m for m in r26.json() if m["month"] == "2026-06")
    assert june_26["total"] == 777.0
    # 2025 bill doesn't bleed into 2026
    assert not any(m["month"].startswith("2025") for m in r26.json())


async def test_summary_default_year_is_current(client):
    from datetime import date
    r = await client.get("/api/summary")
    assert r.status_code == 200
    current_year = str(date.today().year)
    assert all(item["month"].startswith(current_year) for item in r.json())


async def test_summary_health_check(client):
    """El endpoint de salud es accesible sin auth."""
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
