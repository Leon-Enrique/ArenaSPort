"""Usuarios autenticados vía Discord OAuth2.

No hay contraseñas: la identidad la garantiza Discord, nosotros solo
guardamos el vínculo. `es_organizador` es una bandera global simple — no
hay todavía un concepto de "organizador de ESTE torneo en particular";
cuando haga falta, se agrega una tabla de membresía por torneo sin romper
esto.

`puede_gestionar_organizadores` es un segundo nivel, separado a propósito:
sin esto, cualquier organizador promovido tendría el mismo poder que quien
lo promovió — incluido sacarle el rol a quien lo puso ahí. Solo quien tiene
este permiso puede tocar la lista de organizadores; el resto opera el
torneo (aprobar inscripciones, resolver disputas, sortear) sin poder tocar
quién más es organizador.
"""

from datetime import datetime

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base, DateTimeUTC


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    discord_username: Mapped[str] = mapped_column(String(120))
    discord_avatar_url: Mapped[str | None] = mapped_column(String(500))

    # Login alternativo por email/contraseña (ver app/api/routes/auth.py,
    # sub-router /auth/local). Las cuentas creadas así guardan un
    # discord_id sintético ("local:<email>") para no romper el UNIQUE NOT
    # NULL de arriba — no hay usuario de Discord real detrás.
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))

    es_organizador: Mapped[bool] = mapped_column(Boolean, default=False)
    puede_gestionar_organizadores: Mapped[bool] = mapped_column(Boolean, default=False)
    esta_activo: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )
    ultimo_login_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )
