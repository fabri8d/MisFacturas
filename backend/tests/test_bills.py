"""Tests de CRUD completo de facturas."""

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
    assert b["id"]  # uuid4 generado server-side
    assert b["month"] == sample_bill["dueDate"][:7]
    assert b["createdAt"]
    assert b["source"] == "manual"


async def test_create_bill_missing_name(client, sample_bill):
    payload = {**sample_bill, "name": ""}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 422


async def test_create_bill_missing_amount(client, sample_bill):
    payload = {k: v for k, v in sample_bill.items() if k != "amount"}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 422


async def test_create_bill_missing_due_date(client, sample_bill):
    payload = {k: v for k, v in sample_bill.items() if k != "dueDate"}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 422


async def test_create_bill_invalid_category_coerced_to_otro(client, sample_bill):
    # El modelo coerciona categorías desconocidas a "otro" (no rechaza con 422)
    payload = {**sample_bill, "category": "inexistente"}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 201
    assert r.json()["category"] == "otro"


async def test_create_bill_negative_amount(client, sample_bill):
    payload = {**sample_bill, "amount": -100}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 422


async def test_create_bill_zero_amount(client, sample_bill):
    payload = {**sample_bill, "amount": 0}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 422


async def test_month_computed_from_due_date(client, sample_bill):
    payload = {**sample_bill, "dueDate": "2026-06-15"}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 201
    assert r.json()["month"] == "2026-06"


# ── Deduplicación ─────────────────────────────────────────────────────────────

async def test_create_bill_duplicate_detection(client, sample_bill):
    r1 = await client.post("/api/bills", json=sample_bill)
    assert r1.status_code == 201

    r2 = await client.post("/api/bills", json=sample_bill)
    assert r2.status_code == 409
    body = r2.json()
    assert "similar" in body["detail"]["message"].lower()
    assert body["detail"]["existing"]["id"] == r1.json()["id"]


async def test_duplicate_check_case_insensitive(client, sample_bill):
    await client.post("/api/bills", json=sample_bill)
    payload = {**sample_bill, "name": sample_bill["name"].upper()}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 409


async def test_same_name_different_amount_not_duplicate(client, sample_bill):
    await client.post("/api/bills", json=sample_bill)
    payload = {**sample_bill, "amount": sample_bill["amount"] + 1}
    r = await client.post("/api/bills", json=payload)
    assert r.status_code == 201


# ── Listado y filtrado ────────────────────────────────────────────────────────

async def test_get_bills_empty(client):
    r = await client.get("/api/bills")
    assert r.status_code == 200
    assert r.json() == []


async def test_get_bills_by_month(client, sample_bill):
    # Factura en el mes corriente
    await client.post("/api/bills", json={**sample_bill, "dueDate": "2026-06-10"})
    # Factura en mayo
    await client.post("/api/bills", json={**sample_bill, "name": "Mayo bill", "dueDate": "2026-05-10"})

    r_jun = await client.get("/api/bills", params={"month": "2026-06"})
    r_may = await client.get("/api/bills", params={"month": "2026-05"})

    assert len(r_jun.json()) == 1
    assert len(r_may.json()) == 1
    assert r_jun.json()[0]["month"] == "2026-06"
    assert r_may.json()[0]["month"] == "2026-05"


async def test_get_bills_sorted_by_due_date(client, sample_bill):
    dates = ["2026-06-20", "2026-06-05", "2026-06-15"]
    for i, d in enumerate(dates):
        await client.post("/api/bills", json={**sample_bill, "name": f"Bill {i}", "dueDate": d})

    r = await client.get("/api/bills", params={"month": "2026-06"})
    due_dates = [b["dueDate"] for b in r.json()]
    assert due_dates == sorted(due_dates)


# ── Actualización ─────────────────────────────────────────────────────────────

async def test_update_bill(client, sample_bill):
    created = (await client.post("/api/bills", json=sample_bill)).json()
    r = await client.put(f"/api/bills/{created['id']}", json={"amount": 99999.0})
    assert r.status_code == 200
    assert r.json()["amount"] == 99999.0


async def test_update_bill_recomputes_month(client, sample_bill):
    created = (await client.post("/api/bills", json=sample_bill)).json()
    r = await client.put(f"/api/bills/{created['id']}", json={"dueDate": "2026-09-01"})
    assert r.json()["month"] == "2026-09"


async def test_update_bill_not_found(client):
    r = await client.put("/api/bills/no-existe-uuid", json={"amount": 100})
    assert r.status_code == 404


# ── Eliminación ───────────────────────────────────────────────────────────────

async def test_delete_bill(client, sample_bill):
    created = (await client.post("/api/bills", json=sample_bill)).json()
    r = await client.delete(f"/api/bills/{created['id']}")
    assert r.status_code == 204

    bills = (await client.get("/api/bills")).json()
    assert not any(b["id"] == created["id"] for b in bills)


async def test_delete_bill_not_found(client):
    r = await client.delete("/api/bills/no-existe-uuid")
    assert r.status_code == 404


# ── Toggle paid ───────────────────────────────────────────────────────────────

async def test_toggle_paid_unpaid_cycle(client, sample_bill):
    created = (await client.post("/api/bills", json=sample_bill)).json()
    bid = created["id"]

    # unpaid → paid
    r1 = await client.patch(f"/api/bills/{bid}/toggle-paid")
    assert r1.json()["isPaid"] is True
    assert r1.json()["paidDate"] == date.today().isoformat()

    # paid → unpaid
    r2 = await client.patch(f"/api/bills/{bid}/toggle-paid")
    assert r2.json()["isPaid"] is False
    assert r2.json()["paidDate"] is None


async def test_toggle_paid_not_found(client):
    r = await client.patch("/api/bills/no-existe/toggle-paid")
    assert r.status_code == 404


# ── Summary ───────────────────────────────────────────────────────────────────

async def test_summary_last_6_months(client, sample_bill):
    await client.post("/api/bills", json={**sample_bill, "dueDate": "2026-06-10", "amount": 1000})
    await client.post("/api/bills", json={**sample_bill, "name": "Gas", "category": "gas", "dueDate": "2026-05-10", "amount": 500})

    r = await client.get("/api/summary", params={"months": 6})
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 6

    # Verificar estructura
    for item in items:
        assert "month" in item
        assert "label" in item
        assert "total" in item
        assert "paid" in item

    # Labels en español, minúsculas
    labels = [i["label"] for i in items]
    for label in labels:
        assert label[0].islower() or label[0].isdigit() or label == label.lower()


async def test_summary_totals_correct(client, sample_bill):
    # Dos facturas en 2026-06, una pagada
    await client.post("/api/bills", json={**sample_bill, "dueDate": "2026-06-10", "amount": 1000})
    r2 = (await client.post("/api/bills", json={**sample_bill, "name": "Gas", "category": "gas", "dueDate": "2026-06-15", "amount": 500})).json()
    await client.patch(f"/api/bills/{r2['id']}/toggle-paid")

    summary = (await client.get("/api/summary", params={"months": 6})).json()
    jun = next((i for i in summary if i["month"] == "2026-06"), None)
    if jun:
        assert jun["total"] == 1500.0
        assert jun["paid"] == 500.0


# ── Health ────────────────────────────────────────────────────────────────────

async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
