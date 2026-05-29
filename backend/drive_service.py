"""Integración con Google Drive para la detección automática de facturas.

Implementa el flujo OAuth 2.0, gestión de canales de push notification
y procesamiento de archivos nuevos en una carpeta vigilada.
"""

import asyncio
import logging
import os
import uuid
from datetime import date, datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

import groq_service
import storage
import webhook_service
from constants import CATEGORIES

logger = logging.getLogger(__name__)

DRIVE_CONFIG = os.getenv("DRIVE_CONFIG", "/data/drive_config.json")
_PROCESSED_FILES_PATH = os.path.join(os.path.dirname(DRIVE_CONFIG), "processed_drive_files.json")
_RETENTION_DAYS = 30

# Lock global: garantiza que solo un proceso_new_files corre a la vez,
# eliminando la race condition entre webhooks concurrentes.
_processing_lock = asyncio.Lock()


def _check_and_mark(file_id: str) -> bool:
    """Lee el log, verifica si file_id ya fue procesado y, si no, lo marca.

    Operación atómica sobre el JSON: una sola lectura+escritura dentro del
    filelock existente, evitando que dos corrutinas lean antes de que la
    primera escriba. Retorna True si el archivo YA estaba procesado (skip).
    """
    data = storage.read_json(_PROCESSED_FILES_PATH, default={})
    if file_id in data:
        return True  # ya procesado
    today = date.today().isoformat()
    cutoff = (date.today() - timedelta(days=_RETENTION_DAYS)).isoformat()
    data[file_id] = today
    # Purgar entradas antiguas en la misma escritura
    data = {fid: d for fid, d in data.items() if d >= cutoff}
    storage.write_json(_PROCESSED_FILES_PATH, data)
    return False
APP_BASE_URL = os.getenv("APP_BASE_URL", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    f"{APP_BASE_URL}/api/drive/oauth/callback",
)

_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
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


class DriveNotConnectedException(Exception):
    pass


def get_auth_url() -> str:
    """Genera la URL de autorización OAuth para que el usuario la abra en el browser."""
    flow = Flow.from_client_config(_CLIENT_CONFIG, scopes=_SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return auth_url


def exchange_code(code: str) -> None:
    """Intercambia el código de autorización por tokens y los guarda en drive_config.json."""
    flow = Flow.from_client_config(_CLIENT_CONFIG, scopes=_SCOPES)
    flow.redirect_uri = GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)

    creds = flow.credentials
    existing = storage.read_json(DRIVE_CONFIG, default={})
    existing.update(
        {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token or existing.get("refresh_token", ""),
            "token_expiry": creds.expiry.isoformat() if creds.expiry else "",
            "account_email": _get_email(creds),
        }
    )
    storage.write_json(DRIVE_CONFIG, existing)
    logger.info("[DRIVE] OAuth completado — cuenta: %s", existing.get("account_email"))


def get_drive_service():
    """Devuelve un cliente autenticado de la Drive API.

    Refresca el token si está vencido. Lanza DriveNotConnectedException si no hay config.
    """
    config = storage.read_json(DRIVE_CONFIG, default=None)
    if not config or not config.get("refresh_token"):
        raise DriveNotConnectedException("Drive no configurado")

    creds = Credentials(
        token=config.get("access_token"),
        refresh_token=config.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=_SCOPES,
    )

    if not creds.valid:
        creds.refresh(Request())
        config["access_token"] = creds.token
        config["token_expiry"] = creds.expiry.isoformat() if creds.expiry else ""
        storage.write_json(DRIVE_CONFIG, config)

    return build("drive", "v3", credentials=creds)


async def create_watch_channel(folder_id: str) -> None:
    """Crea un canal push en Drive para la carpeta indicada."""
    config = storage.read_json(DRIVE_CONFIG, default={})
    channel_id = str(uuid.uuid4())
    expiry_ms = int((datetime.now(timezone.utc) + timedelta(days=7)).timestamp() * 1000)

    service = get_drive_service()

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

    config.update(
        {
            "watch_folder_id": folder_id,
            "watch_folder_name": folder_name,
            "channel_id": channel_id,
            "channel_expiry": datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc).isoformat(),
            "resource_id": response.get("resourceId", ""),
        }
    )
    storage.write_json(DRIVE_CONFIG, config)
    logger.info("[DRIVE] Canal creado — folder: %s, channel: %s", folder_name, channel_id)


async def stop_watch_channel() -> None:
    """Detiene el canal push activo. No lanza si ya expiró o falla."""
    try:
        config = storage.read_json(DRIVE_CONFIG, default={})
        channel_id = config.get("channel_id")
        resource_id = config.get("resource_id")
        if not channel_id or not resource_id:
            return

        service = get_drive_service()
        service.channels().stop(
            body={"id": channel_id, "resourceId": resource_id}
        ).execute()
    except Exception as exc:
        logger.warning("[DRIVE] stop_watch_channel: %s", exc)


async def renew_channel() -> None:
    """Renueva el canal push (detiene el actual y crea uno nuevo)."""
    try:
        config = storage.read_json(DRIVE_CONFIG, default={})
        folder_id = config.get("watch_folder_id")
        if not folder_id:
            return
        await stop_watch_channel()
        await create_watch_channel(folder_id)
        logger.info("[DRIVE] Channel renewed successfully")
    except Exception as exc:
        logger.error("[DRIVE] renew_channel error: %s", exc)


async def process_new_files(folder_id: str) -> None:
    """Descarga y escanea archivos nuevos en la carpeta vigilada.

    El lock global serializa las llamadas concurrentes, evitando que dos
    webhooks simultáneos procesen los mismos archivos.
    """
    async with _processing_lock:
        await _do_process_new_files(folder_id)


async def _do_process_new_files(folder_id: str) -> None:
    """Lógica interna de procesamiento (llamada solo bajo _processing_lock)."""
    try:
        service = get_drive_service()

        print(f"[DRIVE] Buscando archivos en carpeta {folder_id}")

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
        print(f"[DRIVE] Archivos encontrados: {[f['name'] for f in all_files]}")

        allowed_types = {"image/jpeg", "image/png", "application/pdf"}
        filtered = [f for f in all_files if f.get("mimeType") in allowed_types]
        print(f"[DRIVE] Archivos después del filtro de tipo: {[f['name'] for f in filtered]}")

        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

        for file in filtered:
            file_id = file["id"]
            filename = file["name"]
            mime_type = file["mimeType"]

            if _check_and_mark(file_id):
                print(f"[DRIVE] Saltando {filename} — {file_id} ya procesado")
                continue

            request = service.files().get_media(fileId=file_id)
            file_bytes = request.execute()

            result = await groq_service.scan_invoice(file_bytes, mime_type)

            if result.get("name") and result.get("amount") is not None:
                bill_data = storage.read_bills()
                new_bill = {
                    "id": str(uuid.uuid4()),
                    "name": result["name"],
                    "category": result.get("category") or "otro",
                    "amount": result["amount"],
                    "dueDate": result.get("dueDate") or date.today().isoformat(),
                    "month": (result.get("dueDate") or date.today().isoformat())[:7],
                    "isPaid": False,
                    "paidDate": None,
                    "notes": result.get("notes"),
                    "source": "drive",
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }
                bill_data["bills"].append(new_bill)
                storage.write_bills(bill_data)

                cat = CATEGORIES.get(new_bill["category"], CATEGORIES["otro"])
                due_display = _fmt_date(new_bill["dueDate"]) if new_bill.get("dueDate") else "no detectado"
                amount_fmt = f"{new_bill['amount']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

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
                            f"📅 Vence: {due_display}\n"
                            f"✏️ Revisá en MisFacturas"
                        ),
                    )

                await webhook_service.fire(
                    "bill.auto_detected",
                    {
                        "id": new_bill["id"],
                        "name": new_bill["name"],
                        "category": new_bill["category"],
                        "amount": new_bill["amount"],
                        "dueDate": new_bill["dueDate"],
                        "isPaid": False,
                        "source": "drive",
                    },
                )
            else:
                if token and chat_id:
                    from telegram import Bot
                    bot = Bot(token=token)
                    await bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ Se subió '{filename}' a Drive pero no se pudo leer como factura.",
                    )
                await webhook_service.fire("bill.scan_failed", {"filename": filename, "error": "scan_failed"})

    except Exception as exc:
        logger.error("[DRIVE] process_new_files error: %s", exc)


def _get_email(creds) -> str:
    """Obtiene el email de la cuenta autenticada."""
    try:
        service = build("oauth2", "v2", credentials=creds)
        info = service.userinfo().get().execute()
        return info.get("email", "")
    except Exception:
        return ""


def _get_folder_name(service, folder_id: str) -> str:
    """Obtiene el nombre de una carpeta de Drive por su ID."""
    try:
        folder = service.files().get(fileId=folder_id, fields="name").execute()
        return folder.get("name", folder_id)
    except Exception:
        return folder_id


def _fmt_date(date_str: str) -> str:
    """Convierte YYYY-MM-DD a DD/MM/YYYY."""
    try:
        from datetime import date
        d = date.fromisoformat(date_str)
        return d.strftime("%d/%m/%Y")
    except ValueError:
        return date_str
