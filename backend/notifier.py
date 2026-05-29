"""Notificaciones de Telegram y scheduler diario de MisFacturas.

El AsyncIOScheduler se inicializa dentro del lifespan de FastAPI (no como proceso separado).
El job diario revisa facturas próximas a vencer y envía un mensaje por cada una.
"""

import logging
import os
from datetime import date, datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.error import TelegramError

import storage
import webhook_service
from constants import CATEGORIES

logger = logging.getLogger(__name__)

NOTIFICATIONS_LOG = os.getenv("NOTIFICATIONS_LOG", "/data/notifications_log.json")
NOTIFY_HOUR = int(os.getenv("NOTIFY_HOUR", "9"))

scheduler = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")


async def _send_telegram(token: str, chat_id: str, text: str) -> None:
    """Envía un mensaje de Telegram formateado en Markdown."""
    bot = Bot(token=token)
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")


async def daily_notification_job() -> None:
    """Job diario: envía notificaciones para facturas que vencen en ≤ 3 días."""
    try:
        data = storage.read_bills()
        meta = data.get("meta", {})

        if not meta.get("notifications_enabled", True):
            logger.info("[NOTIFIER] Notificaciones deshabilitadas — skipping")
            return

        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        if not token or not chat_id:
            logger.warning("[NOTIFIER] TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados")
            return

        log: dict = storage.read_json(NOTIFICATIONS_LOG, default={})
        today = date.today()
        today_str = today.isoformat()
        due_today_bills = []

        for bill in data.get("bills", []):
            if bill.get("isPaid"):
                continue

            try:
                due = date.fromisoformat(bill["dueDate"])
            except (KeyError, ValueError):
                continue

            days = (due - today).days

            if days < 0 or days > 3:
                continue

            if log.get(bill["id"]) == today_str:
                continue

            emoji_map = {0: "🔴", 1: "🟠", 2: "🟡", 3: "🔔"}
            label_map = {
                0: "Vencimiento HOY",
                1: "Vence mañana",
                2: "Vence en 2 días",
                3: "Vence en 3 días",
            }
            emoji = emoji_map[days]
            label = label_map[days]

            cat = CATEGORIES.get(bill.get("category", "otro"), CATEGORIES["otro"])
            amount_fmt = f"{bill['amount']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            text = (
                f"{emoji} *{label}*\n"
                f"📋 {bill['name']} — {cat['label']} {cat['emoji']}\n"
                f"💰 ${amount_fmt}\n"
                f"📅 Vence: {_fmt_date(bill['dueDate'])}"
            )

            try:
                await _send_telegram(token, chat_id, text)
                log[bill["id"]] = today_str
                storage.write_json(NOTIFICATIONS_LOG, log)
                logger.info(
                    "[NOTIFIER] %s | %s → sent ✓",
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    bill["name"],
                )
                if days == 0:
                    due_today_bills.append(bill)
            except TelegramError as exc:
                logger.error(
                    "[NOTIFIER] %s | %s → ERROR: %s",
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    bill["name"],
                    exc,
                )

        if due_today_bills:
            await webhook_service.fire(
                "bill.due_today",
                {
                    "bills": [
                        {
                            "id": b["id"],
                            "name": b["name"],
                            "amount": b["amount"],
                            "dueDate": b["dueDate"],
                            "days_until_due": 0,
                        }
                        for b in due_today_bills
                    ]
                },
            )

    except Exception as exc:
        logger.error("[NOTIFIER] Job error: %s", exc)


def _fmt_date(date_str: str) -> str:
    """Convierte YYYY-MM-DD a DD/MM/YYYY."""
    try:
        d = date.fromisoformat(date_str)
        return d.strftime("%d/%m/%Y")
    except ValueError:
        return date_str


def start_scheduler() -> None:
    """Inicia el scheduler y registra el job diario de notificaciones."""
    scheduler.add_job(
        daily_notification_job,
        "cron",
        hour=NOTIFY_HOUR,
        minute=0,
        id="daily_notifications",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[NOTIFIER] Scheduler iniciado — job diario a las %02d:00 ART", NOTIFY_HOUR)


def stop_scheduler() -> None:
    """Detiene el scheduler limpiamente."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
