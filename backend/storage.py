"""Capa de persistencia de MisFacturas.

Toda lectura y escritura de archivos JSON pasa por este módulo.
Se usa filelock para evitar condiciones de carrera entre el scheduler y los requests.
"""

import json
import logging
import os
from typing import Any

from filelock import FileLock

logger = logging.getLogger(__name__)

DATA_FILE = os.getenv("DATA_FILE", "/data/bills.json")

_DEFAULT_BILLS: dict = {
    "meta": {
        "notifications_enabled": True,
        "webhook_url": "",
        "webhook_secret": "",
    },
    "bills": [],
}


def _lock_path(path: str) -> str:
    return path + ".lock"


def read_json(path: str, default: Any = None) -> Any:
    """Lee un archivo JSON con bloqueo exclusivo. Devuelve *default* si no existe."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with FileLock(_lock_path(path)):
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def write_json(path: str, data: Any) -> None:
    """Escribe *data* en un archivo JSON con bloqueo exclusivo."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with FileLock(_lock_path(path)):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def read_bills() -> dict:
    """Lee bills.json y devuelve el dict completo (con meta + bills)."""
    data = read_json(DATA_FILE, default=None)
    if data is None:
        write_json(DATA_FILE, _DEFAULT_BILLS)
        return dict(_DEFAULT_BILLS)
    return data


def write_bills(data: dict) -> None:
    """Escribe el dict completo de facturas en bills.json."""
    write_json(DATA_FILE, data)


def find_duplicate(name: str, amount: float, due_date: str) -> dict | None:
    """Busca una factura existente con igual name/amount/dueDate.

    La comparación de name es case-insensitive y sin espacios extremos.
    Retorna la factura existente o None.
    """
    data = read_bills()
    normalized = name.strip().lower()
    for bill in data.get("bills", []):
        if (
            bill.get("name", "").strip().lower() == normalized
            and bill.get("amount") == amount
            and bill.get("dueDate") == due_date
        ):
            return bill
    return None
