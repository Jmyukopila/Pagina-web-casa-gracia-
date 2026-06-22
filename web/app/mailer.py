"""Transactional email: booking confirmations.

Design goals:
- **Never break a booking.** If SMTP isn't configured (no host / no from), or
  sending fails, we log and return quietly. The reservation already exists.
- **Non-blocking.** smtplib is synchronous, so we run it in a thread via
  asyncio.to_thread and schedule it as a FastAPI BackgroundTask.
- **Bilingual.** The guest gets the email in the language they were browsing.
- **No external deps.** Plain stdlib smtplib + email.message.

Configure via env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_TLS,
MAIL_FROM (e.g. "Casa Gracia <reservas@casagraciacartagena.com>").
"""
from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from .config import settings

log = logging.getLogger("casagracia.mail")


def _cop(value: int) -> str:
    try:
        return "$" + f"{int(value):,}".replace(",", ".") + " COP"
    except (ValueError, TypeError):
        return "$0 COP"


def _content(b: dict, lang: str) -> tuple[str, str, str]:
    """Return (subject, plain_text, html) for the confirmation email."""
    ref = b["reference"]
    name = b["guest_name"]
    room = b["room_name"]
    checkin = b["checkin"]
    checkout = b["checkout"]
    nights = b["nights"]
    guests = b["guests"]
    total = _cop(b["amount_cop"])
    url = b["manage_url"]
    hotel = settings.hotel_name

    if lang == "en":
        subject = f"Your booking at {hotel} · {ref}"
        plain = (
            f"Hi {name},\n\n"
            f"We've received your booking request. Here are the details:\n\n"
            f"Reference: {ref}\n"
            f"Room: {room}\n"
            f"Check-in: {checkin}\n"
            f"Check-out: {checkout}\n"
            f"Nights: {nights}\n"
            f"Guests: {guests}\n"
            f"Total: {total}\n\n"
            f"View your booking: {url}\n\n"
            f"We'll be in touch to confirm. Thank you for booking directly with us.\n"
            f"{hotel} · Cartagena de Indias"
        )
        rows = [
            ("Reference", ref), ("Room", room), ("Check-in", checkin),
            ("Check-out", checkout), ("Nights", nights), ("Guests", guests),
            ("Total", total),
        ]
        intro = f"Hi {name}, we've received your booking request."
        cta = "View your booking"
        outro = "We'll be in touch to confirm. Thank you for booking directly with us."
    else:
        subject = f"Tu reserva en {hotel} · {ref}"
        plain = (
            f"Hola {name},\n\n"
            f"Hemos recibido tu solicitud de reserva. Estos son los detalles:\n\n"
            f"Referencia: {ref}\n"
            f"Habitación: {room}\n"
            f"Entrada: {checkin}\n"
            f"Salida: {checkout}\n"
            f"Noches: {nights}\n"
            f"Huéspedes: {guests}\n"
            f"Total: {total}\n\n"
            f"Ver tu reserva: {url}\n\n"
            f"Te contactaremos para confirmar. Gracias por reservar directamente con nosotros.\n"
            f"{hotel} · Cartagena de Indias"
        )
        rows = [
            ("Referencia", ref), ("Habitación", room), ("Entrada", checkin),
            ("Salida", checkout), ("Noches", nights), ("Huéspedes", guests),
            ("Total", total),
        ]
        intro = f"Hola {name}, hemos recibido tu solicitud de reserva."
        cta = "Ver tu reserva"
        outro = "Te contactaremos para confirmar. Gracias por reservar directamente con nosotros."

    tr = "".join(
        f'<tr><td style="padding:6px 14px;color:#7a6a58">{k}</td>'
        f'<td style="padding:6px 14px;font-weight:600;color:#2b2118">{v}</td></tr>'
        for k, v in rows
    )
    html = f"""\
<!DOCTYPE html><html><body style="margin:0;background:#f6f1ea;font-family:Arial,Helvetica,sans-serif;color:#2b2118">
  <div style="max-width:560px;margin:0 auto;padding:24px">
    <h1 style="font-size:20px;color:#B88850;margin:0 0 4px">{hotel}</h1>
    <p style="margin:0 0 20px;color:#7a6a58">Cartagena de Indias</p>
    <div style="background:#fff;border-radius:14px;padding:24px;border:1px solid #ece3d6">
      <p style="margin:0 0 16px;font-size:15px">{intro}</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px">{tr}</table>
      <a href="{url}" style="display:inline-block;margin-top:20px;background:#B88850;color:#fff;
        text-decoration:none;padding:12px 22px;border-radius:10px;font-weight:600">{cta}</a>
      <p style="margin:20px 0 0;font-size:13px;color:#7a6a58">{outro}</p>
    </div>
  </div>
</body></html>"""
    return subject, plain, html


def _send_sync(to_email: str, subject: str, plain: str, html: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.mail_from
    msg["To"] = to_email
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
        if settings.smtp_tls:
            s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg)


async def send_booking_confirmation(booking: dict, lang: str = "es") -> None:
    """Fire-and-forget confirmation email. Safe no-op if mail isn't configured."""
    if not settings.mail_enabled:
        log.info("Mail not configured; skipping confirmation for %s",
                 booking.get("reference"))
        return
    to_email = booking.get("guest_email")
    if not to_email:
        return
    subject, plain, html = _content(booking, "en" if lang == "en" else "es")
    try:
        await asyncio.to_thread(_send_sync, to_email, subject, plain, html)
        log.info("Confirmation email sent for %s", booking.get("reference"))
    except Exception:
        log.exception("Failed to send confirmation email for %s",
                      booking.get("reference"))
