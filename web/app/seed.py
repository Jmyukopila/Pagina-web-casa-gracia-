"""
Seed the Supabase tables (habitacion + opinion) with Casa Gracia's data and
the HD photos pulled from Facebook. Idempotent: only inserts when empty.
Prices are per night in COP (integers).
"""
from __future__ import annotations

from sqlalchemy import func, select

from .database import SessionLocal
from .models import Habitacion, Opinion

P = "/static/img/fb_hd/"    # HD amenity photos (piscina, terraza, desayuno)
R = "/static/img/rooms/"    # foto real de cada habitación (room-<id>.jpg)
AMEN = ("Aire acondicionado,Baño privado,WiFi gratis,TV satelital,"
        "Minibar,Escritorio,Secador,Caja fuerte")

# Apoyo: fotos reales de zonas comunes para completar la galería de cada
# habitación (la PRIMERA foto siempre es la foto real de la habitación).
POOL = P + "1440x1079_29da8d.jpg"
PLUNGE = P + "1440x1079_733ac2.jpg"
TERRACE = P + "1440x1079_26253f.jpg"
BREAKFAST = P + "1440x960_16ac93.jpg"

# Catálogo real (8 habitaciones). Precios PROPUESTOS (anclados a los anteriores)
# pendientes de confirmar por el hotel. m² estimados.
ROOMS = [
    dict(id_hab="101", nom_hab="Habitación Doble Queen", tipo="Doble Queen",
         cama="1 cama Queen", tam_m2=16, ca_max=2, vista="Interior", precio_noche=300000,
         descripcion="Habitación con cama Queen, aire acondicionado y baño privado. "
                     "Ideal para parejas que buscan comodidad a pasos del Castillo "
                     "de San Felipe.",
         fotos=R+"room-101.jpg,"+POOL+","+TERRACE),
    dict(id_hab="102", nom_hab="Habitación Cuádruple", tipo="Cuádruple",
         cama="2 camas dobles", tam_m2=22, ca_max=4, vista="Interior", precio_noche=460000,
         descripcion="Amplia habitación con dos camas dobles, perfecta para familias "
                     "o grupos de hasta 4 personas, sin renunciar al confort.",
         fotos=R+"room-102.jpg,"+POOL+","+TERRACE),
    dict(id_hab="103", nom_hab="Habitación Cuádruple", tipo="Cuádruple",
         cama="2 camas dobles", tam_m2=22, ca_max=4, vista="Exterior", precio_noche=460000,
         descripcion="Habitación luminosa con dos camas dobles y ventana exterior, "
                     "ideal para familias o grupos de hasta 4 personas.",
         fotos=R+"room-103.jpg,"+PLUNGE+","+TERRACE),
    dict(id_hab="201", nom_hab="Habitación Doble", tipo="Doble",
         cama="1 cama Doble", tam_m2=15, ca_max=2, vista="Interior", precio_noche=280000,
         descripcion="Cómoda habitación con cama doble y baño privado, perfecta para "
                     "una escapada por Cartagena.",
         fotos=R+"room-201.jpg,"+POOL+","+BREAKFAST),
    dict(id_hab="202", nom_hab="Habitación Doble King", tipo="Doble King",
         cama="1 cama King", tam_m2=20, ca_max=2, vista="Exterior", precio_noche=420000,
         descripcion="Espaciosa habitación con cama King y ventana exterior, luminosa "
                     "y serena para una estadía especial.",
         fotos=R+"room-202.jpg,"+POOL+","+PLUNGE),
    dict(id_hab="203", nom_hab="Habitación Triple Queen", tipo="Triple",
         cama="1 cama Queen + sofá cama", tam_m2=20, ca_max=3, vista="Exterior", precio_noche=380000,
         descripcion="Habitación para hasta 3 personas con cama Queen y sofá cama, "
                     "vista exterior y mucha luz natural.",
         fotos=R+"room-203.jpg,"+POOL+","+TERRACE),
    dict(id_hab="301", nom_hab="Habitación Doble Queen Superior", tipo="Doble Queen",
         cama="1 cama Queen", tam_m2=16, ca_max=2, vista="Interior", precio_noche=300000,
         descripcion="Habitación Queen en planta alta, con baño privado y vanity, "
                     "tranquila y luminosa.",
         fotos=R+"room-301.jpg,"+PLUNGE+","+BREAKFAST),
    dict(id_hab="302", nom_hab="Habitación Doble King Superior", tipo="Doble King",
         cama="1 cama King", tam_m2=20, ca_max=2, vista="Exterior", precio_noche=420000,
         descripcion="Habitación King en planta alta, espaciosa y luminosa, con "
                     "todas las comodidades modernas.",
         fotos=R+"room-302.jpg,"+POOL+","+TERRACE),
]

OPINIONS = [
    dict(autor="María F.", pais="Colombia", rating=5, aprobado=True,
         titulo="Hermoso refugio en Manga",
         cuerpo="El hotel es precioso y muy tranquilo. La piscina y la atención del "
                "personal son lo mejor. Volveremos."),
    dict(autor="James W.", pais="United States", rating=5, aprobado=True,
         titulo="Beautiful boutique stay",
         cuerpo="Spotless rooms, great location near the castle, and the team was "
                "incredibly helpful. Highly recommended."),
    dict(autor="Laura G.", pais="Argentina", rating=4, aprobado=True,
         titulo="Muy lindo y bien ubicado",
         cuerpo="Excelente relación precio-calidad. Habitaciones cómodas y desayuno "
                "rico. A pasos de todo."),
]


async def seed() -> None:
    async with SessionLocal() as db:
        n_rooms = (await db.execute(select(func.count(Habitacion.id_hab)))).scalar_one()
        if n_rooms == 0:
            db.add_all([Habitacion(amenidades=AMEN, activa=True, **r) for r in ROOMS])
            await db.commit()
            print(f"[seed] habitaciones insertadas: {len(ROOMS)}")

        n_op = (await db.execute(select(func.count(Opinion.id)))).scalar_one()
        if n_op == 0:
            db.add_all([Opinion(**o) for o in OPINIONS])
            await db.commit()
            print(f"[seed] opiniones insertadas: {len(OPINIONS)}")
