# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Direct-booking engine for Casa Gracia Hotel Boutique (Cartagena). A FastAPI
(async) web app + embedded bilingual chatbot that captures reservations without
OTA commissions. The real application lives entirely in `web/`. The top-level
`scraper/`, `data/`, and `assets/` are a separate, optional content-collection
toolkit (see README) and are not part of the deployed app.

## Commands

All app commands run from `web/` (PowerShell shown; the venv lives in `web/.venv`):

```powershell
cd web
.venv\Scripts\Activate.ps1
pip install -r requirements.txt              # runtime deps
$env:ENVIRONMENT = "development"             # creates + seeds local SQLite
uvicorn app.main:app --reload                # dev server on :8000

pip install -r requirements-dev.txt          # test deps (pytest, asyncio)
pytest -q                                     # full suite
pytest tests/test_booking.py -q               # one file
pytest tests/test_booking.py::test_name -q    # one test

python tools/optimize_images.py               # regenerate .webp after adding photos
```

Database migrations (Postgres/Supabase only) run from the **repo root**, one
file per transaction (auto-rollback on failure):

```powershell
python db/apply.py migration_00X.sql
```

Deploy: `cd web && vercel --prod`. Env vars are managed in the Vercel dashboard
(`vercel env ls`).

## Architecture

**Two environments, one codebase, switched by `ENVIRONMENT`/`DATABASE_URL`:**

- **Dev** = local SQLite (`sqlite+aiosqlite`), auto-created and auto-seeded on
  startup via `lifespan` in `app/main.py` → `init_db()` + `seed()`. Runs with
  zero configuration.
- **Prod** = Supabase Postgres. The lifespan hook **skips** schema/seed
  (`settings.is_prod`) because the schema is owned by the SQL migrations in
  `db/`. The async engine uses `NullPool` + `statement_cache_size=0` because
  Supabase's PgBouncer pooler breaks prepared-statement caching
  (`app/database.py`).

**Serverless:** `web/api/index.py` is the Vercel entrypoint — it just imports
the ASGI `app`. `web/vercel.json` routes everything to it. Because Vercel runs
several instances, anything stateful must live in Postgres, not process memory.

**Spanish DB schema with English template aliases.** Models
(`app/models.py`) map the Supabase tables `cliente`, `habitacion`, `reserva`,
`opinion` (plus `rate_limit`, `escalacion`) with Spanish column names. Each
model exposes English `@property` aliases (`name`, `price_cop`, `checkin`,
`guest_name`…) so Jinja templates read in English. When adding fields, keep this
alias pattern so templates keep working.

**Booking concurrency (the core invariant):** holds are `reserva` rows with
`estado='pendiente'` and a 20-minute `hold_expira`. Availability queries
(`crud.py:_active_filter`) treat a pending row as blocking only while its hold
is unexpired. `release_expired_holds()` flips lapsed holds to `'expirada'`, run
opportunistically by the app (`create_booking` calls it first) and by `pg_cron`
(`migration_003_pgcron.sql`). The hard guarantee against double-booking is a
Postgres `EXCLUDE` constraint — a lost race raises `IntegrityError`, caught and
re-raised as `crud.DatesUnavailable` → routers return HTTP 409. **This
constraint cannot run on SQLite**, so dev and the pytest suite verify only the
logical layer; the physical guarantee is verified against Supabase.

**Chatbot (`app/chat/`), stateless on memory:** the browser sends prior turns
with each `POST /api/chat`. The router (`routers/chat.py`) tries, in order:
1. `prefilter.quick_answer` — fixed FAQ/greeting replies, **0 tokens**, rules in
   `app/chat/data/quick_replies.json`, bilingual via keyword `detect_lang`.
2. `engine.generate_reply` — OpenAI-compatible LLM with a **failover chain**
   (`settings.llm_chain()`: provider + fallbacks, drops any without an API key)
   and a tool loop (`app/chat/tools.py`) that reads live prices/availability from
   the DB and can `escalate_to_human` (writes an `escalacion` row for reception).
Always returns a friendly bilingual fallback if everything fails. Some models
leak tool calls as text (`<function=...>`); `engine._clean_leaked_tools` parses
and strips those.

**Rate limiting (`deps.py`):** distributed fixed-window counter in the
`rate_limit` Postgres table (atomic upsert in `crud.hit_rate_limit`), so it
holds across serverless instances. **Fails open** to a per-instance in-process
deque if the DB is unreachable — the site never breaks because of it. Different
tiers (reads vs. booking vs. chat) get separate counters keyed by `ip:limit`.

**i18n (ES/EN):** a `language` middleware in `main.py` resolves `?lang=` →
cookie → default `es`, storing it on `request.state.lang`. Always render via
`deps.render()`, which injects `t`, `money`, room-name helpers, and the
`asset_v` cache-buster. The `money` helper shows COP in Spanish and converts to
USD in English.

**Routers** (`app/routers/`, all included in `main.py`): `pages` (SSR Jinja
site), `api` (booking/availability/reviews JSON), `chat`, `payments` (Wompi,
deferred/sandbox), `seo` (sitemap/robots/JSON-LD), `admin` (token-protected).

**Admin auth:** `/admin` (HTML) and `/api/admin/*` (JSON) share `ADMIN_TOKEN`.
Pass `?token=` once → stored in an httpOnly cookie. The default placeholder
token is always rejected; comparison uses `secrets.compare_digest`.

## Config

All settings come from env via `app/config.py` (`pydantic-settings`), loading
`../.env` then `web/.env`. Nothing secret is hard-coded. Key knobs: `DATABASE_URL`,
`ENVIRONMENT`, `ADMIN_TOKEN`, `BASE_URL` (needed for correct canonical/OG/sitemap
URLs in prod), LLM provider keys (`gemini`/`groq`/`openrouter`), SMTP
(`mail_enabled` is false until `smtp_host`+`mail_from` are set — bookings never
fail when mail is unconfigured), and Wompi keys.

## Conventions

- Fully async throughout (SQLAlchemy 2.0 asyncpg, async route handlers). Add DB
  access through `crud.py`, not inline in routers.
- Use timezone-aware UTC via `crud._utcnow()`; never `datetime.utcnow()`.
- Presentation uses plain icon glyphs / SVGs, **not emoji**.
- New stateful behavior must be Postgres-backed (serverless = no shared memory).
