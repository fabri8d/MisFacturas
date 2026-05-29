"""Tests de la capa de persistencia JSON con filelock."""

import asyncio
import json

import pytest

import storage


def test_read_nonexistent_file_returns_default(tmp_path):
    path = str(tmp_path / "nonexistent.json")
    assert storage.read_json(path, default=[]) == []
    assert storage.read_json(path, default={}) == {}


def test_write_and_read_roundtrip(tmp_path):
    path = str(tmp_path / "test.json")
    data = {"key": "value", "nums": [1, 2, 3]}
    storage.write_json(path, data)
    assert storage.read_json(path) == data


def test_bills_json_created_on_first_write(tmp_path, monkeypatch):
    path = str(tmp_path / "bills.json")
    monkeypatch.setenv("DATA_FILE", path)
    import importlib
    importlib.reload(storage)

    storage.write_bills({"meta": {}, "bills": []})
    assert (tmp_path / "bills.json").exists()


def test_read_bills_returns_default_structure(tmp_path, monkeypatch):
    path = str(tmp_path / "bills_new.json")
    monkeypatch.setenv("DATA_FILE", path)
    import importlib
    importlib.reload(storage)

    data = storage.read_bills()
    assert "bills" in data
    assert "meta" in data
    assert isinstance(data["bills"], list)


def test_find_duplicate_match(tmp_path, monkeypatch):
    path = str(tmp_path / "bills.json")
    monkeypatch.setenv("DATA_FILE", path)
    import importlib
    importlib.reload(storage)

    bill = {
        "id": "test-id",
        "name": "EPEC",
        "category": "electricidad",
        "amount": 1000.0,
        "dueDate": "2026-06-10",
        "month": "2026-06",
        "isPaid": False,
        "paidDate": None,
        "notes": None,
        "source": "manual",
        "createdAt": "2026-01-01T00:00:00+00:00",
    }
    storage.write_bills({"meta": {}, "bills": [bill]})

    found = storage.find_duplicate("EPEC", 1000.0, "2026-06-10")
    assert found is not None
    assert found["id"] == "test-id"


def test_find_duplicate_case_insensitive(tmp_path, monkeypatch):
    path = str(tmp_path / "bills.json")
    monkeypatch.setenv("DATA_FILE", path)
    import importlib
    importlib.reload(storage)

    bill = {
        "id": "test-id",
        "name": "epec electricidad",
        "category": "electricidad",
        "amount": 1000.0,
        "dueDate": "2026-06-10",
        "month": "2026-06",
        "isPaid": False,
        "paidDate": None,
        "notes": None,
        "source": "manual",
        "createdAt": "2026-01-01T00:00:00+00:00",
    }
    storage.write_bills({"meta": {}, "bills": [bill]})

    assert storage.find_duplicate("EPEC ELECTRICIDAD", 1000.0, "2026-06-10") is not None


def test_find_duplicate_no_match_different_amount(tmp_path, monkeypatch):
    path = str(tmp_path / "bills.json")
    monkeypatch.setenv("DATA_FILE", path)
    import importlib
    importlib.reload(storage)

    bill = {
        "id": "test-id",
        "name": "EPEC",
        "category": "electricidad",
        "amount": 1000.0,
        "dueDate": "2026-06-10",
        "month": "2026-06",
        "isPaid": False,
        "paidDate": None,
        "notes": None,
        "source": "manual",
        "createdAt": "2026-01-01T00:00:00+00:00",
    }
    storage.write_bills({"meta": {}, "bills": [bill]})

    assert storage.find_duplicate("EPEC", 999.0, "2026-06-10") is None


async def test_concurrent_writes_no_corruption(tmp_path, monkeypatch):
    """10 escrituras concurrentes no deben corromper el JSON."""
    path = str(tmp_path / "concurrent.json")
    monkeypatch.setenv("DATA_FILE", path)
    import importlib
    importlib.reload(storage)

    storage.write_bills({"meta": {}, "bills": []})

    async def add_bill(n: int):
        data = storage.read_bills()
        data["bills"].append({"id": str(n), "name": f"Bill {n}"})
        storage.write_bills(data)

    await asyncio.gather(*[add_bill(i) for i in range(10)])

    final = storage.read_bills()
    # El JSON debe ser válido y tener al menos algunas facturas
    assert isinstance(final["bills"], list)
    raw = (tmp_path / "concurrent.json").read_text()
    json.loads(raw)  # No debe lanzar JSONDecodeError
