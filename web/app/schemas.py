"""Pydantic request/response schemas (validation + the public API contract)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

# Longest stay we accept in a single booking (guards typos / abuse).
MAX_NIGHTS = 30


def _not_in_past(v: date) -> date:
    if v < date.today():
        raise ValueError("checkin cannot be in the past")
    return v


def _check_range(checkout: date, checkin: date | None) -> date:
    if checkin:
        if checkout <= checkin:
            raise ValueError("checkout must be after checkin")
        if (checkout - checkin).days > MAX_NIGHTS:
            raise ValueError(f"stay cannot exceed {MAX_NIGHTS} nights")
    return checkout


class AvailabilityQuery(BaseModel):
    room_id: str
    checkin: date
    checkout: date

    @field_validator("checkin")
    @classmethod
    def _checkin_not_past(cls, v: date) -> date:
        return _not_in_past(v)

    @field_validator("checkout")
    @classmethod
    def _order(cls, v: date, info):
        return _check_range(v, info.data.get("checkin"))


class AvailabilityResult(BaseModel):
    room_id: str
    available: bool
    nights: int
    price_cop: int
    total_cop: int


class BookingCreate(BaseModel):
    room_id: str
    guest_name: str = Field(min_length=2, max_length=120)
    guest_email: EmailStr
    guest_phone: str = Field(default="", max_length=40)
    checkin: date
    checkout: date
    guests: int = Field(ge=1, le=10)
    notes: str = Field(default="", max_length=500)

    @field_validator("checkin")
    @classmethod
    def _checkin_not_past(cls, v: date) -> date:
        return _not_in_past(v)

    @field_validator("checkout")
    @classmethod
    def _order(cls, v: date, info):
        return _check_range(v, info.data.get("checkin"))


class BookingOut(BaseModel):
    reference: str
    room_id: str
    checkin: date
    checkout: date
    nights: int
    guests: int
    amount_cop: int
    status: str

    model_config = {"from_attributes": True}


class ReviewCreate(BaseModel):
    room_id: str | None = None
    author: str = Field(min_length=2, max_length=120)
    country: str = Field(default="", max_length=80)
    rating: int = Field(ge=1, le=5)
    title: str = Field(default="", max_length=160)
    body: str = Field(min_length=4, max_length=2000)


# --- Chatbot ---------------------------------------------------------------
class ChatTurn(BaseModel):
    role: str
    content: str = Field(default="", max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
