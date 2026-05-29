"""Servicio de webhooks salientes de MisFacturas.

Envía eventos a una URL configurada por el usuario con firma HMAC-SHA256 opcional.
Nunca lanza excepciones — todos los errores se loguean y se guardan en el log.
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone

import httpx

import storage

logger = logging.getLogger(__name__)

WEBHOOK_LOG = os.getenv("WEBHOOK_LOG", "/data/webhook_log.json")
_MAX_LOG_ENTRIES = 10


async def fire(event_type: str, payload: dict) -> None:
    """Dispara un webhook saliente para el evento dado.

    Args:
        event_type: Nombre del evento (p. ej. "bill.created").
        payload: Datos específicos del evento.
    """
    status_code: int | None = None
    error: str | None = None

    try:
        # Env vars tienen prioridad; bills.json meta como fallback legacy
        webhook_url = os.getenv("WEBHOOK_URL", "").strip()
        webhook_secret = os.getenv("WEBHOOK_SECRET", "").strip()
        if not webhook_url:
            meta = storage.read_bills().get("meta", {})
            webhook_url = meta.get("webhook_url", "").strip()
            webhook_secret = webhook_secret or meta.get("webhook_secret", "").strip()

        if not webhook_url:
            return

        body = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }
        body_bytes = json.dumps(body, ensure_ascii=False).encode()

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if webhook_secret:
            sig = hmac.new(webhook_secret.encode(), body_bytes, hashlib.sha256).hexdigest()
            headers["X-Signature"] = f"sha256={sig}"

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(webhook_url, content=body_bytes, headers=headers)
            status_code = response.status_code

        logger.info("[WEBHOOK] %s → %s", event_type, status_code)

    except Exception as exc:
        error = str(exc)
        logger.error("[WEBHOOK] %s → ERROR: %s", event_type, error)

    finally:
        _append_log(event_type, status_code, error)


def _append_log(event_type: str, status_code: int | None, error: str | None) -> None:
    """Agrega una entrada al webhook_log.json y mantiene solo las últimas 10."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        "status_code": status_code,
        "error": error,
    }
    log = storage.read_json(WEBHOOK_LOG, default=[])
    if not isinstance(log, list):
        log = []
    log.append(entry)
    storage.write_json(WEBHOOK_LOG, log[-_MAX_LOG_ENTRIES:])
