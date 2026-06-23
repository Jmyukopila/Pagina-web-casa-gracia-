"""
Casa Gracia Hotel Boutique -- web app entrypoint.

Run (dev):   uvicorn app.main:app --reload
Run (prod):  gunicorn app.main:app -c gunicorn_conf.py   (see Dockerfile)
"""
from __future__ import annotations

import logging
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure correct Content-Type for modern image formats (Windows registries
# often lack these, so StaticFiles would mislabel them as text/plain).
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database import init_db
from .deps import render
from .routers import admin, api, chat, internal, pages, payments, seo

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("casagracia")
BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Dev convenience only: create the SQLite schema + seed. In production
    # (Supabase) the DB is managed by migrations and is already seeded, so we
    # skip this -- important for serverless cold starts (Vercel).
    if not settings.is_prod:
        try:
            await init_db()
            from .seed import seed
            await seed()
        except Exception:  # never let startup crash the whole service
            log.exception("Startup DB init/seed failed (continuing).")
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/api/docs" if not settings.is_prod else None,
    redoc_url=None,
)

# gzip responses (faster pages, less bandwidth under load).
app.add_middleware(GZipMiddleware, minimum_size=600)

# Static assets.
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Routers.
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(chat.router)
app.include_router(payments.router)
app.include_router(seo.router)
app.include_router(admin.router)
app.include_router(admin.ui_router)
app.include_router(internal.router)


@app.get("/health", include_in_schema=False)
async def health():
    # Fast liveness probe (no DB) -- safe for load balancers / uptime checks.
    return {"status": "ok"}


@app.get("/health/db", include_in_schema=False)
async def health_db():
    # Readiness probe: verifies the database is reachable.
    from sqlalchemy import text

    from .database import SessionLocal
    try:
        async with SessionLocal() as s:
            await s.execute(text("select 1"))
        return {"status": "ok", "db": "up"}
    except Exception:
        log.exception("DB health check failed")
        return JSONResponse({"status": "error", "db": "down"}, status_code=503)


# Language selection: ?lang=es|en sets a cookie; otherwise use the cookie.
@app.middleware("http")
async def language(request: Request, call_next):
    q = request.query_params.get("lang")
    chosen = q if q in ("es", "en") else None
    request.state.lang = chosen or request.cookies.get("lang") or "es"
    if request.state.lang not in ("es", "en"):
        request.state.lang = "es"
    response = await call_next(request)
    if chosen:
        response.set_cookie("lang", chosen, max_age=31536000, samesite="lax")
    return response


# Content-Security-Policy. Inline styles/scripts are pervasive in the templates
# (inline config, onclick handlers, JSON-LD), so 'unsafe-inline' is allowed for
# now; the real wins are locking down sources, base-uri, framing and form posts
# (Wompi checkout is a GET form to checkout.wompi.co). Shipped as Report-Only
# first so violations surface in the console without breaking the site; flip the
# header name to "Content-Security-Policy" to enforce once verified.
CSP_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data:",
    "connect-src 'self'",
    "form-action 'self' https://checkout.wompi.co",
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "object-src 'none'",
])
CSP_HEADER = "Content-Security-Policy-Report-Only"


# Lightweight security headers on every response.
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(CSP_HEADER, CSP_POLICY)
    return response


# --- Friendly error pages (no stack traces leak to users) ------------------
def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


@app.exception_handler(StarletteHTTPException)
async def http_exc_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and _wants_html(request):
        return render(request, "error.html", code=404,
                      message="No encontramos la página que buscas.")
    if _wants_html(request):
        return render(request, "error.html", code=exc.status_code,
                      message=str(exc.detail))
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": "Datos inválidos.", "errors": exc.errors()},
                        status_code=422)


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    if _wants_html(request):
        return render(request, "error.html", code=500,
                      message="Tuvimos un problema procesando tu solicitud. "
                              "Intenta de nuevo en unos momentos.")
    return JSONResponse({"detail": "Internal server error"}, status_code=500)
