from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Todas las rutas de este archivo se anclan acá, al paquete, y NO al
# directorio desde el que se lanzó el proceso.
#
# Con `env_file=".env"` a secas, arrancar uvicorn desde la raíz del repo (o
# desde cualquier otro lado) no encuentra el archivo y la app cae a los
# valores por defecto de abajo sin decir nada. Los dos que duelen:
#
#   - DATABASE_URL -> crea y usa una base SQLite vacía distinta. Pasó de
#     verdad durante el desarrollo, no es hipotético.
#   - ALMACENAMIENTO_LOCAL_DIR -> las evidencias ya subidas quedan en la
#     carpeta vieja y `/evidencias/archivo/{clave}` empieza a devolver 404;
#     la captura que respalda una disputa desaparece de la nada.
RAIZ_BACKEND = Path(__file__).resolve().parents[2]


def anclar_a_raiz(ruta: str) -> str:
    """Convierte una ruta relativa en absoluta respecto de la raíz del
    backend. Las rutas ya absolutas se devuelven intactas."""
    if not ruta:
        return ruta
    p = Path(ruta)
    return ruta if p.is_absolute() else str((RAIZ_BACKEND / p).resolve())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=RAIZ_BACKEND / ".env", extra="ignore")

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

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalizar_url(cls, value: str) -> str:
        """Deja la URL en la forma que espera SQLAlchemy, y ancla SQLite.

        Los proveedores gestionados (Railway, Render, Heroku) inyectan la URL
        de Postgres en su forma canónica, `postgresql://...`, y algunos
        todavía usan el `postgres://` viejo. Ninguna de las dos le dice a
        SQLAlchemy qué driver usar, así que toma el por defecto —psycopg2—
        que este proyecto NO tiene instalado: usa psycopg 3. El resultado es
        que la app no arranca, con un error de driver que no menciona la
        variable de entorno y manda a buscar el problema a otro lado.

        Normalizarlo acá evita eso, y evita también tener que acordarse de
        editar a mano una variable que el proveedor sobrescribe en cada
        redeploy.

        Lo de SQLite es otra cosa: `sqlite:///./torneos.db` es relativo al
        directorio de trabajo, así que el mismo valor apunta a archivos
        distintos según desde dónde se lance el proceso.
        """
        for viejo in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
            if value.startswith(viejo):
                return "postgresql+psycopg://" + value[len(viejo):]

        prefijo = "sqlite:///"
        if not value.startswith(prefijo):
            return value
        ruta = value[len(prefijo):]
        if not ruta or Path(ruta).is_absolute():
            return value
        return f"{prefijo}{Path(anclar_a_raiz(ruta)).as_posix()}"

    @field_validator("ALMACENAMIENTO_LOCAL_DIR")
    @classmethod
    def _anclar_directorio_evidencias(cls, value: str) -> str:
        return anclar_a_raiz(value)

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
