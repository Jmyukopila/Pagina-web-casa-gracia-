<div align="center">

# Casa Gracia Hotel Boutique — Canal Directo

**Motor de reserva directa** para Casa Gracia (Manga, Cartagena de Indias).
Web propia + chatbot embebido para captar reservas sin pagar comisiones de OTAs.

[![Sitio web](https://img.shields.io/badge/Sitio_web-casa--gracia.vercel.app-B88850?style=for-the-badge)](https://casa-gracia.vercel.app)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-CA2C2C)
![Supabase](https://img.shields.io/badge/Supabase-Postgres-3FCF8E?logo=supabase&logoColor=white)
![Vercel](https://img.shields.io/badge/Vercel-serverless-000000?logo=vercel&logoColor=white)

</div>

## En producción

| | Enlace |
|---|---|
| **Sitio web** | https://casa-gracia.vercel.app |
| **Panel de administración** | https://casa-gracia.vercel.app/admin |

> El panel pide el `ADMIN_TOKEN` (configurado en Vercel) para entrar. No lo
> compartas ni lo subas al repositorio.

## Características

- **Reserva directa** con flujo completo: búsqueda, detalle de habitación,
  disponibilidad en vivo y confirmación.
- **Anti doble-reserva** a nivel de base de datos (constraint `EXCLUDE` de
  Postgres) + **apartados de 20 min** que vencen y liberan la fecha
  automáticamente (barrido por la app y por `pg_cron`).
- **Chatbot embebido** bilingüe: pre-filtro de FAQ sin tokens, modelo LLM con
  *failover* entre proveedores y herramientas que consultan precios y
  disponibilidad reales; escala a recepción y guarda el caso.
- **Bilingüe ES/EN** con detección de idioma y cambio por cookie.
- **Correo de confirmación** de reserva (SMTP opcional; no falla si no está
  configurado).
- **SEO**: canonical, OpenGraph/Twitter, JSON-LD `Hotel`, `sitemap.xml` y
  `robots.txt` dinámicos.
- **Imágenes optimizadas**: pipeline WebP con variantes móviles del hero.
- **Pulido visual**: hero con carrusel, scroll-reveal, micro-interacciones
  (todo respeta `prefers-reduced-motion`).
- **Panel de administración** protegido por token: reservas, aprobación de
  opiniones y cola de escalaciones del chatbot.
- **Rate-limiting distribuido** respaldado en Postgres (funciona entre
  instancias *serverless*).
- **Tests** con pytest sobre la lógica de reservas, apartados, escalaciones y
  rate-limit.

## Tecnología

FastAPI (async) · SQLAlchemy 2.0 (asyncpg) · Supabase Postgres · Jinja2 SSR ·
JS/CSS sin frameworks · LLMs vía endpoints compatibles con OpenAI · Vercel.

## Estructura

```
Canal directo casa gracia/
├── web/                         App de reserva directa (lo principal)
│   ├── app/
│   │   ├── main.py              Entrypoint FastAPI (middlewares, errores)
│   │   ├── config.py            Settings desde entorno (.env)
│   │   ├── models.py · crud.py  ORM + capa de acceso a datos
│   │   ├── mailer.py            Correo de confirmación (SMTP opcional)
│   │   ├── routers/             pages · api · chat · admin · seo · payments
│   │   ├── chat/                Chatbot: engine, tools, prefilter, knowledge
│   │   ├── templates/           Jinja2 (index, rooms, booking, admin…)
│   │   └── static/              CSS, JS e imágenes (con WebP)
│   ├── tools/optimize_images.py Genera WebP + variantes móviles
│   ├── tests/                   pytest (reservas, holds, rate-limit…)
│   ├── api/index.py             Adaptador serverless (Vercel)
│   └── vercel.json
├── db/                          Migraciones SQL + utilidades (apply.py)
├── data/ · scraper/ · assets/   Toolkit para recolectar contenido (ver abajo)
└── PLAN.md                      Estrategia y hoja de ruta del canal directo
```

## Puesta en marcha (local)

Por defecto usa **SQLite** y se autosiembra, así que arranca sin configurar nada.

```powershell
cd web
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ENVIRONMENT = "development"     # crea y siembra la BD SQLite local
uvicorn app.main:app --reload
```

Abre http://127.0.0.1:8000

Para apuntar a Postgres/Supabase u otras opciones, copia `.env.example` a `.env`
y rellena los valores (`DATABASE_URL`, claves del chatbot, SMTP, `ADMIN_TOKEN`…).

### Tests

```powershell
cd web
pip install -r requirements-dev.txt
pytest -q
```

### Optimizar imágenes

Tras añadir o reemplazar fotos en `app/static/img/`:

```powershell
cd web
python tools/optimize_images.py     # genera los .webp (idempotente)
```

## Despliegue (Vercel)

La app vive en `web/` y se despliega desde ahí (el `rootDirectory` del proyecto
es la raíz del repo):

```powershell
cd web
vercel --prod
```

Las variables de entorno se gestionan en el panel de Vercel (`vercel env ls`).
Las migraciones de base de datos se aplican con `python db/apply.py <archivo>.sql`.

## Panel de administración

`/admin` — protegido por `ADMIN_TOKEN`. Permite:

- Ver reservas recientes y su estado.
- Aprobar o rechazar opiniones pendientes.
- Trabajar la cola de **escalaciones del chatbot** (con el contacto del huésped).

También expone una API JSON de solo lectura en `/api/admin/*`.

---

## Toolkit de recolección de contenido (opcional)

`scraper/` reúne el contenido del hotel (info, fotos, precios) **de tus propias
cuentas** para alimentar el canal directo.

> **Importante:** Booking.com y Airbnb bloquean el scraping automatizado y sus
> términos lo prohíben. Úsalo solo como operador del hotel sobre tu propio
> contenido. Para algo continuo, prefiere las vías oficiales: export del
> **Extranet** de Booking, **API de Airbnb** para hosts profesionales, o un
> **Channel Manager** (Cloudbeds, SiteMinder, Hostaway, Lobby PMS…).

```powershell
cd scraper
py -m pip install -r requirements.txt
py -m playwright install chromium

py scrape_booking.py      # abre un Chromium real; resuelve el CAPTCHA una vez
py scrape_airbnb.py       # las 4 habitaciones de Airbnb
py download_images.py     # descarga las fotos a ../assets/
py merge_to_profile.py    # consolida todo en data/casa-gracia-scraped.json
```

Edita `scraper/config.py` para fechas, moneda o `HEADLESS = True`. La primera
corrida usa un perfil persistente (`scraper/.pw-profile`): inicia sesión una vez
en tu Extranet / cuenta de host y queda recordado.

Ver **PLAN.md** para la hoja de ruta completa del canal directo.
