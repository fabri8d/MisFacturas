"""Servicio de webhooks salientes de MisFacturas v2.

Envía eventos a una URL configurada por el usuario con firma HMAC-SHA256 opcional.
Nunca lanza excepciones — todos los errores se loguean.
Soporta webhooks por usuario (url/secret desde profile de Supabase) y global (env vars).
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


async def fire(
    event_type: str,
    payload: dict,
    *,
    url: Optional[str] = None,
    secret: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """Dispara un webhook saliente para el evento dado.

    Si url/secret no se pasan, se leen de WEBHOOK_URL/WEBHOOK_SECRET env vars.
    Si user_id se pasa, el resultado se loguea en la tabla webhook_logs de Supabase.
    """
    status_code: Optional[int] = None
    error: Optional[str] = None

    try:
        webhook_url = (url or "").strip() or os.getenv("WEBHOOK_URL", "").strip()
        webhook_secret = (secret or "").strip() or os.getenv("WEBHOOK_SECRET", "").strip()

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
        if user_id:
            _append_supabase_log(event_type, status_code, error, user_id)


def _append_supabase_log(
    event_type: str,
    status_code: Optional[int],
    error: Optional[str],
    user_id: str,
) -> None:
    """Registra el resultado del webhook en la tabla webhook_logs de Supabase."""
    try:
        from supabase_client import supabase
        supabase.table("webhook_logs").insert({
            "user_id": user_id,
            "event": event_type,
            "status_code": status_code,
            "error": error,
        }).execute()
    except Exception as exc:
        logger.error("[WEBHOOK] Error al guardar log en Supabase: %s", exc)
