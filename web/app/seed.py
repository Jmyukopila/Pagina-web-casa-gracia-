"""
Seed the Supabase tables (habitacion + opinion) with Casa Gracia's data and
the HD photos pulled from Facebook. Idempotent: only inserts when empty.
Prices are per night in COP (integers).
"""
from __future__ import annotations

from sqlalchemy import func, select

from .database import SessionLocal
from .models import Habitacion, Opinion

P = "/static/img/fb_hd/"   # HD photos folder
AMEN = ("Aire acondicionado,Baño privado,WiFi gratis,TV satelital,"
        "Minibar,Escritorio,Secador,Caja fuerte")

ROOMS = [
    dict(id_hab="101", nom_hab="Habitación Comfort Queen", tipo="Comfort Double",
         cama="1 cama Queen", tam_m2=15, ca_max=2, vista="Interior", precio_noche=280000,
         descripcion="Acogedora habitación recién renovada con cama Queen, aire "
                     "acondicionado y baño privado. Ideal para parejas que buscan "
                     "tranquilidad a pasos del Castillo de San Felipe.",
         # 1 cama Queen + baño privado, piscina y desayuno como apoyo.
         fotos=P+"1440x1079_63fb62.jpg,"+P+"1440x1079_2bcde1.jpg,"
               +P+"1440x1079_29da8d.jpg,"+P+"1440x960_16ac93.jpg"),
    dict(id_hab="301", nom_hab="Habitación Comfort Queen Superior", tipo="Comfort Double",
         cama="1 cama Queen", tam_m2=15, ca_max=2, vista="Exterior", precio_noche=300000,
         descripcion="Habitación Queen en planta alta, luminosa y silenciosa, con "
                     "todas las comodidades modernas y acceso a la piscina.",
         # 1 cama Queen luminosa con sala de estar; piscina y terraza.
         fotos=P+"1440x1050_e2286a.jpg,"+P+"1440x960_a779ff.jpg,"
               +P+"1440x1079_26253f.jpg,"+P+"1440x960_74bdd8.jpg"),
    dict(id_hab="201", nom_hab="Habitación Doble Estándar", tipo="Standard Double",
         cama="1 cama Doble", tam_m2=16, ca_max=2, vista="Interior", precio_noche=300000,
         descripcion="Cómoda habitación doble con cama matrimonial, perfecta para "
                     "una escapada por Cartagena.",
         # 1 cama matrimonial; piscina y terraza de apoyo.
         fotos=P+"1440x1079_63fb62.jpg,"+P+"1440x1079_733ac2.jpg,"
               +P+"1440x1079_26253f.jpg,"+P+"1440x960_16ac93.jpg"),
    dict(id_hab="102", nom_hab="Habitación Doble Amplia", tipo="Large Double",
         cama="1 cama Queen", tam_m2=18, ca_max=2, vista="Interior", precio_noche=340000,
         descripcion="Versión más amplia de nuestra habitación doble, con espacio "
                     "extra de estar y zona de trabajo.",
         # 1 cama Queen con sala de estar (sofá) + escritorio de trabajo.
         fotos=P+"1440x1050_e2286a.jpg,"+P+"1440x1079_2bcde1.jpg,"
               +P+"1440x962_4da7d3.jpg,"+P+"1440x1079_29da8d.jpg"),
    dict(id_hab="202", nom_hab="Habitación Deluxe King · Vista Piscina", tipo="Deluxe Double",
         cama="1 cama King", tam_m2=20, ca_max=2, vista="Vista a la piscina", precio_noche=420000,
         descripcion="Nuestra habitación insignia: cama King, vista directa a la "
                     "piscina y una atmósfera serena para una estadía especial.",
         # 1 cama King primero, luego las vistas de la piscina.
         fotos=P+"1440x960_3be3bb.jpg,"+P+"1440x1079_29da8d.jpg,"
               +P+"1440x1079_733ac2.jpg,"+P+"1440x960_a779ff.jpg"),
    dict(id_hab="203", nom_hab="Habitación Cuádruple Familiar", tipo="Quadruple",
         cama="2 camas dobles", tam_m2=21, ca_max=4, vista="Interior", precio_noche=460000,
         descripcion="Espaciosa habitación con dos camas dobles para familias o "
                     "grupos de hasta 4 personas, sin renunciar a la comodidad.",
         # 2 camas dobles en las cuatro fotos.
         fotos=P+"1440x1079_a3f60a.jpg,"+P+"1440x1079_68b3ee.jpg,"
               +P+"1440x960_887c04.jpg,"+P+"1440x962_6a9a46.jpg"),
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
