"""SEO endpoints: robots.txt and a dynamic sitemap.xml.

The sitemap lists the public, indexable pages plus one URL per active room,
so search engines discover every room detail page. Booking-flow URLs
(/reserva/...) are intentionally excluded (they're per-reservation, noindex).
"""
from __future__ import annotations

from datetime import date
from xml.sax.saxutils import escape

from fastapi import APIRouter, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from .. import crud
from ..config import settings
from ..database import get_session

router = APIRouter()

# Static public pages and their relative priority for the sitemap.
_STATIC_PAGES = [
    ("/", "1.0", "weekly"),
    ("/habitaciones", "0.9", "weekly"),
    ("/reservar", "0.8", "weekly"),
    ("/opiniones", "0.6", "monthly"),
    ("/contacto", "0.5", "monthly"),
]


def _base(request: Request) -> str:
    # Prefer the configured BASE_URL; fall back to the request's own origin so
    # the sitemap is correct even before BASE_URL is set in the environment.
    configured = settings.base_url.rstrip("/")
    if configured and not configured.startswith("http://localhost"):
        return configured
    return str(request.base_url).rstrip("/")


@router.get("/robots.txt", include_in_schema=False)
async def robots_txt(request: Request) -> Response:
    base = _base(request)
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /reserva/\n"
        "Disallow: /api/\n"
        f"\nSitemap: {base}/sitemap.xml\n"
    )
    return Response(body, media_type="text/plain")


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml(request: Request,
                      db: AsyncSession = Depends(get_session)) -> Response:
    base = _base(request)
    today = date.today().isoformat()
    urls: list[str] = []

    for path, priority, freq in _STATIC_PAGES:
        urls.append(
            f"  <url><loc>{escape(base + path)}</loc>"
            f"<lastmod>{today}</lastmod>"
            f"<changefreq>{freq}</changefreq>"
            f"<priority>{priority}</priority></url>"
        )

    try:
        rooms = await crud.list_rooms(db)
    except Exception:
        rooms = []
    for room in rooms:
        loc = escape(f"{base}/habitaciones/{room.slug}")
        urls.append(
            f"  <url><loc>{loc}</loc>"
            f"<lastmod>{today}</lastmod>"
            f"<changefreq>weekly</changefreq>"
            f"<priority>0.7</priority></url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    return Response(xml, media_type="application/xml")
