-- migration_008_room_photos.sql
-- Reasigna las fotos de cada habitación para que CONCUERDEN con su descripción
-- (la primera foto es la miniatura de la tarjeta y la portada del detalle):
--   * Deluxe King -> cama King primero, luego vistas de piscina.
--   * Cuádruple Familiar -> las cuatro fotos con dos camas.
--   * Queen / Doble -> una sola cama; piscina/terraza/desayuno como apoyo.
-- Mismo mapeo que web/app/seed.py (fuente de verdad en dev). Idempotente.

UPDATE habitacion SET fotos =
  '/static/img/fb_hd/1440x1079_63fb62.jpg,/static/img/fb_hd/1440x1079_2bcde1.jpg,/static/img/fb_hd/1440x1079_29da8d.jpg,/static/img/fb_hd/1440x960_16ac93.jpg'
  WHERE id_hab = '101';

UPDATE habitacion SET fotos =
  '/static/img/fb_hd/1440x1050_e2286a.jpg,/static/img/fb_hd/1440x960_a779ff.jpg,/static/img/fb_hd/1440x1079_26253f.jpg,/static/img/fb_hd/1440x960_74bdd8.jpg'
  WHERE id_hab = '301';

UPDATE habitacion SET fotos =
  '/static/img/fb_hd/1440x1079_63fb62.jpg,/static/img/fb_hd/1440x1079_733ac2.jpg,/static/img/fb_hd/1440x1079_26253f.jpg,/static/img/fb_hd/1440x960_16ac93.jpg'
  WHERE id_hab = '201';

UPDATE habitacion SET fotos =
  '/static/img/fb_hd/1440x1050_e2286a.jpg,/static/img/fb_hd/1440x1079_2bcde1.jpg,/static/img/fb_hd/1440x962_4da7d3.jpg,/static/img/fb_hd/1440x1079_29da8d.jpg'
  WHERE id_hab = '102';

UPDATE habitacion SET fotos =
  '/static/img/fb_hd/1440x960_3be3bb.jpg,/static/img/fb_hd/1440x1079_29da8d.jpg,/static/img/fb_hd/1440x1079_733ac2.jpg,/static/img/fb_hd/1440x960_a779ff.jpg'
  WHERE id_hab = '202';

UPDATE habitacion SET fotos =
  '/static/img/fb_hd/1440x1079_a3f60a.jpg,/static/img/fb_hd/1440x1079_68b3ee.jpg,/static/img/fb_hd/1440x960_887c04.jpg,/static/img/fb_hd/1440x962_6a9a46.jpg'
  WHERE id_hab = '203';
