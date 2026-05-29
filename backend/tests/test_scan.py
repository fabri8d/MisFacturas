"""Tests del endpoint de escaneo de facturas con IA (Groq)."""

from unittest.mock import AsyncMock, patch

import pytest


async def test_scan_unsupported_file_type(client):
    """Archivos que no son imagen ni PDF → 415."""
    r = await client.post(
        "/api/scan-invoice",
        files={"invoice": ("doc.txt", b"hello world", "text/plain")},
    )
    assert r.status_code == 415


async def test_scan_returns_null_on_groq_error(client):
    """Si Groq lanza excepción → HTTP 200 con todos los campos null."""
    with patch("groq_service.scan_invoice", new=AsyncMock(return_value={
        "name": None, "category": None, "amount": None, "dueDate": None, "notes": None,
    })):
        r = await client.post(
            "/api/scan-invoice",
            files={"invoice": ("factura.jpg", b"fake-image-bytes", "image/jpeg")},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] is None
    assert body["amount"] is None
    assert body["dueDate"] is None


async def test_scan_category_fallback_to_otro():
    """Respuesta de Groq con category inválida → se normaliza a 'otro'."""
    from groq_service import _parse_response

    result = _parse_response('{"name":"Test","category":"inexistente","amount":1000,"dueDate":"2026-06-01","notes":""}')
    assert result["category"] is None  # inválida → None (luego el endpoint/store usa "otro")


async def test_scan_invalid_date_returns_null():
    """Fecha inválida en respuesta de Groq → dueDate=None."""
    from groq_service import _parse_response

    result = _parse_response('{"name":"Test","category":"gas","amount":500,"dueDate":"32/13/2026","notes":""}')
    assert result["dueDate"] is None


async def test_scan_strips_markdown_fences():
    """Groq a veces envuelve el JSON en ```json ... ``` — debe parsearlo igual."""
    from groq_service import _parse_response

    raw = '```json\n{"name":"EPEC","category":"electricidad","amount":15000,"dueDate":"2026-06-10","notes":""}\n```'
    result = _parse_response(raw)
    assert result["name"] == "EPEC"
    assert result["amount"] == 15000.0


async def test_scan_amount_rounded_to_2_decimals():
    """El monto se redondea a 2 decimales."""
    from groq_service import _parse_response

    result = _parse_response('{"name":"X","category":"agua","amount":1234.5678,"dueDate":null,"notes":""}')
    assert result["amount"] == 1234.57


async def test_scan_jpeg_accepted(client):
    """JPEG es un tipo aceptado → llega a groq_service (no 415)."""
    with patch("groq_service.scan_invoice", new=AsyncMock(return_value={
        "name": "Test", "category": "otro", "amount": 100, "dueDate": None, "notes": None,
    })):
        r = await client.post(
            "/api/scan-invoice",
            files={"invoice": ("img.jpg", b"\xff\xd8\xff", "image/jpeg")},
        )
    assert r.status_code == 200


async def test_scan_pdf_accepted(client):
    """PDF es un tipo aceptado → llega a groq_service."""
    with patch("groq_service.scan_invoice", new=AsyncMock(return_value={
        "name": None, "category": None, "amount": None, "dueDate": None, "notes": None,
    })):
        r = await client.post(
            "/api/scan-invoice",
            files={"invoice": ("factura.pdf", b"%PDF-1.4", "application/pdf")},
        )
    assert r.status_code == 200
