"""Integración con Google Drive v2 — tokens OAuth por usuario en Supabase.

Cada usuario tiene sus propios tokens guardados en la tabla profiles.
Incluye organización automática en subcarpetas año/mes/tipo.
"""

import asyncio
import logging
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from io import BytesIO

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

import groq_service
import webhook_service
from constants import CATEGORIES
from supabase_client import supabase

logger = logging.getLogger(__name__)

MONTHS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

APP_BASE_URL = os.getenv("APP_BASE_URL", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    f"{APP_BASE_URL}/api/drive/oauth/callback",
)

_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

_CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uris": [GOOGLE_REDIRECT_URI],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

# Un lock por usuario para serializar webhooks concurrentes del mismo usuario
_processing_locks: dict[str, asyncio.Lock] = {}


class DriveNotConnectedException(Exception):
    pass


def _get_lock(user_id: str) -> asyncio.Lock:
    if user_id not in _processing_locks:
        _processing_locks[user_id] = asyncio.Lock()
    return _processing_locks[user_id]


def get_auth_url(state: str = "") -> str:
    """Genera la URL de autorización OAuth para que el usuario la abra en el browser."""
    flow = Flow.from_client_config(_CLIENT_CONFIG, scopes=_SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    kwargs: dict = {"access_type": "offline", "prompt": "consent"}
    if state:
        kwargs["state"] = state
    auth_url, _ = flow.authorization_url(**kwargs)
    return auth_url


async def exchange_code(code: str, user_id: str) -> None:
    """Intercambia el código de autorización por tokens y los guarda en el profile del usuario."""
    flow = Flow.from_client_config(_CLIENT_CONFIG, scopes=_SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)
    creds = flow.credentials

    account_email = _get_email(creds)
    expiry_ts = creds.expiry.isoformat() if creds.expiry else None

    supabase.table("profiles").update({
        "drive_access_token": creds.token,
        "drive_refresh_token": creds.refresh_token,
        "drive_token_expiry": expiry_ts,
        "drive_account_email": account_email,
    }).eq("id", user_id).execute()

    logger.info("[DRIVE] OAuth completado para user %s — cuenta: %s", user_id[:8], account_email)


async def get_drive_service(user_id: str):
    """Devuelve un cliente autenticado de la Drive API para el usuario.

    Refresca el token si está vencido y actualiza el profile.
    Lanza DriveNotConnectedException si no hay tokens.
    """
    profile_resp = (
        supabase.table("profiles")
        .select("drive_access_token,drive_refresh_token,drive_token_expiry")
        .eq("id", user_id)
        .single()
        .execute()
    )
    profile = profile_resp.data or {}

    if not profile.get("drive_refresh_token"):
        raise DriveNotConnectedException("Drive no configurado para este usuario")

    creds = Credentials(
        token=profile.get("drive_access_token"),
        refresh_token=profile["drive_refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=_SCOPES,
    )

    if not creds.valid:
        creds.refresh(Request())
        expiry_ts = creds.expiry.isoformat() if creds.expiry else None
        supabase.table("profiles").update({
            "drive_access_token": creds.token,
            "drive_token_expiry": expiry_ts,
        }).eq("id", user_id).execute()

    return build("drive", "v3", credentials=creds)


async def create_watch_channel(folder_id: str, user_id: str) -> None:
    """Crea un canal push en Drive para la carpeta del usuario."""
    service = await get_drive_service(user_id)
    channel_id = str(uuid.uuid4())
    expiry_ms = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp() * 1000)

    response = service.files().watch(
        fileId=folder_id,
        body={
            "id": channel_id,
            "type": "web_hook",
            "address": f"{APP_BASE_URL}/api/drive/webhook",
            "expiration": expiry_ms,
        },
    ).execute()

    folder_name = _get_folder_name(service, folder_id)
    channel_expiry = datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc).isoformat()

    supabase.table("profiles").update({
        "drive_folder_id": folder_id,
        "drive_folder_name": folder_name,
        "drive_channel_id": channel_id,
        "drive_channel_expiry": channel_expiry,
        "drive_resource_id": response.get("resourceId", ""),
    }).eq("id", user_id).execute()

    logger.info("[DRIVE] Canal creado — user %s folder: %s channel: %s", user_id[:8], folder_name, channel_id)


async def stop_watch_channel(user_id: str) -> None:
    """Detiene el canal push activo del usuario. Silencioso si ya expiró o falla."""
    try:
        profile_resp = (
            supabase.table("profiles")
            .select("drive_channel_id,drive_resource_id")
            .eq("id", user_id)
            .single()
            .execute()
        )
        profile = profile_resp.data or {}
        channel_id = profile.get("drive_channel_id")
        resource_id = profile.get("drive_resource_id")

        if not channel_id or not resource_id:
            return

        service = await get_drive_service(user_id)
        service.channels().stop(body={"id": channel_id, "resourceId": resource_id}).execute()

        supabase.table("profiles").update({
            "drive_channel_id": None,
            "drive_channel_expiry": None,
            "drive_resource_id": None,
        }).eq("id", user_id).execute()
    except Exception as exc:
        logger.warning("[DRIVE] stop_watch_channel user %s: %s", user_id[:8], exc)


async def process_new_files(folder_id: str, user_id: str) -> None:
    """Descarga y escanea archivos nuevos en la carpeta del usuario."""
    async with _get_lock(user_id):
        await _do_process_new_files(folder_id, user_id)


async def _do_process_new_files(folder_id: str, user_id: str) -> None:
    try:
        service = await get_drive_service(user_id)
        logger.info("[DRIVE] Buscando archivos en carpeta %s para user %s", folder_id, user_id[:8])

        results = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                orderBy="modifiedTime desc",
                fields="files(id,name,mimeType,modifiedTime)",
                pageSize=5,
            )
            .execute()
        )

        all_files = results.get("files", [])
        allowed_types = {"image/jpeg", "image/png", "application/pdf"}
        filtered = [f for f in all_files if f.get("mimeType") in allowed_types]

        # Cargar drive_file_ids ya procesados para este usuario
        existing_resp = (
            supabase.table("bills")
            .select("drive_file_id")
            .eq("user_id", user_id)
            .not_.is_("drive_file_id", "null")
            .execute()
        )
        processed_ids = {row["drive_file_id"] for row in (existing_resp.data or [])}

        # Leer profile para Telegram del usuario
        profile_resp = (
            supabase.table("profiles")
            .select("telegram_chat_id")
            .eq("id", user_id)
            .single()
            .execute()
        )
        profile = profile_resp.data or {}
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = (profile.get("telegram_chat_id") or "").strip()

        for file in filtered:
            file_id = file["id"]
            filename = file["name"]
            mime_type = file["mimeType"]

            if file_id in processed_ids:
                logger.debug("[DRIVE] Saltando %s — ya procesado", filename)
                continue

            request = service.files().get_media(fileId=file_id)
            file_bytes = request.execute()

            result = await groq_service.scan_invoice(file_bytes, mime_type)

            if result.get("name") and result.get("amount") is not None:
                due = result.get("dueDate") or None
                detected_date = bool(due)
                due = due or date.today().isoformat()

                row = {
                    "user_id": user_id,
                    "name": result["name"],
                    "category": result.get("category") or "otro",
                    "amount": result["amount"],
                    "due_date": due,
                    "month": due[:7],
                    "is_paid": False,
                    "notes": result.get("notes"),
                    "source": "drive",
                    "drive_file_id": file_id,
                }

                # Organizar en subcarpeta si se detectó la fecha
                profile = get_user_profile(user_id)
                root_folder_id = profile.get("drive_folder_id") or folder_id
                if detected_date:
                    try:
                        dest_folder_id = get_month_folder(
                            root_folder_id, date.fromisoformat(due), "Facturas", service
                        )
                        updated = move_file(file_id, dest_folder_id, folder_id, service)
                        row["drive_folder_id"] = dest_folder_id
                        row["drive_web_view_link"] = updated.get("webViewLink")
                    except Exception as e:
                        logger.warning("[DRIVE] No se pudo mover archivo: %s", e)
                else:
                    # Sin fecha: renombrar con prefijo para identificar
                    try:
                        rename_file(file_id, f"SIN-FECHA-{filename}", service)
                    except Exception as e:
                        logger.warning("[DRIVE] No se pudo renombrar archivo: %s", e)

                bill_resp = supabase.table("bills").insert(row).execute()
                new_bill = bill_resp.data[0] if bill_resp.data else row

                cat = CATEGORIES.get(new_bill.get("category", "otro"), CATEGORIES["otro"])
                amount_fmt = f"{float(new_bill['amount']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                if token and chat_id:
                    from telegram import Bot
                    bot = Bot(token=token)
                    await bot.send_message(
                        chat_id=chat_id,
                        parse_mode="Markdown",
                        text=(
                            f"📥 *Factura detectada automáticamente*\n"
                            f"📋 {new_bill['name']} — {cat['label']} {cat['emoji']}\n"
                            f"💰 ${amount_fmt}\n"
                            f"📅 Vence: {_fmt_date(due)}\n"
                            f"✏️ Revisá en MisFacturas"
                        ),
                    )

                await webhook_service.fire(
                    "bill.auto_detected",
                    {"id": str(new_bill.get("id", "")), "name": new_bill["name"],
                     "category": new_bill.get("category"), "amount": new_bill["amount"],
                     "dueDate": due, "source": "drive"},
                    user_id=user_id,
                )
            else:
                if token and chat_id:
                    from telegram import Bot
                    bot = Bot(token=token)
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ Se subió '{filename}' a Drive pero no se pudo leer como factura.",
                    )
                await webhook_service.fire(
                    "bill.scan_failed", {"filename": filename, "error": "scan_failed"}, user_id=user_id
                )

    except Exception as exc:
        logger.error("[DRIVE] process_new_files error user %s: %s", user_id[:8], exc)


# ─── Helpers de organización en subcarpetas ────────────────────────────────────

def get_or_create_folder(parent_id: str, name: str, service) -> str:
    """Busca una carpeta por nombre dentro de parent_id. La crea si no existe."""
    query = (
        f"name='{name}' and '{parent_id}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )
    result = service.files().list(q=query, fields="files(id,name)", pageSize=1).execute()
    if result.get("files"):
        return result["files"][0]["id"]

    folder = service.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
        fields="id",
    ).execute()
    return folder["id"]


def get_month_folder(root_folder_id: str, due_date: date, subfolder: str, service) -> str:
    """Crea o retorna la carpeta año/mes/subfolder. subfolder = 'Facturas' | 'Comprobantes'."""
    year_id  = get_or_create_folder(root_folder_id, str(due_date.year), service)
    month_name = f"{due_date.month:02d} - {MONTHS_ES[due_date.month]}"
    month_id = get_or_create_folder(year_id, month_name, service)
    return get_or_create_folder(month_id, subfolder, service)


def move_file(file_id: str, new_parent_id: str, old_parent_id: str, service) -> dict:
    """Mueve un archivo de carpeta. Retorna el file actualizado con links."""
    return service.files().update(
        fileId=file_id,
        addParents=new_parent_id,
        removeParents=old_parent_id,
        fields="id,name,webViewLink,webContentLink",
    ).execute()


def rename_file(file_id: str, new_name: str, service) -> None:
    """Renombra un archivo en Drive."""
    service.files().update(fileId=file_id, body={"name": new_name}).execute()


def upload_file_to_folder(
    file_bytes: bytes, file_name: str, mime_type: str, folder_id: str, service
) -> dict:
    """Sube un archivo a una carpeta específica de Drive.
    Retorna { id, name, webViewLink, webContentLink }.
    """
    media = MediaIoBaseUpload(BytesIO(file_bytes), mimetype=mime_type, resumable=False)
    file_metadata = {"name": file_name, "parents": [folder_id]}
    return service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id,name,webViewLink,webContentLink",
    ).execute()


def get_user_profile(user_id: str) -> dict:
    """Lee el profile del usuario desde Supabase."""
    resp = (
        supabase.table("profiles")
        .select("drive_folder_id,drive_access_token,telegram_chat_id")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return resp.data or {}


async def organize_bill_file(bill: dict, user_id: str) -> dict | None:
    """Mueve el archivo de una factura a su subcarpeta correcta según due_date.

    Retorna los campos de Drive actualizados o None si no se puede organizar.
    """
    if not bill.get("drive_file_id"):
        return None
    try:
        service = await get_drive_service(user_id)
        profile = get_user_profile(user_id)
        root_folder_id = profile.get("drive_folder_id")
        if not root_folder_id:
            return None

        due_date = date.fromisoformat(str(bill["due_date"]))
        dest_folder_id = get_month_folder(root_folder_id, due_date, "Facturas", service)

        old_parent = bill.get("drive_folder_id") or root_folder_id
        updated = move_file(
            file_id=bill["drive_file_id"],
            new_parent_id=dest_folder_id,
            old_parent_id=old_parent,
            service=service,
        )
        return {
            "drive_folder_id": dest_folder_id,
            "drive_web_view_link": updated.get("webViewLink"),
        }
    except Exception as exc:
        logger.warning("[DRIVE] organize_bill_file error: %s", exc)
        return None


async def upload_file_to_drive(
    file_bytes: bytes, filename: str, mime_type: str, user_id: str
) -> str:
    """Compatibilidad hacia atrás — sube a la carpeta raíz del usuario. Retorna file_id."""
    service = await get_drive_service(user_id)
    profile = get_user_profile(user_id)
    folder_id = profile.get("drive_folder_id")
    if not folder_id:
        raise ValueError("No hay carpeta de Drive configurada para este usuario")
    result = upload_file_to_folder(file_bytes, filename, mime_type, folder_id, service)
    return result["id"]


def _get_email(creds) -> str:
    try:
        service = build("oauth2", "v2", credentials=creds)
        info = service.userinfo().get().execute()
        return info.get("email", "")
    except Exception:
        return ""


def _get_folder_name(service, folder_id: str) -> str:
    try:
        folder = service.files().get(fileId=folder_id, fields="name").execute()
        return folder.get("name", folder_id)
    except Exception:
        return folder_id


def _fmt_date(date_str: str) -> str:
    try:
        d = date.fromisoformat(date_str)
        return d.strftime("%d/%m/%Y")
    except ValueError:
        return date_str
