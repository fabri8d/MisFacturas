"""MisFacturas — API backend principal.

Registra todos los routers bajo el prefijo /api y gestiona el ciclo de vida
del scheduler de APScheduler dentro del contexto de FastAPI (lifespan).
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()  # carga .env antes de que los módulos lean variables de entorno

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

import drive_service
import groq_service
import notifier
import storage
import webhook_service
from constants import CATEGORIES
from models import BillCreate, BillResponse, BillUpdate, SummaryItem

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
NOTIFICATIONS_LOG = os.getenv("NOTIFICATIONS_LOG", "/data/notifications_log.json")
WEBHOOK_LOG = os.getenv("WEBHOOK_LOG", "/data/webhook_log.json")
DRIVE_CONFIG = os.getenv("DRIVE_CONFIG", "/data/drive_config.json")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "").strip()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el inicio y cierre del scheduler."""
    notifier.start_scheduler()

    # Auto-configurar carpeta de Drive desde DRIVE_FOLDER_ID si OAuth ya está hecho
    if DRIVE_FOLDER_ID:
        try:
            config = storage.read_json(DRIVE_CONFIG, default={})
            if config.get("refresh_token") and config.get("watch_folder_id") != DRIVE_FOLDER_ID:
                logger.info("[MAIN] Configurando carpeta Drive desde env: %s", DRIVE_FOLDER_ID)
                await drive_service.stop_watch_channel()
                await drive_service.create_watch_channel(DRIVE_FOLDER_ID)
        except Exception as exc:
            logger.warning("[MAIN] Auto Drive folder setup error: %s", exc)

    # Renovar canal de Drive si expira pronto
    try:
        config = storage.read_json(DRIVE_CONFIG, default={})
        expiry_str = config.get("channel_expiry")
        if expiry_str and config.get("watch_folder_id"):
            expiry = datetime.fromisoformat(expiry_str)
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < datetime.now(timezone.utc) + timedelta(days=1):
                asyncio.create_task(drive_service.renew_channel())
    except Exception as exc:
        logger.warning("[MAIN] Drive channel check error: %s", exc)

    # Job de renovación de canal cada 6 días
    try:
        notifier.scheduler.add_job(
            drive_service.renew_channel,
            "interval",
            days=6,
            id="drive_channel_renew",
            replace_existing=True,
        )
    except Exception as exc:
        logger.warning("[MAIN] Drive renew job error: %s", exc)

    yield

    notifier.stop_scheduler()


app = FastAPI(title="MisFacturas API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


# ─── Bills CRUD ────────────────────────────────────────────────────────────────

@app.get("/api/bills", response_model=list[BillResponse])
async def get_bills(month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$")):
    """Devuelve todas las facturas, opcionalmente filtradas por mes (YYYY-MM), ordenadas por dueDate."""
    data = storage.read_bills()
    bills = data.get("bills", [])
    if month:
        bills = [b for b in bills if b.get("month") == month]
    bills.sort(key=lambda b: b.get("dueDate", ""))
    return bills


@app.post("/api/bills/import", status_code=200)
async def import_bills(file: UploadFile = File(...)):
    """Reemplaza todas las facturas con el contenido de un bills.json exportado."""
    raw = await file.read()
    try:
        incoming = __import__("json").loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Archivo JSON inválido")
    if not isinstance(incoming, dict) or "bills" not in incoming:
        raise HTTPException(status_code=400, detail="Formato incorrecto: falta la clave 'bills'")
    current = storage.read_bills()
    current["bills"] = incoming["bills"]
    storage.write_bills(current)
    return {"ok": True, "imported": len(incoming["bills"])}


@app.post("/api/bills", response_model=BillResponse, status_code=201)
async def create_bill(bill: BillCreate):
    """Crea una nueva factura. id y month se calculan server-side.

    Retorna HTTP 409 si ya existe una factura con el mismo name/amount/dueDate.
    """
    existing = storage.find_duplicate(bill.name, bill.amount, bill.dueDate)
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"message": "Ya existe una factura similar", "existing": existing},
        )

    data = storage.read_bills()
    new_bill = {
        "id": str(uuid.uuid4()),
        "name": bill.name,
        "category": bill.category,
        "amount": bill.amount,
        "dueDate": bill.dueDate,
        "month": bill.dueDate[:7],
        "isPaid": bill.isPaid,
        "paidDate": bill.paidDate if bill.isPaid else None,
        "notes": bill.notes,
        "source": bill.source,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    data["bills"].append(new_bill)
    storage.write_bills(data)

    asyncio.create_task(
        webhook_service.fire(
            "bill.created",
            {k: new_bill[k] for k in ("id", "name", "category", "amount", "dueDate", "isPaid", "source")},
        )
    )
    return new_bill


@app.put("/api/bills/{bill_id}", response_model=BillResponse)
async def update_bill(bill_id: str, bill: BillUpdate):
    """Actualiza los campos enviados de una factura. Devuelve 404 si no existe."""
    data = storage.read_bills()
    for idx, b in enumerate(data["bills"]):
        if b["id"] == bill_id:
            update = bill.model_dump(exclude_none=True)
            if "dueDate" in update:
                update["month"] = update["dueDate"][:7]
            data["bills"][idx].update(update)
            storage.write_bills(data)
            return data["bills"][idx]
    raise HTTPException(status_code=404, detail="Factura no encontrada")


@app.delete("/api/bills/{bill_id}", status_code=204)
async def delete_bill(bill_id: str):
    """Elimina una factura. Devuelve 404 si no existe."""
    data = storage.read_bills()
    original_len = len(data["bills"])
    data["bills"] = [b for b in data["bills"] if b["id"] != bill_id]
    if len(data["bills"]) == original_len:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    storage.write_bills(data)


@app.patch("/api/bills/{bill_id}/toggle-paid", response_model=BillResponse)
async def toggle_paid(bill_id: str):
    """Alterna el estado de pago. Si pasa a pagada, registra la fecha de hoy."""
    data = storage.read_bills()
    for idx, b in enumerate(data["bills"]):
        if b["id"] == bill_id:
            new_paid = not b.get("isPaid", False)
            data["bills"][idx]["isPaid"] = new_paid
            data["bills"][idx]["paidDate"] = date.today().isoformat() if new_paid else None
            storage.write_bills(data)
            if new_paid:
                bill = data["bills"][idx]
                asyncio.create_task(
                    webhook_service.fire(
                        "bill.paid",
                        {k: bill[k] for k in ("id", "name", "category", "amount", "dueDate", "isPaid", "source")},
                    )
                )
            return data["bills"][idx]
    raise HTTPException(status_code=404, detail="Factura no encontrada")


@app.get("/api/summary", response_model=list[SummaryItem])
async def get_summary(months: int = Query(6, ge=1, le=24)):
    """Devuelve el resumen de los últimos N meses (total y pagado por mes)."""
    from calendar import month_name as _month_name

    data = storage.read_bills()
    bills = data.get("bills", [])

    today = date.today()
    result = []

    for i in range(months - 1, -1, -1):
        # Mes corriente menos i meses
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_str = f"{year:04d}-{month:02d}"

        month_bills = [b for b in bills if b.get("month") == month_str]
        total = sum(b.get("amount", 0) for b in month_bills)
        paid = sum(b.get("amount", 0) for b in month_bills if b.get("isPaid"))

        # Label en español, minúsculas (locale manual para evitar dependencias del OS)
        _MONTHS_ES = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
        ]
        label = f"{_MONTHS_ES[month - 1]} {year}"

        result.append(SummaryItem(month=month_str, label=label, total=total, paid=paid))

    return result


# ─── AI scan ───────────────────────────────────────────────────────────────────

ALLOWED_SCAN_TYPES = {"image/jpeg", "image/png", "application/pdf"}


@app.post("/api/scan-invoice")
async def scan_invoice(invoice: UploadFile = File(...)):
    """Escanea una factura con Groq y devuelve los campos detectados. Siempre HTTP 200."""
    if invoice.content_type not in ALLOWED_SCAN_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de archivo no soportado. Usá JPEG, PNG o PDF.",
        )
    file_bytes = await invoice.read()
    result = await groq_service.scan_invoice(file_bytes, invoice.content_type)
    return result


# ─── Notifications ─────────────────────────────────────────────────────────────

@app.get("/api/notifications/config")
async def notifications_config():
    data = storage.read_bills()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    return {
        "enabled": data.get("meta", {}).get("notifications_enabled", True),
        "telegram_configured": bool(token and chat_id),
    }



@app.post("/api/notifications/test")
async def notifications_test():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return {"ok": False, "message": "Telegram no configurado (falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID)"}
    try:
        from telegram import Bot
        bot = Bot(token=token)
        await bot.send_message(
            chat_id=chat_id,
            text="✅ *MisFacturas* — Notificaciones funcionando correctamente.",
            parse_mode="Markdown",
        )
        return {"ok": True, "message": "Mensaje de prueba enviado correctamente"}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}


# ─── Google Drive ───────────────────────────────────────────────────────────────


@app.get("/api/drive/oauth/callback")
async def drive_oauth_callback(code: str):
    drive_service.exchange_code(code)
    return RedirectResponse(url=f"{FRONTEND_URL}/settings?drive=connected")


@app.get("/api/drive/status")
async def drive_status():
    config = storage.read_json(DRIVE_CONFIG, default={})
    connected = bool(config.get("refresh_token"))
    return {
        "connected": connected,
        "folder_id": config.get("watch_folder_id"),
        "folder_name": config.get("watch_folder_name"),
        "account_email": config.get("account_email"),
        "channel_expiry": config.get("channel_expiry"),
    }


@app.post("/api/drive/set-folder")
async def drive_set_folder(body: dict):
    folder_id = body.get("folder_id", "").strip()
    if not folder_id:
        raise HTTPException(status_code=400, detail="folder_id requerido")
    try:
        service = drive_service.get_drive_service()
        folder = service.files().get(fileId=folder_id, fields="name,mimeType").execute()
        if "folder" not in folder.get("mimeType", ""):
            raise HTTPException(status_code=400, detail="El ID no corresponde a una carpeta")
    except drive_service.DriveNotConnectedException:
        raise HTTPException(status_code=401, detail="Drive no conectado")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Carpeta inaccesible: {exc}")

    await drive_service.stop_watch_channel()
    await drive_service.create_watch_channel(folder_id)
    config = storage.read_json(DRIVE_CONFIG, default={})
    return {"ok": True, "folder_name": config.get("watch_folder_name", folder_id)}


@app.post("/api/drive/disconnect")
async def drive_disconnect():
    await drive_service.stop_watch_channel()
    import pathlib
    pathlib.Path(DRIVE_CONFIG).unlink(missing_ok=True)
    return {"ok": True}


@app.post("/api/drive/webhook")
async def drive_webhook(request: Request):
    """Receptor de push notifications de Google Drive. Siempre devuelve HTTP 200."""
    print(f"[DRIVE] Webhook headers: {dict(request.headers)}")
    print(f"[DRIVE] Resource-State: {request.headers.get('x-goog-resource-state')}")
    resource_state = request.headers.get("x-goog-resource-state")
    changed = request.headers.get("x-goog-changed", "")

    if resource_state == "sync":
        return {"ok": True}

    if resource_state in ("add", "update") and "children" in changed:
        config = storage.read_json(DRIVE_CONFIG, default={})
        folder_id = config.get("watch_folder_id")
        if folder_id:
            asyncio.create_task(drive_service.process_new_files(folder_id))

    return {"ok": True}


# ─── Webhooks salientes ────────────────────────────────────────────────────────

@app.get("/api/webhooks/config")
async def webhooks_config():
    data = storage.read_bills()
    meta = data.get("meta", {})
    url = meta.get("webhook_url", "")
    secret = meta.get("webhook_secret", "")
    return {
        "url_set": bool(url),
        "secret_set": bool(secret),
        "url_preview": url[:30] if url else None,
    }



@app.post("/api/webhooks/test")
async def webhooks_test():
    try:
        await webhook_service.fire(
            "webhook.test",
            {"message": "Test desde MisFacturas", "timestamp": datetime.now(timezone.utc).isoformat()},
        )
        log = storage.read_json(WEBHOOK_LOG, default=[])
        last = log[-1] if log else {}
        return {
            "ok": last.get("error") is None,
            "status_code": last.get("status_code"),
            "error": last.get("error"),
        }
    except Exception as exc:
        return {"ok": False, "status_code": None, "error": str(exc)}


@app.get("/api/webhooks/log")
async def webhooks_log():
    log = storage.read_json(WEBHOOK_LOG, default=[])
    return log[-10:]
