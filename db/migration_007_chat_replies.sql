-- ============================================================
-- Casa Gracia - migracion 007: respuestas en vivo del chat
-- Permite que recepcion responda desde /admin y que la respuesta
-- aparezca en el chat del huesped (mientras tenga la pestana abierta).
--   * escalacion.thread_id  : hilo (UUID del navegador) al que responder.
--   * respuesta_chat        : cola de respuestas del agente por hilo; el
--                             widget hace polling por thread_id e id (cursor).
-- Idempotente.
-- ============================================================
alter table escalacion add column if not exists thread_id varchar(40);

create index if not exists idx_escalacion_thread
  on escalacion (thread_id);

create table if not exists respuesta_chat (
  id         bigserial    primary key,            -- cursor monotonico de polling
  thread_id  varchar(40)  not null,               -- hilo del navegador (UUID)
  texto      text         not null,               -- respuesta escrita por recepcion
  creado_en  timestamptz  not null default now()
);

-- Polling: respuestas de un hilo con id mayor al ultimo visto.
create index if not exists idx_respuesta_thread
  on respuesta_chat (thread_id, id);
