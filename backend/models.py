"""Esquemas Pydantic v2 para la API de MisFacturas v2 (Supabase)."""

import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from constants import CATEGORY_KEYS

CategoryKey = Literal[
    "electricidad", "gas", "agua", "internet", "telefono",
    "alquiler", "expensas", "seguro", "streaming", "otro",
]

SourceKey = Literal["manual", "drive"]


def _snake_to_camel(name: str) -> str:
    """Convierte snake_case a camelCase para serialización de respuestas."""
    parts = name.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class BillCreate(BaseModel):
    """Cuerpo de la petición para crear una nueva factura.

    Acepta tanto camelCase (desde el frontend) como snake_case.
    """

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1)
    category: CategoryKey
    amount: float = Field(..., gt=0)
    due_date: str = Field(..., alias="dueDate", pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: Optional[str] = None
    is_paid: bool = Field(False, alias="isPaid")
    paid_date: Optional[str] = Field(None, alias="paidDate", pattern=r"^\d{4}-\d{2}-\d{2}$")
    source: SourceKey = "manual"

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in CATEGORY_KEYS:
            return "otro"
        return v


class BillUpdate(BaseModel):
    """Cuerpo de la petición para actualizar una factura (todos los campos opcionales)."""

    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(None, min_length=1)
    category: Optional[CategoryKey] = None
    amount: Optional[float] = Field(None, gt=0)
    due_date: Optional[str] = Field(None, alias="dueDate", pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: Optional[str] = None
    is_paid: Optional[bool] = Field(None, alias="isPaid")
    paid_date: Optional[str] = Field(None, alias="paidDate", pattern=r"^\d{4}-\d{2}-\d{2}$")
    source: Optional[SourceKey] = None

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in CATEGORY_KEYS:
            return "otro"
        return v


class BillResponse(BaseModel):
    """Factura completa devuelta por la API. Serializada como camelCase."""

    model_config = ConfigDict(
        alias_generator=_snake_to_camel,
        populate_by_name=True,
    )

    id: str
    name: str
    category: str
    amount: float
    due_date: str
    month: str
    is_paid: bool
    paid_date: Optional[str]
    notes: Optional[str]
    source: str
    drive_file_id: Optional[str] = None
    created_at: str

    @classmethod
    def from_supabase(cls, row: dict) -> "BillResponse":
        """Crea un BillResponse a partir de una fila de Supabase.

        Convierte campos DATE/TIMESTAMPTZ a strings y normaliza nulos.
        """
        def _str(v) -> Optional[str]:
            if v is None:
                return None
            if hasattr(v, "isoformat"):
                return v.isoformat()
            return str(v)

        return cls(
            id=str(row["id"]),
            name=row["name"],
            category=row["category"],
            amount=float(row["amount"]),
            due_date=_str(row["due_date"]),
            month=row["month"],
            is_paid=bool(row.get("is_paid", False)),
            paid_date=_str(row.get("paid_date")),
            notes=row.get("notes"),
            source=row.get("source", "manual"),
            drive_file_id=row.get("drive_file_id"),
            created_at=_str(row.get("created_at", "")),
        )


class SummaryItem(BaseModel):
    """Ítem del resumen histórico por mes."""

    month: str      # "YYYY-MM"
    label: str      # "mayo 2025" (locale es-AR, minúsculas)
    total: float
    paid: float
