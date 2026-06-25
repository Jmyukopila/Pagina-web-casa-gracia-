-- migration_009_rooms_real.sql
-- Catálogo REAL de 8 habitaciones con sus fotos reales (room-<id>.jpg).
-- Actualiza las 6 habitaciones existentes (101,102,201,202,203,301) e inserta
-- las nuevas 103 y 302. Idempotente (UPSERT por id_hab). Mismo mapeo que
-- web/app/seed.py. Precios PROPUESTOS — confirmar con el hotel antes de aplicar.
--
-- Fotos: la PRIMERA es la foto real de la habitación; el resto son zonas
-- comunes reales (piscina/terraza/desayuno) para completar la galería.

INSERT INTO habitacion
  (id_hab, nom_hab, tipo, descripcion, cama, tam_m2, vista, precio_noche, ca_max, fotos, amenidades, activa)
VALUES
  ('101', 'Habitación Doble Queen', 'Doble Queen',
   'Habitación con cama Queen, aire acondicionado y baño privado. Ideal para parejas que buscan comodidad a pasos del Castillo de San Felipe.',
   '1 cama Queen', 16, 'Interior', 300000, 2,
   '/static/img/rooms/room-101.jpg,/static/img/fb_hd/1440x1079_29da8d.jpg,/static/img/fb_hd/1440x1079_26253f.jpg',
   'Aire acondicionado,Baño privado,WiFi gratis,TV satelital,Minibar,Escritorio,Secador,Caja fuerte', true),

  ('102', 'Habitación Cuádruple', 'Cuádruple',
   'Amplia habitación con dos camas dobles, perfecta para familias o grupos de hasta 4 personas, sin renunciar al confort.',
   '2 camas dobles', 22, 'Interior', 460000, 4,
   '/static/img/rooms/room-102.jpg,/static/img/fb_hd/1440x1079_29da8d.jpg,/static/img/fb_hd/1440x1079_26253f.jpg',
   'Aire acondicionado,Baño privado,WiFi gratis,TV satelital,Minibar,Escritorio,Secador,Caja fuerte', true),

  ('103', 'Habitación Cuádruple', 'Cuádruple',
   'Habitación luminosa con dos camas dobles y ventana exterior, ideal para familias o grupos de hasta 4 personas.',
   '2 camas dobles', 22, 'Exterior', 460000, 4,
   '/static/img/rooms/room-103.jpg,/static/img/fb_hd/1440x1079_733ac2.jpg,/static/img/fb_hd/1440x1079_26253f.jpg',
   'Aire acondicionado,Baño privado,WiFi gratis,TV satelital,Minibar,Escritorio,Secador,Caja fuerte', true),

  ('201', 'Habitación Doble', 'Doble',
   'Cómoda habitación con cama doble y baño privado, perfecta para una escapada por Cartagena.',
   '1 cama Doble', 15, 'Interior', 280000, 2,
   '/static/img/rooms/room-201.jpg,/static/img/fb_hd/1440x1079_29da8d.jpg,/static/img/fb_hd/1440x960_16ac93.jpg',
   'Aire acondicionado,Baño privado,WiFi gratis,TV satelital,Minibar,Escritorio,Secador,Caja fuerte', true),

  ('202', 'Habitación Doble King', 'Doble King',
   'Espaciosa habitación con cama King y ventana exterior, luminosa y serena para una estadía especial.',
   '1 cama King', 20, 'Exterior', 420000, 2,
   '/static/img/rooms/room-202.jpg,/static/img/fb_hd/1440x1079_29da8d.jpg,/static/img/fb_hd/1440x1079_733ac2.jpg',
   'Aire acondicionado,Baño privado,WiFi gratis,TV satelital,Minibar,Escritorio,Secador,Caja fuerte', true),

  ('203', 'Habitación Triple Queen', 'Triple',
   'Habitación para hasta 3 personas con cama Queen y sofá cama, vista exterior y mucha luz natural.',
   '1 cama Queen + sofá cama', 20, 'Exterior', 380000, 3,
   '/static/img/rooms/room-203.jpg,/static/img/fb_hd/1440x1079_29da8d.jpg,/static/img/fb_hd/1440x1079_26253f.jpg',
   'Aire acondicionado,Baño privado,WiFi gratis,TV satelital,Minibar,Escritorio,Secador,Caja fuerte', true),

  ('301', 'Habitación Doble Queen Superior', 'Doble Queen',
   'Habitación Queen en planta alta, con baño privado y vanity, tranquila y luminosa.',
   '1 cama Queen', 16, 'Interior', 300000, 2,
   '/static/img/rooms/room-301.jpg,/static/img/fb_hd/1440x1079_733ac2.jpg,/static/img/fb_hd/1440x960_16ac93.jpg',
   'Aire acondicionado,Baño privado,WiFi gratis,TV satelital,Minibar,Escritorio,Secador,Caja fuerte', true),

  ('302', 'Habitación Doble King Superior', 'Doble King',
   'Habitación King en planta alta, espaciosa y luminosa, con todas las comodidades modernas.',
   '1 cama King', 20, 'Exterior', 420000, 2,
   '/static/img/rooms/room-302.jpg,/static/img/fb_hd/1440x1079_29da8d.jpg,/static/img/fb_hd/1440x1079_26253f.jpg',
   'Aire acondicionado,Baño privado,WiFi gratis,TV satelital,Minibar,Escritorio,Secador,Caja fuerte', true)

ON CONFLICT (id_hab) DO UPDATE SET
  nom_hab      = EXCLUDED.nom_hab,
  tipo         = EXCLUDED.tipo,
  descripcion  = EXCLUDED.descripcion,
  cama         = EXCLUDED.cama,
  tam_m2       = EXCLUDED.tam_m2,
  vista        = EXCLUDED.vista,
  precio_noche = EXCLUDED.precio_noche,
  ca_max       = EXCLUDED.ca_max,
  fotos        = EXCLUDED.fotos,
  amenidades   = EXCLUDED.amenidades,
  activa       = EXCLUDED.activa;
