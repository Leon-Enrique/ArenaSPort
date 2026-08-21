from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite:///./torneos.db"
    DEBUG: bool = True
    RUN_SEED: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # --- Auth (Discord OAuth2 + JWT propio) ---
    JWT_SECRET: str = "cambiar-en-produccion-nunca-usar-este-valor-en-serio"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # una semana

    DISCORD_CLIENT_ID: str = ""
    DISCORD_CLIENT_SECRET: str = ""
    DISCORD_REDIRECT_URI: str = "http://localhost:8000/api/auth/discord/callback"

    # A quién considerar organizador desde el arranque, por discord_id,
    # separados por coma — así el primer login ya tiene quien apruebe al
    # resto. Sin esto, nadie podría promoverse a organizador nunca.
    DISCORD_IDS_ORGANIZADORES_INICIALES: str = ""

    # --- Evidencia (R2 compatible con S3; local en desarrollo) ---
    ALMACENAMIENTO_LOCAL: bool = True  # False en producción, usa R2
    ALMACENAMIENTO_LOCAL_DIR: str = "./evidencias"
    R2_ENDPOINT_URL: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = ""
    R2_PUBLIC_BASE_URL: str = ""  # URL pública o de tu dominio propio delante del bucket

    @property
    def origenes_cors(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def discord_ids_organizadores_iniciales(self) -> set[str]:
        return {
            d.strip()
            for d in self.DISCORD_IDS_ORGANIZADORES_INICIALES.split(",")
            if d.strip()
        }


settings = Settings()
