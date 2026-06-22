-- ============================================================
-- Casa Gracia - migracion 001: esquema corregido
-- Tablas vacias (0 filas) -> recreacion limpia. Transaccional.
-- ============================================================
create extension if not exists btree_gist;

drop table if exists reserva   cascade;
drop table if exists opinion   cascade;
drop table if exists habitacion cascade;
drop table if exists cliente   cascade;

-- ---- clientes -------------------------------------------------
create table cliente (
  id        serial primary key,
  nombre    varchar(120) not null,
  correo    varchar(160) not null,
  telefono  varchar(20),                         -- texto, NO int
  creado_en timestamptz  not null default now()
);
create index idx_cliente_correo on cliente (correo);

-- ---- habitaciones --------------------------------------------
create table habitacion (
  id_hab       varchar(16) primary key,          -- "101", "202"
  nom_hab      varchar(120) not null,
  tipo         varchar(60),
  descripcion  text,
  cama         varchar(80),
  tam_m2       smallint,
  vista        varchar(80),
  precio_noche integer     not null check (precio_noche >= 0),  -- COP entero, NO varchar
  ca_max       smallint    not null default 2,
  fotos        text,                             -- rutas separadas por coma
  amenidades   text,                             -- separadas por coma
  activa       boolean     not null default true -- en servicio (no "ocupada")
);

-- ---- reservas -------------------------------------------------
create table reserva (
  id_res      serial primary key,
  referencia  varchar(40) unique not null,       -- CG-260620-XXXX
  id_cliente  integer     not null references cliente(id)     on delete restrict,
  id_hab      varchar(16) not null references habitacion(id_hab) on delete restrict,
  fecha_in    date        not null,
  fecha_fi    date        not null,
  n_adultos   smallint    not null default 1 check (n_adultos >= 1),
  n_ninos     smallint    not null default 0 check (n_ninos  >= 0),  -- sin ñ
  valor       integer     not null check (valor >= 0),               -- COP entero, NO float
  moneda      varchar(3)  not null default 'COP',
  estado      varchar(20) not null default 'pendiente'
              check (estado in ('pendiente','confirmada','cancelada','expirada')),
  wompi_tx_id varchar(80),
  notas       varchar(500),
  hold_expira timestamptz,                        -- vence el apartado de 20 min
  creado_en   timestamptz not null default now(),
  check (fecha_fi > fecha_in),
  -- impide doble-reserva fisicamente: misma habitacion + fechas solapadas
  exclude using gist (
    id_hab with =,
    daterange(fecha_in, fecha_fi, '[)') with &&
  ) where (estado in ('pendiente','confirmada'))
);
create index idx_reserva_hab_fechas on reserva (id_hab, fecha_in, fecha_fi);
create index idx_reserva_cliente    on reserva (id_cliente);
create index idx_reserva_estado     on reserva (estado);

-- ---- opiniones (la web tiene seccion de comentarios) ----------
create table opinion (
  id        serial primary key,
  id_hab    varchar(16) references habitacion(id_hab) on delete set null,
  autor     varchar(120) not null,
  pais      varchar(80),
  rating    smallint not null check (rating between 1 and 5),
  titulo    varchar(160),
  cuerpo    text not null,
  aprobado  boolean not null default false,
  creado_en timestamptz not null default now()
);
create index idx_opinion_aprobado on opinion (aprobado);

-- ---- Seguridad: RLS activado (deny por defecto al anon key) ---
-- La app del backend usa la conexion directa de Postgres y NO se ve afectada.
-- Si luego quieres lectura publica (ej. habitaciones), agregamos policies.
alter table cliente    enable row level security;
alter table habitacion enable row level security;
alter table reserva    enable row level security;
alter table opinion    enable row level security;
