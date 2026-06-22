-- ============================================================
-- Casa Gracia - migracion 004: escalaciones del chatbot
-- Cuando el asistente deriva una conversacion a recepcion
-- (escalate_to_human), guardamos el caso para no perderlo:
-- motivo, ultimo mensaje del cliente y un extracto del contexto.
-- Recepcion lo revisa y marca 'atendido'. Idempotente.
-- ============================================================
create table if not exists escalacion (
  id         serial primary key,
  motivo     text         not null,                -- por que se escalo
  mensaje    text,                                 -- ultimo mensaje del cliente
  idioma     varchar(2)   not null default 'es',   -- es | en
  contexto   text,                                 -- extracto de la conversacion
  contacto   varchar(160),                         -- contacto si el cliente lo dio
  atendido   boolean      not null default false,  -- recepcion ya lo gestiono
  creado_en  timestamptz  not null default now()
);

-- Bandeja de pendientes: lo no atendido, primero lo mas reciente.
create index if not exists idx_escalacion_pendientes
  on escalacion (creado_en desc)
  where atendido = false;
