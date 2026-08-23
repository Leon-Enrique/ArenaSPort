"""Equipos, jugadores e inscripciones.

La identidad del jugador es JSON (cada juego pide lo suyo) + una clave derivada
que permite el índice único de elegibilidad.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, DateTimeUTC
from app.domain.enums import EstadoInscripcion


class Equipo(Base):
    """Un equipo, que puede vivir más allá de un torneo.

    Es la entidad PERMANENTE; el plantel de un torneo puntual es la
    `Inscripcion` con sus `Jugador`. Es la misma separación que hacen
    Battlefy (Team vs Tournament Roster) y Toornament: el equipo se conserva,
    el plantel se arma de nuevo en cada edición.

    `propietario_usuario_id` es quién lo administra. Nulo a propósito en dos
    casos que siguen existiendo: los equipos creados por una inscripción
    anónima (la plataforma deja anotarse sin cuenta, y esa es una ventaja
    para torneos de base que no queremos perder) y los 53 equipos que ya
    estaban antes de que esto existiera. Sin dueño, el equipo funciona igual
    dentro de su torneo — lo único que no puede es reutilizarse en el
    siguiente, porque nadie puede demostrar que le pertenece.
    """

    __tablename__ = "equipos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), index=True)
    tag: Mapped[str | None] = mapped_column(String(12))
    logo_url: Mapped[str | None] = mapped_column(String(500))

    propietario_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), index=True
    )

    contacto_nombre: Mapped[str | None] = mapped_column(String(120))
    contacto_whatsapp: Mapped[str | None] = mapped_column(String(40))
    contacto_discord: Mapped[str | None] = mapped_column(String(80))

    esta_activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )

    inscripciones: Mapped[list["Inscripcion"]] = relationship(back_populates="equipo")


class Inscripcion(Base):
    __tablename__ = "inscripciones"
    __table_args__ = (
        UniqueConstraint("edicion_id", "equipo_id", name="uq_inscripcion_equipo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    edicion_id: Mapped[int] = mapped_column(ForeignKey("ediciones.id"), index=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipos.id"), index=True)

    estado: Mapped[EstadoInscripcion] = mapped_column(
        Enum(EstadoInscripcion, native_enum=False, length=40),
        default=EstadoInscripcion.PENDIENTE,
        index=True,
    )
    motivo_rechazo: Mapped[str | None] = mapped_column(Text)
    seed: Mapped[int | None] = mapped_column(Integer)  # siembra para el sorteo

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )
    revisada_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    equipo: Mapped["Equipo"] = relationship(back_populates="inscripciones")
    jugadores: Mapped[list["Jugador"]] = relationship(
        back_populates="inscripcion",
        cascade="all, delete-orphan",
        order_by="Jugador.orden",
    )

    @property
    def titulares(self) -> list["Jugador"]:
        return [j for j in self.jugadores if not j.es_suplente]

    @property
    def suplentes(self) -> list["Jugador"]:
        return [j for j in self.jugadores if j.es_suplente]


class Jugador(Base):
    """Un jugador dentro de una inscripción concreta.

    El mismo humano puede aparecer en varias ediciones; lo que impide que esté en
    dos equipos de LA MISMA edición es el índice único sobre clave_identidad.
    """

    __tablename__ = "jugadores"
    __table_args__ = (
        # Único PARCIAL: la regla es "un jugador en un solo equipo por
        # edición", pero solo cuenta mientras su inscripción esté viva.
        #
        # Antes era un UNIQUE común y eso dejaba un agujero: al rechazar un
        # equipo, sus cinco jugadores seguían ocupando cupo y no podían
        # entrar en ningún otro, para siempre. El chequeo de la aplicación
        # solo no alcanza — sin restricción en la base, dos inscripciones
        # simultáneas del mismo jugador pasan las dos.
        #
        # La condición va sobre `ocupa_cupo` y no sobre el estado de la
        # inscripción porque un índice no puede mirar otra tabla.
        Index(
            "uq_jugador_elegibilidad",
            "edicion_id",
            "clave_identidad",
            unique=True,
            sqlite_where=text("ocupa_cupo = 1"),
            postgresql_where=text("ocupa_cupo"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inscripcion_id: Mapped[int] = mapped_column(
        ForeignKey("inscripciones.id"), index=True
    )
    # Desnormalizado a propósito: hace posible el constraint de elegibilidad.
    edicion_id: Mapped[int] = mapped_column(ForeignKey("ediciones.id"), index=True)

    # {"nick": "Lyon", "id_juego": "123456789", "server": "2251"}
    identidad: Mapped[dict] = mapped_column(JSON)
    # Derivada de los campos clave del juego: "123456789|2251"
    clave_identidad: Mapped[str] = mapped_column(String(200), index=True)

    orden: Mapped[int] = mapped_column(Integer, default=0)
    es_suplente: Mapped[bool] = mapped_column(Boolean, default=False)
    es_capitan: Mapped[bool] = mapped_column(Boolean, default=False)

    # Si este jugador bloquea el cupo de elegibilidad de la edición.
    #
    # Es un derivado del estado de la inscripción (ver
    # ESTADOS_QUE_OCUPAN_CUPO): existe desnormalizado acá solo porque el
    # índice único parcial de arriba no puede consultar otra tabla. La
    # sincronización vive en `sincronizar_cupo_de_elegibilidad`
    # (app/api/routes/inscripciones.py) y se llama desde los únicos tres
    # lugares que cambian el estado de una inscripción.
    ocupa_cupo: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    # Vincula a este jugador con una cuenta de Discord real. Nulo mientras
    # el equipo se inscribe sin que nadie haya iniciado sesión todavía — se
    # completa cuando el capitán se loguea por primera vez y confirma que es
    # él. Sin esto, reportar/confirmar resultados no tiene con qué verificar
    # que quien llama es realmente el capitán de este equipo.
    # Mismo largo que `Usuario.discord_id`: acá se guarda exactamente el
    # mismo valor, incluido el sintético "local:<email>" de las cuentas
    # locales. Si esta columna fuera más corta, vincular a un jugador con
    # una cuenta local de email largo fallaría solo en Postgres.
    discord_id: Mapped[str | None] = mapped_column(String(320), index=True)

    inscripcion: Mapped["Inscripcion"] = relationship(back_populates="jugadores")

    @property
    def nick(self) -> str:
        return self.identidad.get("nick", "?")
