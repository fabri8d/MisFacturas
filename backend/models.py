"""Esquemas Pydantic v2 para la API de MisFacturas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from constants import CATEGORY_KEYS

CategoryKey = Literal[
    "electricidad", "gas", "agua", "internet", "telefono",
    "alquiler", "expensas", "seguro", "streaming", "otro",
]

SourceKey = Literal["manual", "drive"]


class BillCreate(BaseModel):
    """Cuerpo de la petición para crear una nueva factura."""

    name: str = Field(..., min_length=1)
    category: CategoryKey
    amount: float = Field(..., gt=0)
    dueDate: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: Optional[str] = None
    isPaid: bool = False
    paidDate: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    source: SourceKey = "manual"

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in CATEGORY_KEYS:
            return "otro"
        return v


class BillUpdate(BaseModel):
    """Cuerpo de la petición para actualizar una factura (todos los campos opcionales)."""

    name: Optional[str] = Field(None, min_length=1)
    category: Optional[CategoryKey] = None
    amount: Optional[float] = Field(None, gt=0)
    dueDate: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    notes: Optional[str] = None
    isPaid: Optional[bool] = None
    paidDate: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    source: Optional[SourceKey] = None

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in CATEGORY_KEYS:
            return "otro"
        return v


class BillResponse(BaseModel):
    """Factura completa devuelta por la API."""

    id: str
    name: str
    category: str
    amount: float
    dueDate: str
    month: str
    isPaid: bool
    paidDate: Optional[str]
    notes: Optional[str]
    source: str
    createdAt: str


class SummaryItem(BaseModel):
    """Ítem del resumen histórico por mes."""

    month: str      # "YYYY-MM"
    label: str      # "mayo 2025" (locale es-AR, minúsculas)
    total: float
    paid: float
