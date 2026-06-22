"""Server-rendered pages: home, rooms, booking flow, reviews, contact."""
from __future__ import annotations

from datetime import date, timedelta

from fastapi import (APIRouter, BackgroundTasks, Depends, Form, HTTPException,
                     Request, status)
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, i18n, mailer
from ..database import get_session
from ..deps import rate_limit, render, t_for
from ..config import settings
from ..payments import wompi
from ..schemas import BookingCreate, ReviewCreate

router = APIRouter()


# --- Home ------------------------------------------------------------------
@router.get("/")
async def home(request: Request, db: AsyncSession = Depends(get_session)):
    rooms = await crud.list_rooms(db)
    avg, count = await crud.average_rating(db)
    reviews = await crud.list_reviews(db, approved_only=True, limit=3)
    return render(request, "index.html",
                  rooms=rooms[:3], all_rooms=rooms,
                  rating_avg=avg, rating_count=count, reviews=reviews)


# --- Rooms -----------------------------------------------------------------
@router.get("/habitaciones")
async def rooms_list(request: Request, db: AsyncSession = Depends(get_session)):
    rooms = await crud.list_rooms(db)
    return render(request, "rooms.html", rooms=rooms)


@router.get("/habitaciones/{slug}")
async def room_detail(request: Request, slug: str,
                     db: AsyncSession = Depends(get_session)):
    room = await crud.get_room_by_slug(db, slug)
    if not room or not room.activa:
        raise HTTPException(404, "Habitación no encontrada.")
    today = date.today()
    return render(request, "room_detail.html", room=room,
                  default_checkin=(today + timedelta(days=7)).isoformat(),
                  default_checkout=(today + timedelta(days=9)).isoformat())


# --- Booking flow ----------------------------------------------------------
@router.get("/reservar")
async def booking_form(request: Request, room: str = "",
                      checkin: str = "", checkout: str = "",
                      db: AsyncSession = Depends(get_session)):
    room_obj = await crud.get_room_by_slug(db, room) if room else None
    rooms = await crud.list_rooms(db)
    return render(request, "booking.html", room=room_obj, rooms=rooms,
                  checkin=checkin, checkout=checkout)


@router.post("/reservar")
async def booking_submit(
    request: Request,
    background: BackgroundTasks,
    room_id: str = Form(...),
    guest_name: str = Form(...),
    guest_email: str = Form(...),
    guest_phone: str = Form(""),
    checkin: date = Form(...),
    checkout: date = Form(...),
    guests: int = Form(1),
    notes: str = Form(""),
    db: AsyncSession = Depends(get_session),
):
    await rate_limit(request, max_per_minute=15)
    t = t_for(request)
    # Validate via schema (gives clean errors).
    try:
        data = BookingCreate(room_id=room_id, guest_name=guest_name,
                             guest_email=guest_email, guest_phone=guest_phone,
                             checkin=checkin, checkout=checkout,
                             guests=guests, notes=notes)
    except ValidationError as e:
        rooms = await crud.list_rooms(db)
        room_obj = await crud.get_room(db, room_id)
        return render(request, "booking.html", room=room_obj, rooms=rooms,
                      checkin=str(checkin), checkout=str(checkout),
                      error=t("Revisa los datos del formulario."))

    room = await crud.get_room(db, data.room_id)
    if not room or not room.activa:
        raise HTTPException(404, t("Habitación no encontrada."))
    if data.guests > room.max_occupancy:
        rooms = await crud.list_rooms(db)
        return render(request, "booking.html", room=room, rooms=rooms,
                      checkin=str(checkin), checkout=str(checkout),
                      error=t("Esta habitación admite máximo {n} huéspedes.", n=room.max_occupancy))

    # Re-check availability right before creating (avoids double-booking).
    if not await crud.is_available(db, room.id, data.checkin, data.checkout):
        rooms = await crud.list_rooms(db)
        return render(request, "booking.html", room=room, rooms=rooms,
                      checkin=str(checkin), checkout=str(checkout),
                      error=t("Esas fechas ya no están disponibles para esta habitación."))

    try:
        booking = await crud.create_booking(db, room, data)
    except crud.DatesUnavailable:
        # The failed commit was rolled back, which expires session objects;
        # re-fetch the room so the template can read its attributes.
        rooms = await crud.list_rooms(db)
        room = await crud.get_room(db, data.room_id)
        return render(request, "booking.html", room=room, rooms=rooms,
                      checkin=str(checkin), checkout=str(checkout),
                      error=t("Esas fechas ya no están disponibles para esta habitación."))

    # Confirmation email (background, never blocks or breaks the booking).
    lang = i18n.get_lang(request)
    base = settings.base_url.rstrip("/")
    background.add_task(mailer.send_booking_confirmation, {
        "reference": booking.reference,
        "guest_name": booking.guest_name,
        "guest_email": booking.guest_email,
        "room_name": i18n.room_name(room, lang),
        "checkin": str(booking.checkin),
        "checkout": str(booking.checkout),
        "nights": booking.nights,
        "guests": booking.guests,
        "amount_cop": booking.amount_cop,
        "manage_url": f"{base}/reserva/{booking.reference}/resultado",
    }, lang)

    return RedirectResponse(f"/reserva/{booking.reference}/pago",
                            status_code=status.HTTP_303_SEE_OTHER)


@router.get("/reserva/{reference}/pago")
async def booking_payment(request: Request, reference: str,
                         db: AsyncSession = Depends(get_session)):
    booking = await crud.get_booking(db, reference)
    if not booking:
        raise HTTPException(404, "Reserva no encontrada.")
    room = await crud.get_room(db, booking.id_hab)
    if booking.estado == "confirmada":
        return RedirectResponse(f"/reserva/{reference}/resultado",
                                status_code=303)
    ctx = wompi.checkout_context(booking)
    wompi_ready = bool(settings.wompi_public_key and settings.wompi_integrity_secret)
    return render(request, "checkout.html", booking=booking, room=room,
                  wompi=ctx, wompi_ready=wompi_ready)


@router.get("/reserva/{reference}/resultado")
async def booking_result(request: Request, reference: str,
                        id: str = "", env: str = "",
                        db: AsyncSession = Depends(get_session)):
    booking = await crud.get_booking(db, reference)
    if not booking:
        raise HTTPException(404, "Reserva no encontrada.")
    room = await crud.get_room(db, booking.id_hab)
    return render(request, "result.html", booking=booking, room=room)


# --- Reviews ---------------------------------------------------------------
@router.get("/opiniones")
async def reviews_page(request: Request, db: AsyncSession = Depends(get_session)):
    reviews = await crud.list_reviews(db, approved_only=True, limit=60)
    avg, count = await crud.average_rating(db)
    rooms = await crud.list_rooms(db)
    return render(request, "reviews.html", reviews=reviews, rating_avg=avg,
                  rating_count=count, rooms=rooms)


@router.post("/opiniones")
async def reviews_submit(
    request: Request,
    author: str = Form(...),
    country: str = Form(""),
    rating: int = Form(...),
    title: str = Form(""),
    body: str = Form(...),
    room_id: str = Form(""),
    db: AsyncSession = Depends(get_session),
):
    await rate_limit(request, max_per_minute=6)
    t = t_for(request)
    try:
        data = ReviewCreate(author=author, country=country, rating=rating,
                            title=title, body=body, room_id=(room_id or None))
    except ValidationError:
        reviews = await crud.list_reviews(db, approved_only=True, limit=60)
        avg, count = await crud.average_rating(db)
        rooms = await crud.list_rooms(db)
        return render(request, "reviews.html", reviews=reviews, rating_avg=avg,
                      rating_count=count, rooms=rooms,
                      error=t("Revisa los datos de tu opinión (calificación 1-5 y comentario)."))
    await crud.create_review(db, data,
                             auto_approve=not settings.reviews_require_approval)
    msg = (t("¡Gracias! Tu opinión fue publicada.")
           if not settings.reviews_require_approval
           else t("¡Gracias! Tu opinión será publicada tras una breve revisión."))
    reviews = await crud.list_reviews(db, approved_only=True, limit=60)
    avg, count = await crud.average_rating(db)
    rooms = await crud.list_rooms(db)
    return render(request, "reviews.html", reviews=reviews, rating_avg=avg,
                  rating_count=count, rooms=rooms, success=msg)


# --- Contact / info --------------------------------------------------------
@router.get("/contacto")
async def contact(request: Request):
    return render(request, "contact.html")
