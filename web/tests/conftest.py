"""Test fixtures: an isolated in-memory SQLite database per test.

We exercise the *logical* booking layer (availability checks, hold expiry,
reference generation). The Postgres-only EXCLUDE constraint that physically
blocks double-booking can't run on SQLite, so those guarantees are covered by
the migrations in db/ and verified against Supabase, not here.
"""
from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Habitacion


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    # A single shared in-memory connection (StaticPool) so schema + data persist
    # across the test's queries.
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as s:
        s.add(Habitacion(
            id_hab="DBL-01", nom_hab="Doble Estándar", tipo="doble",
            precio_noche=320000, ca_max=2, activa=True,
        ))
        await s.commit()
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session, monkeypatch):
    """An httpx client wired to the FastAPI app over the in-memory `session`.

    Two things are overridden so requests stay isolated:
    - the get_session dependency yields the test session (not the configured DB);
    - the rate limiter (which opens its own SessionLocal, bypassing the override)
      is neutralised so it never touches a real database and never trips.
    """
    from app import crud
    from app.database import get_session
    from app.main import app

    async def _override_get_session():
        yield session

    async def _no_rate_limit(*_args, **_kwargs):
        return 1  # always under the limit

    app.dependency_overrides[get_session] = _override_get_session
    monkeypatch.setattr(crud, "hit_rate_limit", _no_rate_limit)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


def make_booking_data(**over):
    """A valid BookingCreate with sensible defaults; override per test."""
    from datetime import date, timedelta

    from app.schemas import BookingCreate

    today = date.today()
    defaults = dict(
        room_id="DBL-01",
        guest_name="Ana Pérez",
        guest_email="ana@example.com",
        guest_phone="3001234567",
        checkin=today + timedelta(days=10),
        checkout=today + timedelta(days=12),
        guests=2,
        notes="",
    )
    defaults.update(over)
    return BookingCreate(**defaults)
