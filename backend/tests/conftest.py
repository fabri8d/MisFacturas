"""Fixtures compartidas para la suite de tests de MisFacturas."""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Asegurar que el módulo backend sea importable desde este directorio
sys.path.insert(0, str(Path(__file__).parent.parent))


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Redirige todos los archivos de datos a /tmp para cada test."""
    data_file = tmp_path / "bills.json"
    notif_log = tmp_path / "notifications_log.json"
    drive_cfg  = tmp_path / "drive_config.json"
    webhook_log = tmp_path / "webhook_log.json"
    proc_files  = tmp_path / "processed_drive_files.json"

    monkeypatch.setenv("DATA_FILE",         str(data_file))
    monkeypatch.setenv("NOTIFICATIONS_LOG", str(notif_log))
    monkeypatch.setenv("DRIVE_CONFIG",      str(drive_cfg))
    monkeypatch.setenv("WEBHOOK_LOG",       str(webhook_log))
    monkeypatch.setenv("GROQ_API_KEY",      "test-key")
    monkeypatch.setenv("DRIVE_FOLDER_ID",   "")
    monkeypatch.setenv("WEBHOOK_URL",       "")
    monkeypatch.setenv("WEBHOOK_SECRET",    "")

    # Recargar storage con las nuevas vars de entorno
    import importlib
    import storage
    importlib.reload(storage)


@pytest_asyncio.fixture
async def client(isolated_env):
    """Cliente HTTP asíncrono apuntando a la app FastAPI en memoria.

    El lifespan (scheduler) se bypasea en tests — no es necesario para testear la API.
    """
    import importlib

    # Recargar notifier para que el scheduler singleton use el loop actual
    import notifier
    importlib.reload(notifier)

    import main as main_module
    importlib.reload(main_module)

    # Usamos lifespan=False para no iniciar el scheduler en tests
    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_bill():
    today = date.today()
    due = (today + timedelta(days=10)).isoformat()
    return {
        "name": "EPEC Electricidad",
        "category": "electricidad",
        "amount": 15432.50,
        "dueDate": due,
        "notes": "Bimestral",
        "isPaid": False,
        "source": "manual",
    }


@pytest.fixture
def bills_with_data(tmp_path, isolated_env):
    """Pre-puebla bills.json con 5 facturas de distintas categorías y meses."""
    import storage

    today = date.today()
    this_month = today.strftime("%Y-%m")
    last_month = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    bills = [
        {
            "id": "aaaaaaaa-0001-0001-0001-000000000001",
            "name": "EPEC",
            "category": "electricidad",
            "amount": 15000.0,
            "dueDate": f"{this_month}-10",
            "month": this_month,
            "isPaid": False,
            "paidDate": None,
            "notes": None,
            "source": "manual",
            "createdAt": "2026-01-01T00:00:00+00:00",
        },
        {
            "id": "aaaaaaaa-0002-0002-0002-000000000002",
            "name": "Metrogas",
            "category": "gas",
            "amount": 8500.0,
            "dueDate": f"{this_month}-15",
            "month": this_month,
            "isPaid": True,
            "paidDate": today.isoformat(),
            "notes": None,
            "source": "manual",
            "createdAt": "2026-01-01T00:00:00+00:00",
        },
        {
            "id": "aaaaaaaa-0003-0003-0003-000000000003",
            "name": "Telecentro",
            "category": "internet",
            "amount": 22000.0,
            "dueDate": f"{this_month}-20",
            "month": this_month,
            "isPaid": False,
            "paidDate": None,
            "notes": None,
            "source": "manual",
            "createdAt": "2026-01-01T00:00:00+00:00",
        },
        {
            "id": "aaaaaaaa-0004-0004-0004-000000000004",
            "name": "Alquiler",
            "category": "alquiler",
            "amount": 250000.0,
            "dueDate": f"{last_month}-05",
            "month": last_month,
            "isPaid": True,
            "paidDate": f"{last_month}-03",
            "notes": None,
            "source": "manual",
            "createdAt": "2025-12-01T00:00:00+00:00",
        },
        {
            "id": "aaaaaaaa-0005-0005-0005-000000000005",
            "name": "Seguro Auto",
            "category": "seguro",
            "amount": 45000.0,
            "dueDate": f"{last_month}-15",
            "month": last_month,
            "isPaid": False,
            "paidDate": None,
            "notes": None,
            "source": "manual",
            "createdAt": "2025-12-01T00:00:00+00:00",
        },
    ]
    data = {
        "meta": {"notifications_enabled": True, "webhook_url": "", "webhook_secret": ""},
        "bills": bills,
    }
    storage.write_bills(data)
    return bills
