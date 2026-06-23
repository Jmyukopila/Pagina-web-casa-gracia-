-- ============================================================
-- Casa Gracia - migracion 006: integracion con Lobby PMS (channel manager)
-- Sincronizacion bidireccional: importamos reservas de OTAs desde Lobby como
-- filas 'externa' que BLOQUEAN la fecha (logica y fisicamente), y marcamos las
-- reservas con su codigo de Lobby. Transaccional e idempotente.
--
-- Cambios:
--   1. Columnas de sync en reserva (origen, lobby_code, lobby_synced_en).
--   2. Nuevo estado 'externa' (reserva importada de un OTA via Lobby).
--   3. El estado 'externa' participa en el CHECK, en el EXCLUDE anti-overbooking
--      y en el indice de reservas activas, igual que 'pendiente'/'confirmada'.
-- ============================================================

-- ---- 1. Columnas de sincronizacion ---------------------------
alter table reserva add column if not exists origen        varchar(10) not null default 'directo';
alter table reserva add column if not exists lobby_code     varchar(40);
alter table reserva add column if not exists lobby_synced_en timestamptz;

create unique index if not exists idx_reserva_lobby_code
  on reserva (lobby_code) where lobby_code is not null;
create index if not exists idx_reserva_origen on reserva (origen);

-- ---- 2. CHECK de estado: anadir 'externa' --------------------
do $$
declare c text;
begin
  select conname into c
    from pg_constraint
   where conrelid = 'reserva'::regclass and contype = 'c'
     and pg_get_constraintdef(oid) ilike '%estado%';
  if c is not null then
    execute format('alter table reserva drop constraint %I', c);
  end if;
end $$;

alter table reserva add constraint reserva_estado_check
  check (estado in ('pendiente','confirmada','cancelada','expirada','externa'));

-- ---- 3. EXCLUDE anti-overbooking: incluir 'externa' ----------
-- Descubre el nombre del constraint EXCLUDE (auto-generado en 001) y lo recrea
-- con un nombre estable incluyendo el estado 'externa' en el WHERE.
do $$
declare c text;
begin
  select conname into c
    from pg_constraint
   where conrelid = 'reserva'::regclass and contype = 'x';
  if c is not null then
    execute format('alter table reserva drop constraint %I', c);
  end if;
end $$;

alter table reserva add constraint reserva_no_overlap
  exclude using gist (
    id_hab with =,
    daterange(fecha_in, fecha_fi, '[)') with &&
  ) where (estado in ('pendiente','confirmada','externa'));

-- ---- 4. Indice de reservas activas: incluir 'externa' --------
drop index if exists idx_reserva_activas;
create index idx_reserva_activas
  on reserva (id_hab, fecha_in, fecha_fi)
  where estado in ('pendiente','confirmada','externa');
