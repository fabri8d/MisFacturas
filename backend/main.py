"""MisFacturas v2 — API backend principal.

Todos los endpoints protegidos requieren JWT de Supabase Auth.
Bills y configuración se persisten en Supabase PostgreSQL.
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

import drive_service
import groq_service
import notifier
import webhook_service
from auth import get_current_user
from constants import CATEGORIES
from models import BillCreate, BillResponse, BillUpdate, ReceiptResponse, SummaryItem
from supabase_client import supabase

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ALLOWED_SCAN_TYPES = {"image/jpeg", "image/png", "application/pdf"}

_MONTHS_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    notifier.start_scheduler()
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
async def get_bills(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    current_user: dict = Depends(get_current_user),
):
    uid = current_user["id"]
    query = supabase.table("bills").select("*").eq("user_id", uid).order("due_date")
    if month:
        query = query.eq("month", month)
    resp = query.execute()
    return [BillResponse.from_supabase(row) for row in resp.data]


@app.post("/api/bills/import", status_code=200)
async def import_bills(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Reemplaza todas las facturas del usuario con el contenido de un bills.json exportado."""
    uid = current_user["id"]
    raw = await file.read()
    try:
        incoming = json.loads(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Archivo JSON inválido")
    if not isinstance(incoming, dict) or "bills" not in incoming:
        raise HTTPException(status_code=400, detail="Formato incorrecto: falta la clave 'bills'")

    supabase.table("bills").delete().eq("user_id", uid).execute()

    rows = []
    for b in incoming["bills"]:
        due = b.get("dueDate") or b.get("due_date")
        if not due:
            continue
        rows.append({
            "user_id": uid,
            "name": b.get("name", ""),
            "category": b.get("category", "otro"),
            "amount": float(b.get("amount", 0)),
            "due_date": due,
            "month": due[:7],
            "is_paid": bool(b.get("isPaid") or b.get("is_paid", False)),
            "paid_date": b.get("paidDate") or b.get("paid_date"),
            "notes": b.get("notes"),
            "source": b.get("source", "manual"),
        })
    if rows:
        supabase.table("bills").insert(rows).execute()
    return {"ok": True, "imported": len(rows)}


@app.post("/api/bills", response_model=BillResponse, status_code=201)
async def create_bill(bill: BillCreate, current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]

    # Deduplicación: mismo nombre (case-insensitive) + amount + due_date para este usuario
    dup = (
        supabase.table("bills")
        .select("*")
        .eq("user_id", uid)
        .ilike("name", bill.name)
        .eq("amount", str(bill.amount))
        .eq("due_date", bill.due_date)
        .limit(1)
        .execute()
    )
    if dup.data:
        existing = BillResponse.from_supabase(dup.data[0])
        raise HTTPException(
            status_code=409,
            detail={"message": "Ya existe una factura similar", "existing": existing.model_dump(by_alias=True)},
        )

    row = {
        "user_id": uid,
        "name": bill.name,
        "category": bill.category,
        "amount": bill.amount,
        "due_date": bill.due_date,
        "month": bill.due_date[:7],
        "is_paid": bill.is_paid,
        "paid_date": bill.paid_date if bill.is_paid else None,
        "notes": bill.notes,
        "source": bill.source,
    }
    # Campos opcionales de Drive (cuando se sube desde la web)
    if bill.drive_file_id:
        row["drive_file_id"] = bill.drive_file_id
    if bill.drive_folder_id:
        row["drive_folder_id"] = bill.drive_folder_id
    if bill.drive_web_view_link:
        row["drive_web_view_link"] = bill.drive_web_view_link
    resp = supabase.table("bills").insert(row).execute()
    created = BillResponse.from_supabase(resp.data[0])

    asyncio.create_task(
        webhook_service.fire(
            "bill.created",
            {"id": created.id, "name": created.name, "category": created.category,
             "amount": created.amount, "dueDate": created.due_date, "source": created.source},
            user_id=uid,
        )
    )
    return created


@app.put("/api/bills/{bill_id}", response_model=BillResponse)
async def update_bill(
    bill_id: str, bill: BillUpdate, current_user: dict = Depends(get_current_user)
):
    uid = current_user["id"]
    check = supabase.table("bills").select("id").eq("id", bill_id).eq("user_id", uid).limit(1).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    update = bill.model_dump(exclude_none=True, by_alias=False)
    if not update:
        row = supabase.table("bills").select("*").eq("id", bill_id).single().execute()
        return BillResponse.from_supabase(row.data)

    due_date_changed = "due_date" in update
    if due_date_changed:
        update["month"] = update["due_date"][:7]
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    resp = supabase.table("bills").update(update).eq("id", bill_id).eq("user_id", uid).execute()
    updated_bill = BillResponse.from_supabase(resp.data[0])

    # Si cambió la fecha y la factura tiene archivo en Drive → reorganizar en background
    if due_date_changed and updated_bill.drive_file_id:
        bill_dict = resp.data[0]
        asyncio.create_task(
            _reorganize_bill_file_background(bill_dict, uid)
        )

    return updated_bill


async def _reorganize_bill_file_background(bill: dict, user_id: str) -> None:
    """Reorganiza el archivo en Drive tras un cambio de fecha. No bloquea la respuesta."""
    drive_updates = await drive_service.organize_bill_file(bill, user_id)
    if drive_updates:
        supabase.table("bills").update(drive_updates).eq("id", bill["id"]).execute()


@app.delete("/api/bills/{bill_id}", status_code=204)
async def delete_bill(bill_id: str, current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    resp = supabase.table("bills").delete().eq("id", bill_id).eq("user_id", uid).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Factura no encontrada")


@app.patch("/api/bills/{bill_id}/toggle-paid", response_model=BillResponse)
async def toggle_paid(bill_id: str, current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    check = (
        supabase.table("bills").select("*").eq("id", bill_id).eq("user_id", uid).limit(1).execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    current = check.data[0]
    new_paid = not bool(current.get("is_paid", False))
    update = {
        "is_paid": new_paid,
        "paid_date": date.today().isoformat() if new_paid else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = supabase.table("bills").update(update).eq("id", bill_id).eq("user_id", uid).execute()
    updated = BillResponse.from_supabase(resp.data[0])

    if new_paid:
        asyncio.create_task(
            webhook_service.fire(
                "bill.paid",
                {"id": updated.id, "name": updated.name, "category": updated.category,
                 "amount": updated.amount, "dueDate": updated.due_date, "source": updated.source},
                user_id=uid,
            )
        )
    return updated


@app.get("/api/summary", response_model=list[SummaryItem])
async def get_summary(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    months: Optional[int] = Query(None, ge=1, le=24),
    current_user: dict = Depends(get_current_user),
):
    """Resumen de facturas.

    - ?year=YYYY  → devuelve los 12 meses del año (default: año actual)
    - ?months=N   → devuelve los últimos N meses (modo legacy, mantiene compat)
    """
    uid = current_user["id"]
    resp = supabase.table("bills").select("month,amount,is_paid").eq("user_id", uid).execute()
    bills = resp.data

    today = date.today()

    # Modo legacy: últimos N meses
    if months is not None and year is None:
        result = []
        for i in range(months - 1, -1, -1):
            y = today.year
            m = today.month - i
            while m <= 0:
                m += 12
                y -= 1
            month_str = f"{y:04d}-{m:02d}"
            month_bills = [b for b in bills if b.get("month") == month_str]
            total = sum(float(b.get("amount", 0)) for b in month_bills)
            paid = sum(float(b.get("amount", 0)) for b in month_bills if b.get("is_paid"))
            label = f"{_MONTHS_ES[m - 1]} {y}"
            result.append(SummaryItem(month=month_str, label=label, total=total, paid=paid))
        return result

    # Modo año: siempre los 12 meses del año solicitado
    target_year = year if year is not None else today.year
    result = []
    for m in range(1, 13):
        month_str = f"{target_year:04d}-{m:02d}"
        month_bills = [b for b in bills if b.get("month") == month_str]
        total = sum(float(b.get("amount", 0)) for b in month_bills)
        paid = sum(float(b.get("amount", 0)) for b in month_bills if b.get("is_paid"))
        result.append(SummaryItem(month=month_str, label=_MONTHS_ES[m - 1], total=total, paid=paid))
    return result


@app.get("/api/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Devuelve el perfil del usuario autenticado, sincronizando avatar desde Auth metadata."""
    uid = current_user["id"]
    profile_resp = (
        supabase.table("profiles")
        .select("avatar_url,full_name,email")
        .eq("id", uid)
        .single()
        .execute()
    )
    profile = profile_resp.data or {}

    # Sincronizar avatar/nombre desde Auth metadata si no está en el profile
    meta = current_user.get("user_metadata", {})
    update = {}
    if not profile.get("avatar_url") and meta.get("avatar_url"):
        update["avatar_url"] = meta["avatar_url"]
    if not profile.get("full_name") and meta.get("full_name"):
        update["full_name"] = meta["full_name"]
    if update:
        supabase.table("profiles").update(update).eq("id", uid).execute()
        profile.update(update)

    return {
        "id": uid,
        "email": profile.get("email") or current_user["email"],
        "full_name": profile.get("full_name") or meta.get("full_name"),
        "avatar_url": profile.get("avatar_url") or meta.get("avatar_url"),
    }


# ─── AI scan ───────────────────────────────────────────────────────────────────

@app.post("/api/scan-invoice")
async def scan_invoice(
    invoice: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    if invoice.content_type not in ALLOWED_SCAN_TYPES:
        raise HTTPException(status_code=415, detail="Tipo de archivo no soportado. Usá JPEG, PNG o PDF.")
    file_bytes = await invoice.read()
    return await groq_service.scan_invoice(file_bytes, invoice.content_type)


# ─── Notifications ─────────────────────────────────────────────────────────────

@app.get("/api/notifications/config")
async def notifications_config(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    profile = (
        supabase.table("profiles")
        .select("notifications_enabled,telegram_chat_id")
        .eq("id", uid)
        .single()
        .execute()
    )
    data = profile.data or {}
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    return {
        "enabled": data.get("notifications_enabled", True),
        "telegram_configured": bool(token and data.get("telegram_chat_id")),
        "telegram_chat_id": data.get("telegram_chat_id"),
    }


@app.patch("/api/notifications/config")
async def update_notifications_config(
    body: dict, current_user: dict = Depends(get_current_user)
):
    uid = current_user["id"]
    update = {}
    if "notifications_enabled" in body:
        update["notifications_enabled"] = bool(body["notifications_enabled"])
    if "telegram_chat_id" in body:
        update["telegram_chat_id"] = body["telegram_chat_id"] or None
    if update:
        supabase.table("profiles").update(update).eq("id", uid).execute()
    return {"ok": True}


@app.post("/api/notifications/test")
async def notifications_test(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    profile = (
        supabase.table("profiles")
        .select("telegram_chat_id")
        .eq("id", uid)
        .single()
        .execute()
    )
    chat_id = ((profile.data or {}).get("telegram_chat_id") or "").strip()
    if not token or not chat_id:
        return {"ok": False, "message": "Telegram no configurado (falta token del bot o tu chat_id en el perfil)"}
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

@app.get("/api/drive/status")
async def drive_status(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    profile = (
        supabase.table("profiles")
        .select(
            "drive_access_token,drive_account_email,drive_folder_id,"
            "drive_folder_name,drive_channel_expiry"
        )
        .eq("id", uid)
        .single()
        .execute()
    )
    data = profile.data or {}
    expiry = data.get("drive_channel_expiry")
    return {
        "connected": bool(data.get("drive_access_token")),
        "folder_id": data.get("drive_folder_id"),
        "folder_name": data.get("drive_folder_name"),
        "account_email": data.get("drive_account_email"),
        "channel_expiry": str(expiry) if expiry else None,
    }


@app.get("/api/drive/oauth/start")
async def drive_oauth_start(current_user: dict = Depends(get_current_user)):
    """Inicia el flujo OAuth de Google Drive para el usuario autenticado."""
    from jose import jwt as jose_jwt
    state = jose_jwt.encode(
        {"user_id": current_user["id"]},
        os.environ.get("SUPABASE_JWT_SECRET", "secret"),
        algorithm="HS256",
    )
    auth_url = drive_service.get_auth_url(state=state)
    return {"auth_url": auth_url}


@app.get("/api/drive/oauth/callback")
async def drive_oauth_callback(code: str, state: str = ""):
    """Callback OAuth de Google Drive — intercambia el code y guarda tokens en el profile."""
    from jose import jwt as jose_jwt, JWTError
    try:
        payload = jose_jwt.decode(
            state, os.environ.get("SUPABASE_JWT_SECRET", "secret"), algorithms=["HS256"]
        )
        user_id = payload["user_id"]
    except (JWTError, KeyError):
        raise HTTPException(status_code=400, detail="State OAuth inválido")
    try:
        await drive_service.exchange_code(code, user_id)
    except Exception as exc:
        logger.error("[DRIVE] exchange_code error: %s", exc)
        return RedirectResponse(url=f"{FRONTEND_URL}/settings?drive=error")
    return RedirectResponse(url=f"{FRONTEND_URL}/settings?drive=connected")


@app.post("/api/drive/set-folder")
async def drive_set_folder(body: dict, current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    folder_id = body.get("folder_id", "").strip()
    if not folder_id:
        raise HTTPException(status_code=400, detail="folder_id requerido")
    try:
        service = await drive_service.get_drive_service(uid)
        folder = service.files().get(fileId=folder_id, fields="name,mimeType").execute()
        if "folder" not in folder.get("mimeType", ""):
            raise HTTPException(status_code=400, detail="El ID no corresponde a una carpeta")
    except drive_service.DriveNotConnectedException:
        raise HTTPException(status_code=401, detail="Drive no conectado")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Carpeta inaccesible: {exc}")

    await drive_service.stop_watch_channel(uid)
    await drive_service.create_watch_channel(folder_id, uid)
    profile_resp = (
        supabase.table("profiles")
        .select("drive_folder_name")
        .eq("id", uid)
        .single()
        .execute()
    )
    folder_name = (profile_resp.data or {}).get("drive_folder_name", folder_id)
    return {"ok": True, "folder_name": folder_name}


@app.post("/api/drive/disconnect")
async def drive_disconnect(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    supabase.table("profiles").update({
        "drive_access_token": None,
        "drive_refresh_token": None,
        "drive_token_expiry": None,
        "drive_account_email": None,
        "drive_folder_id": None,
        "drive_folder_name": None,
        "drive_channel_id": None,
        "drive_channel_expiry": None,
        "drive_resource_id": None,
    }).eq("id", uid).execute()
    return {"ok": True}


@app.post("/api/drive/webhook")
async def drive_webhook(request: Request):
    """Receptor de push notifications de Google Drive. Mapea channel_id → user_id via Supabase."""
    resource_state = request.headers.get("x-goog-resource-state")
    changed = request.headers.get("x-goog-changed", "")
    channel_id = request.headers.get("x-goog-channel-id", "")

    if resource_state == "sync":
        return {"ok": True}

    if resource_state in ("add", "update") and "children" in changed and channel_id:
        profile_resp = (
            supabase.table("profiles")
            .select("id,drive_folder_id")
            .eq("drive_channel_id", channel_id)
            .limit(1)
            .execute()
        )
        if profile_resp.data:
            profile = profile_resp.data[0]
            user_id = profile["id"]
            folder_id = profile["drive_folder_id"]
            if folder_id:
                asyncio.create_task(drive_service.process_new_files(folder_id, user_id))

    return {"ok": True}


@app.post("/api/drive/upload")
async def drive_upload(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Sube una factura desde la web a Drive, la escanea y retorna datos para el formulario."""
    uid = current_user["id"]
    max_size = 20 * 1024 * 1024  # 20 MB

    allowed_types = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=415, detail="Tipo de archivo no soportado. Usá JPEG, PNG o PDF.")

    file_bytes = await file.read()
    if len(file_bytes) > max_size:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máximo 20 MB)")

    profile_data = drive_service.get_user_profile(uid)
    if not profile_data.get("drive_access_token"):
        raise HTTPException(status_code=400, detail="Drive no configurado")
    root_folder_id = profile_data.get("drive_folder_id")
    if not root_folder_id:
        raise HTTPException(status_code=400, detail="Carpeta de Drive no configurada")

    service = await drive_service.get_drive_service(uid)

    # Escanear con IA
    scan_result = await groq_service.scan_invoice(file_bytes, file.content_type)

    # Determinar carpeta de destino según fecha detectada
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = f"{ts}-{file.filename or 'factura'}"

    if scan_result.get("dueDate"):
        try:
            due = date.fromisoformat(scan_result["dueDate"])
            folder_id = drive_service.get_month_folder(root_folder_id, due, "Facturas", service)
        except Exception:
            folder_id = root_folder_id
    else:
        folder_id = root_folder_id
        safe_name = f"SIN-FECHA-{safe_name}"

    drive_file = drive_service.upload_file_to_folder(
        file_bytes, safe_name, file.content_type, folder_id, service
    )

    return {
        "scanResult": scan_result,
        "driveFileId": drive_file["id"],
        "driveFolderId": folder_id,
        "driveWebViewLink": drive_file.get("webViewLink"),
    }


# ─── Webhooks salientes ────────────────────────────────────────────────────────

@app.get("/api/webhooks/config")
async def webhooks_config(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    profile = (
        supabase.table("profiles").select("webhook_url,webhook_secret").eq("id", uid).single().execute()
    )
    data = profile.data or {}
    url = data.get("webhook_url") or ""
    secret = data.get("webhook_secret") or ""
    return {
        "url_set": bool(url),
        "secret_set": bool(secret),
        "url_preview": url[:30] if url else None,
    }


@app.post("/api/webhooks/save")
async def webhooks_save(body: dict, current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    update = {}
    if "webhook_url" in body:
        update["webhook_url"] = body["webhook_url"] or None
    if "webhook_secret" in body:
        update["webhook_secret"] = body["webhook_secret"] or None
    if update:
        supabase.table("profiles").update(update).eq("id", uid).execute()
    return {"ok": True}


@app.post("/api/webhooks/test")
async def webhooks_test(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    profile = (
        supabase.table("profiles").select("webhook_url,webhook_secret").eq("id", uid).single().execute()
    )
    data = profile.data or {}
    url = (data.get("webhook_url") or "").strip()
    secret = (data.get("webhook_secret") or "").strip()

    if not url:
        return {"ok": False, "status_code": None, "error": "No hay webhook URL configurada"}

    await webhook_service.fire(
        "webhook.test",
        {"message": "Test desde MisFacturas", "timestamp": datetime.now(timezone.utc).isoformat()},
        url=url, secret=secret, user_id=uid,
    )
    log_resp = (
        supabase.table("webhook_logs")
        .select("*")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    last = log_resp.data[0] if log_resp.data else {}
    return {
        "ok": last.get("error") is None,
        "status_code": last.get("status_code"),
        "error": last.get("error"),
    }


@app.get("/api/webhooks/log")
async def webhooks_log(current_user: dict = Depends(get_current_user)):
    uid = current_user["id"]
    resp = (
        supabase.table("webhook_logs")
        .select("*")
        .eq("user_id", uid)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    return resp.data


# ─── Comprobantes de pago ───────────────────────────────────────────────────────

ALLOWED_RECEIPT_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_RECEIPT_SIZE = 10 * 1024 * 1024  # 10 MB


@app.get("/api/bills/receipts/summary")
async def receipts_summary(current_user: dict = Depends(get_current_user)):
    """Conteo de comprobantes por factura del usuario. { bill_id: count }"""
    uid = current_user["id"]
    resp = (
        supabase.table("receipts")
        .select("bill_id")
        .eq("user_id", uid)
        .execute()
    )
    counts: dict = {}
    for row in (resp.data or []):
        bid = str(row["bill_id"])
        counts[bid] = counts.get(bid, 0) + 1
    return counts


@app.post("/api/bills/{bill_id}/receipts", status_code=201)
async def upload_receipt(
    bill_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Sube un comprobante de pago a Drive y lo vincula con la factura."""
    uid = current_user["id"]

    # Verificar ownership
    bill_resp = (
        supabase.table("bills")
        .select("*")
        .eq("id", bill_id)
        .eq("user_id", uid)
        .single()
        .execute()
    )
    if not bill_resp.data:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    bill = bill_resp.data

    # Validaciones
    if file.content_type not in ALLOWED_RECEIPT_TYPES:
        raise HTTPException(status_code=415, detail="Tipo de archivo no soportado. Usá JPEG, PNG o PDF.")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_RECEIPT_SIZE:
        raise HTTPException(status_code=413, detail="Archivo demasiado grande (máximo 10 MB)")

    if not bill.get("due_date"):
        raise HTTPException(
            status_code=400,
            detail="La factura no tiene fecha de vencimiento. "
                   "Editá la factura para agregar la fecha antes de subir el comprobante.",
        )

    # Verificar Drive conectado
    profile = drive_service.get_user_profile(uid)
    if not profile.get("drive_access_token"):
        raise HTTPException(status_code=400, detail="Drive no conectado. Configuralo en Ajustes.")
    root_folder_id = profile.get("drive_folder_id")
    if not root_folder_id:
        raise HTTPException(status_code=400, detail="Carpeta de Drive no configurada.")

    # Obtener carpeta Comprobantes/mes
    service = await drive_service.get_drive_service(uid)
    due = date.fromisoformat(str(bill["due_date"]))
    folder_id = drive_service.get_month_folder(root_folder_id, due, "Comprobantes", service)

    # Subir a Drive con timestamp para evitar colisiones
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_name = f"{ts}-{file.filename or 'comprobante'}"
    drive_file = drive_service.upload_file_to_folder(
        file_bytes, safe_name, file.content_type, folder_id, service
    )

    # Guardar en tabla receipts
    receipt_row = {
        "user_id": uid,
        "bill_id": bill_id,
        "drive_file_id": drive_file["id"],
        "drive_folder_id": folder_id,
        "file_name": file.filename or safe_name,
        "file_size": len(file_bytes),
        "mime_type": file.content_type,
        "drive_web_view_link": drive_file.get("webViewLink"),
        "drive_web_content_link": drive_file.get("webContentLink"),
    }
    ins = supabase.table("receipts").insert(receipt_row).execute()
    receipt = ins.data[0]

    # Marcar factura como pagada si no lo estaba
    was_paid = bool(bill.get("is_paid"))
    if not was_paid:
        supabase.table("bills").update({
            "is_paid": True,
            "paid_date": date.today().isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", bill_id).execute()

    return ReceiptResponse.from_supabase(receipt)


@app.get("/api/bills/{bill_id}/receipts")
async def list_receipts(
    bill_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Lista todos los comprobantes de una factura."""
    uid = current_user["id"]

    check = (
        supabase.table("bills").select("id").eq("id", bill_id).eq("user_id", uid).limit(1).execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    resp = (
        supabase.table("receipts")
        .select("*")
        .eq("bill_id", bill_id)
        .eq("user_id", uid)
        .order("uploaded_at", desc=True)
        .execute()
    )
    return [ReceiptResponse.from_supabase(r) for r in (resp.data or [])]


@app.delete("/api/bills/{bill_id}/receipts/{receipt_id}", status_code=204)
async def delete_receipt(
    bill_id: str,
    receipt_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Elimina un comprobante de Drive y de Supabase."""
    uid = current_user["id"]

    # Verificar ownership del bill y del receipt
    r_resp = (
        supabase.table("receipts")
        .select("*")
        .eq("id", receipt_id)
        .eq("bill_id", bill_id)
        .eq("user_id", uid)
        .single()
        .execute()
    )
    if not r_resp.data:
        raise HTTPException(status_code=404, detail="Comprobante no encontrado")
    receipt = r_resp.data

    # Eliminar de Drive (silencioso si ya no existe)
    try:
        service = await drive_service.get_drive_service(uid)
        service.files().delete(fileId=receipt["drive_file_id"]).execute()
    except Exception as exc:
        logger.warning("[RECEIPTS] No se pudo eliminar de Drive: %s", exc)

    # Eliminar de Supabase
    supabase.table("receipts").delete().eq("id", receipt_id).execute()


@app.post("/api/bills/{bill_id}/drive-organize")
async def drive_organize_bill(
    bill_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Reorganiza manualmente el archivo de una factura en Drive según su fecha."""
    uid = current_user["id"]
    bill_resp = (
        supabase.table("bills").select("*").eq("id", bill_id).eq("user_id", uid).single().execute()
    )
    if not bill_resp.data:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    bill = bill_resp.data
    if not bill.get("drive_file_id"):
        return {"ok": False, "reason": "La factura no tiene archivo en Drive"}
    if not bill.get("due_date"):
        return {"ok": False, "reason": "La factura no tiene fecha de vencimiento"}

    drive_updates = await drive_service.organize_bill_file(bill, uid)
    if drive_updates:
        supabase.table("bills").update(drive_updates).eq("id", bill_id).execute()
        return {"ok": True, "driveWebViewLink": drive_updates.get("drive_web_view_link")}
    return {"ok": False, "reason": "No se pudo reorganizar el archivo"}
