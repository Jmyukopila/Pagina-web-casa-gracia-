-- migration_010_escalacion_canal.sql
-- Añade el canal preferido por el huésped ("whatsapp" / "correo") a las
-- escalaciones del chatbot, para que recepción sepa por dónde responderle.
-- Idempotente.

ALTER TABLE escalacion ADD COLUMN IF NOT EXISTS canal varchar(20);
