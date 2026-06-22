-- ============================================================
-- Casa Gracia - migracion 002: ciclo de vida de los "holds"
-- Apartados de 20 min que vencen deben liberar la fecha tanto en
-- las consultas como en el constraint EXCLUDE. La app marca
-- 'pendiente' -> 'expirada'; este indice parcial hace ese barrido
-- barato a medida que crece la tabla. Idempotente.
-- ============================================================

-- Acelera:  UPDATE reserva SET estado='expirada'
--           WHERE estado='pendiente' AND hold_expira < now();
create index if not exists idx_reserva_pending_hold
  on reserva (hold_expira)
  where estado = 'pendiente';

-- Acelera la busqueda de reservas activas por habitacion+fechas
-- (disponibilidad / calendario) ignorando las ya canceladas/expiradas.
create index if not exists idx_reserva_activas
  on reserva (id_hab, fecha_in, fecha_fi)
  where estado in ('pendiente', 'confirmada');
