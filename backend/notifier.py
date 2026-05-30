"""Notificaciones de Telegram y scheduler multi-usuario de MisFacturas v2.

El AsyncIOScheduler corre dentro del lifespan de FastAPI.
El job diario itera por todos los usuarios con Telegram configurado.
"""

import logging
import os
from datetime import date, datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.error import TelegramError

import webhook_service
from constants import CATEGORIES
from supabase_client import supabase

logger = logging.getLogger(__name__)

NOTIFY_HOUR = int(os.getenv("NOTIFY_HOUR", "9"))

scheduler = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")


async def _send_telegram(token: str, chat_id: str, text: str) -> None:
    bot = Bot(token=token)
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")


async def daily_notification_job() -> None:
    """Job diario: itera todos los usuarios con Telegram configurado y envía notificaciones."""
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            logger.warning("[NOTIFIER] TELEGRAM_BOT_TOKEN no configurado — skipping")
            return

        # Obtener todos los usuarios con Telegram configurado y notificaciones habilitadas
        profiles_resp = (
            supabase.table("profiles")
            .select("id,telegram_chat_id")
            .eq("notifications_enabled", True)
            .not_.is_("telegram_chat_id", "null")
            .execute()
        )
        profiles = profiles_resp.data or []
        logger.info("[NOTIFIER] Procesando %d usuarios con Telegram configurado", len(profiles))

        today = date.today()
        today_str = today.isoformat()

        for profile in profiles:
            user_id = profile["id"]
            chat_id = (profile.get("telegram_chat_id") or "").strip()
            if not chat_id:
                continue

            await _notify_user(token, chat_id, user_id, today, today_str)

    except Exception as exc:
        logger.error("[NOTIFIER] Job error: %s", exc)


async def _notify_user(
    token: str, chat_id: str, user_id: str, today: date, today_str: str
) -> None:
    """Envía notificaciones para las facturas pendientes del usuario."""
    try:
        bills_resp = (
            supabase.table("bills")
            .select("id,name,category,amount,due_date")
            .eq("user_id", user_id)
            .eq("is_paid", False)
            .execute()
        )
        bills = bills_resp.data or []

        due_today_bills = []

        for bill in bills:
            try:
                due = date.fromisoformat(str(bill["due_date"]))
            except (KeyError, ValueError):
                continue

            days = (due - today).days
            if days < 0 or days > 3:
                continue

            # Deduplicación: verificar si ya se notificó hoy
            log_resp = (
                supabase.table("notification_logs")
                .select("id")
                .eq("bill_id", bill["id"])
                .eq("notified_at", today_str)
                .limit(1)
                .execute()
            )
            if log_resp.data:
                continue

            emoji_map = {0: "🔴", 1: "🟠", 2: "🟡", 3: "🔔"}
            label_map = {
                0: "Vencimiento HOY",
                1: "Vence mañana",
                2: "Vence en 2 días",
                3: "Vence en 3 días",
            }
            cat = CATEGORIES.get(bill.get("category", "otro"), CATEGORIES["otro"])
            amount_fmt = (
                f"{float(bill['amount']):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )

            text = (
                f"{emoji_map[days]} *{label_map[days]}*\n"
                f"📋 {bill['name']} — {cat['label']} {cat['emoji']}\n"
                f"💰 ${amount_fmt}\n"
                f"📅 Vence: {_fmt_date(str(bill['due_date']))}"
            )

            try:
                await _send_telegram(token, chat_id, text)
                supabase.table("notification_logs").insert({
                    "user_id": user_id,
                    "bill_id": bill["id"],
                    "notified_at": today_str,
                }).execute()
                logger.info("[NOTIFIER] user %s | %s → sent ✓", user_id[:8], bill["name"])

                if days == 0:
                    due_today_bills.append(bill)
            except TelegramError as exc:
                logger.error("[NOTIFIER] user %s | %s → ERROR: %s", user_id[:8], bill["name"], exc)

        if due_today_bills:
            await webhook_service.fire(
                "bill.due_today",
                {
                    "bills": [
                        {"id": b["id"], "name": b["name"], "amount": float(b["amount"]),
                         "dueDate": str(b["due_date"]), "days_until_due": 0}
                        for b in due_today_bills
                    ]
                },
                user_id=user_id,
            )

    except Exception as exc:
        logger.error("[NOTIFIER] _notify_user %s error: %s", user_id[:8], exc)


async def supabase_keepalive() -> None:
    """Ping a Supabase para evitar la pausa automática del free tier (cada 3 días)."""
    try:
        supabase.table("profiles").select("id").limit(1).execute()
        logger.info("[KEEPALIVE] Supabase ping OK")
    except Exception as exc:
        logger.error("[KEEPALIVE] Error: %s", exc)


def _fmt_date(date_str: str) -> str:
    try:
        d = date.fromisoformat(date_str)
        return d.strftime("%d/%m/%Y")
    except ValueError:
        return date_str


def start_scheduler() -> None:
    scheduler.add_job(
        daily_notification_job,
        "cron",
        hour=NOTIFY_HOUR,
        minute=0,
        id="daily_notifications",
        replace_existing=True,
    )
    scheduler.add_job(
        supabase_keepalive,
        "interval",
        days=3,
        id="supabase_keepalive",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("[NOTIFIER] Scheduler iniciado — notificaciones a las %02d:00 ART", NOTIFY_HOUR)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
