"""
Shared DB connection helper for the Supabase migration scripts.

Reads the connection string from (in order):
  1. env var  SUPABASE_DB_URL
  2. env var  DATABASE_URL
  3. ../web/.env  (DATABASE_URL=...)

Accepts SQLAlchemy-style URLs (postgresql+asyncpg://...) and plain ones;
strips the +asyncpg driver suffix for asyncpg.connect(). Forces SSL (Supabase
requires it).
"""
from __future__ import annotations
import os
import re
from pathlib import Path

import asyncpg


_KEYS = ("SUPABASE_DB_URL", "DATABASE_URL")


def _from_env_file() -> str | None:
    root = Path(__file__).resolve().parent.parent
    for envf in (root / ".env", root / "web" / ".env"):     # root first
        if not envf.exists():
            continue
        for line in envf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            for k in _KEYS:
                if line.startswith(k + "="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        return val
    return None


def get_dsn() -> str:
    dsn = os.environ.get("SUPABASE_DB_URL") or os.environ.get("DATABASE_URL") or _from_env_file()
    if not dsn:
        raise SystemExit(
            "No encontre la cadena de conexion. Define SUPABASE_DB_URL o pon "
            "DATABASE_URL=postgresql://... en web/.env")
    # asyncpg wants a plain postgresql:// URL (no +asyncpg, no sslmode kwarg here)
    dsn = re.sub(r"^postgresql\+asyncpg://", "postgresql://", dsn)
    dsn = re.sub(r"[?&]sslmode=\w+", "", dsn)
    return dsn


async def connect() -> asyncpg.Connection:
    # statement_cache_size=0 -> compatible with Supabase pooler (PgBouncer).
    return await asyncpg.connect(get_dsn(), ssl="require", timeout=30,
                                 statement_cache_size=0)
