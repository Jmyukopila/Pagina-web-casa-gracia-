# Casa Gracia — Sitio web + motor de reservas

Sitio del hotel con **reservas, disponibilidad por calendario, habitaciones,
opiniones y pagos con Wompi**, construido para aguantar tráfico y desplegarse
sin sorpresas con **Docker**.

Stack: **FastAPI (async) + Gunicorn/Uvicorn**, **SQLAlchemy 2.0 async**,
**Jinja2** (SSR, bueno para SEO), **Nginx** (caché/gzip/rate-limit/balanceo),
**Postgres** (lo gestionas tú). Sin paso de build de JS.

## Estructura
```
web/
├── app/
│   ├── main.py            # FastAPI: rutas, errores, salud, seguridad
│   ├── config.py          # settings por variables de entorno (.env)
│   ├── database.py        # engine/sesión async (DATABASE_URL)
│   ├── models.py          # Room, Booking, Review
│   ├── schemas.py         # validación (Pydantic)
│   ├── crud.py            # consultas + lógica de disponibilidad
│   ├── seed.py            # carga habitaciones reales de Casa Gracia
│   ├── deps.py            # plantillas, contexto global, rate limit
│   ├── payments/wompi.py  # firma de integridad + verificación de webhook
│   ├── routers/           # pages.py (SSR), api.py (JSON), payments.py
│   ├── templates/         # Jinja2 (estética de marca)
│   └── static/            # css, js, imágenes, logo
├── Dockerfile            # imagen de producción (no-root, healthcheck)
├── docker-compose.yml    # nginx + app (escalable) + postgres
├── nginx/nginx.conf      # proxy: caché, gzip, rate-limit, balanceo
├── gunicorn_conf.py      # workers async, reciclaje, timeouts
├── requirements.txt
└── .env.example          # copia a .env y completa
```

## Desarrollo local (rápido, con SQLite)
```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (o: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn app.main:app --reload     # http://127.0.0.1:8000
```
Arranca con SQLite y **siembra las habitaciones automáticamente**. Docs API en
`/api/docs` (solo fuera de producción).

## Producción con Docker
```bash
cp .env.example .env              # completa Wompi, dominio, DB...
docker compose up -d --build
docker compose up -d --scale web=3   # 3 réplicas balanceadas por Nginx
```
Nginx queda en el puerto 80 (añade 443/TLS con tus certificados).

## Base de datos (la gestionas tú)
- Por defecto usa el Postgres incluido en compose.
- Para usar el tuyo: borra el servicio `db` del compose y pon tu cadena en
  `DATABASE_URL` (formato `postgresql+asyncpg://usuario:clave@host:5432/bd`).
- `create_all` solo crea tablas que falten; para cambios de esquema usa
  migraciones (p. ej. Alembic) contra tu base.

## Pagos (Wompi)
1. Crea cuenta en Wompi y usa primero **sandbox**.
2. Pon en `.env`: `WOMPI_PUBLIC_KEY`, `WOMPI_INTEGRITY_SECRET`, `WOMPI_EVENTS_SECRET`.
3. Configura el **webhook/eventos** de Wompi apuntando a
   `https://TU-DOMINIO/api/wompi/webhook`.
4. Flujo: reserva → se aparta 20 min (estado *pending*) → checkout Wompi →
   el webhook (verificado por firma) confirma o cancela la reserva. **Nunca**
   confiamos solo en el redirect del navegador.

> El servidor no toca datos de tarjeta: Wompi gestiona el pago.

## Cómo aguanta tráfico / evita caídas
- App **async** + varios workers de Gunicorn + **réplicas** horizontales.
- **Nginx**: gzip, caché de estáticos, **rate-limit** por IP y balanceo.
- Pool de conexiones con `pool_pre_ping` (resiste conexiones caídas).
- Manejadores globales de error → páginas 404/500 amables, sin filtrar stack.
- `/health` para readiness/liveness; healthcheck en el contenedor.
- Re-chequeo de disponibilidad antes de crear la reserva (evita doble-booking).

> Nota: el rate-limit por defecto es en memoria (por instancia). Con varias
> réplicas, respáldalo en **Redis** para un contador compartido.

## Endpoints principales
| Ruta | Qué hace |
|---|---|
| `/` | Inicio (hero, habitaciones, opiniones, ubicación) |
| `/habitaciones` · `/habitaciones/{slug}` | Listado y detalle con disponibilidad |
| `/reservar` | Formulario de reserva → pago |
| `/reserva/{ref}/pago` · `/resultado` | Checkout Wompi y resultado |
| `/opiniones` | Reseñas + formulario (moderado) |
| `/contacto` | Info y mapa |
| `GET /api/availability` | Disponibilidad (JSON) |
| `GET /api/rooms/{id}/calendar` | Rangos ocupados (JSON) |
| `POST /api/wompi/webhook` | Confirmación de pago (firmado) |
| `POST /api/reviews/{id}/approve` | Aprobar reseña (header `X-Admin-Token`) |

## Probado
Arranca limpio; todas las páginas devuelven 200, el 404 funciona, el flujo de
reserva crea el *hold* y **bloquea las fechas** (verificado: solape→no
disponible, sin solape→disponible), las reseñas se envían y las firmas de Wompi
(integridad + webhook) se validan y rechazan manipulaciones.
