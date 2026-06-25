"""
Application settings, loaded from environment variables (.env).
Nothing secret is hard-coded -- safe to commit. Provide real values via .env
or your deploy platform's secret manager.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load the project-root .env (where the Supabase DATABASE_URL lives) and,
    # if present, a local web/.env that overrides it.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    # --- App -------------------------------------------------------------
    app_name: str = "Casa Gracia Hotel Boutique"
    base_url: str = "http://localhost:8000"
    secret_key: str = "change-me-in-production"      # session signing
    environment: str = "development"                  # development | production
    debug: bool = False

    # --- Database (YOU manage this) --------------------------------------
    # Dev default = local SQLite. Prod = set DATABASE_URL to your Postgres, e.g.
    # postgresql+asyncpg://user:pass@host:5432/casagracia
    database_url: str = "sqlite+aiosqlite:///./casagracia.db"

    # --- Hotel info (shown across the site) ------------------------------
    hotel_name: str = "Casa Gracia Hotel Boutique"
    hotel_address: str = "Carrera 17 #26-133, Manga, Cartagena de Indias, Colombia"
    hotel_lat: float = 10.4188
    hotel_lng: float = -75.5412
    hotel_phone: str = "+57 300 000 0000"            # TODO: real number
    hotel_whatsapp: str = "573000000000"             # digits only, for wa.me
    hotel_email: str = "reservas@casagraciacartagena.com"
    hotel_instagram: str = "https://www.instagram.com/casagracia.ctg/"
    hotel_facebook: str = "https://www.facebook.com/61570407230142"

    # --- Currency / pricing ---------------------------------------------
    currency: str = "COP"
    usd_to_cop: int = 4000                            # display helper only

    # --- Wompi (payments) ------------------------------------------------
    # Get these from your Wompi dashboard (sandbox first).
    wompi_public_key: str = ""
    wompi_integrity_secret: str = ""
    wompi_events_secret: str = ""
    wompi_base_checkout: str = "https://checkout.wompi.co/p/"
    wompi_api_base: str = "https://sandbox.wompi.co/v1"   # prod: https://production.wompi.co/v1

    # --- Chatbot (LLM) ---------------------------------------------------
    # Free providers exposed through OpenAI-compatible endpoints, tried in
    # order (primary first, then fallbacks) so a saturated quota fails over.
    # Secrets (the *_api_key) come from env / the deploy platform, never code.
    llm_provider: str = "gemini"
    llm_fallbacks: str = "groq,openrouter"
    llm_history_limit: int = 8            # max prior turns the server keeps
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-oss-120b:free"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1"

    # --- Email (booking confirmations) -----------------------------------
    # SMTP is optional: if unset, the app simply skips sending (logs a notice)
    # so bookings never fail because mail isn't configured yet. Works with any
    # provider (Gmail app-password, Resend SMTP, Mailgun, SendGrid, ...).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True                              # STARTTLS on port 587
    mail_from: str = ""                               # e.g. "Casa Gracia <reservas@...>"

    @property
    def mail_enabled(self) -> bool:
        return bool(self.smtp_host and self.mail_from)

    # --- Reviews ---------------------------------------------------------
    reviews_require_approval: bool = True
    admin_token: str = "change-me-admin-token"        # session secret / JSON API
    admin_user: str = "admin"                         # dashboard login user
    admin_password: str = ""                           # dashboard login pass (env)

    # --- Rate limiting ---------------------------------------------------
    rate_limit_per_minute: int = 60

    # --- Lobby PMS (channel manager) -------------------------------------
    # Two-way sync: pull OTA reservations + rates from Lobby, push direct
    # bookings to Lobby. Everything is gated on lobby_enabled (= a token is set),
    # so with no account the site behaves exactly as before. The token + IP
    # policy come from Lobby (Configuraciones > Usuarios, Permisos y API).
    lobby_base_url: str = "https://api.lobbypms.com/api/v2"
    lobby_api_token: str = ""
    # Maps local id_hab -> Lobby room/product id, as JSON, e.g.
    # {"DBL-01": "123", "KNG-02": "124"}. Read both ways via lobby_room_pairs().
    lobby_room_map: str = ""
    # Shared secret the Vercel Cron (and admin button) send to POST
    # /internal/lobby/sync so only authorized callers can trigger a sync.
    lobby_sync_secret: str = ""
    # How many days ahead to pull/sync reservations and rates (Lobby caps
    # occupancy stats at 90 days).
    lobby_sync_window_days: int = 90

    @property
    def lobby_enabled(self) -> bool:
        return bool(self.lobby_api_token)

    def lobby_room_pairs(self) -> dict[str, str]:
        """Parsed {id_hab: lobby_room_id} map; empty if unset/invalid."""
        import json
        if not self.lobby_room_map.strip():
            return {}
        try:
            data = json.loads(self.lobby_room_map)
        except json.JSONDecodeError:
            return {}
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}

    @property
    def is_prod(self) -> bool:
        return self.environment.lower() == "production"

    # --- LLM provider chain (OpenAI-compatible endpoints) ----------------
    def _llm_endpoint(self, provider: str) -> tuple[str, str, str] | None:
        """(base_url, api_key, model) for a provider, or None if unknown."""
        p = provider.lower().strip()
        if p == "groq":
            return ("https://api.groq.com/openai/v1", self.groq_api_key, self.groq_model)
        if p == "gemini":
            return ("https://generativelanguage.googleapis.com/v1beta/openai/",
                    self.gemini_api_key, self.gemini_model)
        if p == "openrouter":
            return ("https://openrouter.ai/api/v1", self.openrouter_api_key,
                    self.openrouter_model)
        if p == "ollama":
            return (self.ollama_base_url, "ollama", self.ollama_model)
        return None

    def llm_chain(self) -> list[tuple[str, str, str, str]]:
        """(provider, base_url, api_key, model) in order of use; drops any
        provider without a key (except ollama, which is local)."""
        order = [self.llm_provider] + [p for p in self.llm_fallbacks.split(",") if p.strip()]
        chain, seen = [], set()
        for prov in order:
            prov = prov.lower().strip()
            if not prov or prov in seen:
                continue
            seen.add(prov)
            ep = self._llm_endpoint(prov)
            if ep is None:
                continue
            base_url, key, model = ep
            if prov != "ollama" and not key:
                continue
            chain.append((prov, base_url, key, model))
        return chain

    @property
    def chat_enabled(self) -> bool:
        return bool(self.llm_chain())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
