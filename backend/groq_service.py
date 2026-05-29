"""Integración con la API de Groq para el escaneo de facturas.

Soporta imágenes JPEG/PNG (visión) y PDF (extraído como imagen con pdf2image).
Nunca lanza excepciones — ante cualquier error devuelve campos null.
"""

import base64
import io
import json
import logging
import os
import re

from groq import AsyncGroq

from constants import CATEGORY_KEYS

logger = logging.getLogger(__name__)

_GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
_PROMPT = (
    'Analizá esta factura argentina. Respondé SOLO con un objeto JSON válido, '
    'sin markdown, sin explicaciones, sin texto adicional: '
    '{"name":"empresa o servicio","category":"electricidad|gas|agua|internet|'
    'telefono|alquiler|expensas|seguro|streaming|otro","amount":número o null,'
    '"dueDate":"fecha de vencimiento en formato YYYY-MM-DD. '
    'IMPORTANTE: las facturas argentinas usan formato DD/MM/YYYY, '
    'por lo tanto 02/06/2026 significa el 2 de junio de 2026 '
    'y debe convertirse a 2026-06-02. NUNCA interpretes el primer número como el mes. '
    'Si no hay fecha, null",'
    '"notes":"info relevante o string vacío"}'
)

_NULL_RESULT: dict = {
    "name": None,
    "category": None,
    "amount": None,
    "dueDate": None,
    "notes": None,
}


async def scan_invoice(file_bytes: bytes, content_type: str) -> dict:
    """Escanea una factura con Groq y devuelve los campos detectados.

    Args:
        file_bytes: Contenido binario del archivo.
        content_type: MIME type del archivo ("image/jpeg", "image/png", "application/pdf").

    Returns:
        Dict con name, category, amount, dueDate, notes (cualquier campo puede ser None).
    """
    try:
        image_bytes, image_mime = _prepare_image(file_bytes, content_type)
        b64 = base64.b64encode(image_bytes).decode()
        data_url = f"data:{image_mime};base64,{b64}"

        client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        response = await client.chat.completions.create(
            model=_GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": _PROMPT},
                    ],
                }
            ],
            max_tokens=512,
        )

        raw = response.choices[0].message.content or ""
        return _parse_response(raw)

    except Exception as exc:
        logger.error("[GROQ] scan_invoice error: %s", exc)
        return dict(_NULL_RESULT)


def _prepare_image(file_bytes: bytes, content_type: str) -> tuple[bytes, str]:
    """Devuelve (image_bytes, mime_type). Convierte PDF a JPEG si es necesario."""
    if content_type == "application/pdf":
        from pdf2image import convert_from_bytes

        pages = convert_from_bytes(file_bytes, first_page=1, last_page=1)
        buf = io.BytesIO()
        pages[0].save(buf, format="JPEG")
        return buf.getvalue(), "image/jpeg"

    return file_bytes, content_type


def _parse_response(raw: str) -> dict:
    """Parsea la respuesta de Groq, valida campos y devuelve un dict limpio."""
    try:
        # Elimina posibles bloques markdown (```json ... ```)
        cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()
        data = json.loads(cleaned)

        category = data.get("category")
        if category not in CATEGORY_KEYS:
            category = None

        amount = data.get("amount")
        if amount is not None:
            try:
                amount = round(float(amount), 2)
            except (TypeError, ValueError):
                amount = None

        due_date = data.get("dueDate")
        if due_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(due_date)):
            due_date = None

        return {
            "name": data.get("name") or None,
            "category": category,
            "amount": amount,
            "dueDate": due_date,
            "notes": data.get("notes") or None,
        }

    except Exception as exc:
        logger.error("[GROQ] parse_response error: %s | raw: %.200s", exc, raw)
        return dict(_NULL_RESULT)
