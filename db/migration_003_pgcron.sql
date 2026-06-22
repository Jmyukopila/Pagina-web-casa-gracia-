-- ============================================================
-- Casa Gracia - migracion 003 (OPCIONAL): auto-expiracion de holds
-- Programa un job pg_cron que cada 5 min marca como 'expirada' las
-- reservas 'pendiente' cuyo apartado de 20 min ya vencio. Esto libera
-- la fecha incluso si la web no recibe trafico.
--
-- La app YA expira holds de forma oportunista en cada intento de
-- reserva (crud.release_expired_holds), asi que este job es solo
-- "housekeeping" de respaldo. Requiere privilegios para pg_cron
-- (en Supabase, el rol postgres los tiene). Idempotente por nombre.
--
-- Aplicado en produccion el 2026-06-21 (jobid=1).
-- ============================================================
create extension if not exists pg_cron;

select cron.schedule(
  'casagracia-expire-holds',
  '*/5 * * * *',
  $$update reserva set estado = 'expirada'
     where estado = 'pendiente'
       and hold_expira is not null
       and hold_expira < now()$$
);
