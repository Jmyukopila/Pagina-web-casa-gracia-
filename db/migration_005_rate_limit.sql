-- ============================================================
-- Casa Gracia - migracion 005: rate limiting distribuido
-- En Vercel hay varias instancias; un contador en memoria por
-- instancia no limita de verdad. Esta tabla es un contador de
-- ventana fija compartido (clave = ip+tier, ventana = minuto epoch).
-- La app hace UPSERT +1 y compara con el limite. Idempotente.
-- ============================================================
create table if not exists rate_limit (
  clave    varchar(80) not null,
  ventana  integer     not null,          -- minuto epoch (floor(epoch/60))
  conteo   integer     not null default 0,
  primary key (clave, ventana)
);

-- Para purgar ventanas viejas de forma barata.
create index if not exists idx_rate_limit_ventana on rate_limit (ventana);

-- Limpieza automatica cada 15 min: borra ventanas con mas de ~5 min.
-- (pg_cron ya esta habilitado; ver migracion 003.)
do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_cron') then
    perform cron.schedule(
      'casagracia-rate-limit-cleanup',
      '*/15 * * * *',
      $cron$ delete from rate_limit where ventana < (extract(epoch from now())/60)::int - 5 $cron$
    );
  end if;
end $$;
