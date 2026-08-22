"""Catálogo de juegos y estructura de torneos.

El juego es CONFIGURACIÓN, no código: agregar Free Fire o CODM es insertar una fila.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, DateTimeUTC
from app.domain.enums import EstadoEdicion, FormatoFase, ModeloCompetencia


class Juego(Base):
    __tablename__ = "juegos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    modelo_competencia_default: Mapped[ModeloCompetencia] = mapped_column(
        Enum(ModeloCompetencia, native_enum=False, length=40)
    )
    titulares_requeridos: Mapped[int] = mapped_column(Integer)
    suplentes_maximos: Mapped[int] = mapped_column(Integer)

    # Qué datos se le piden a cada jugador y cuáles forman la clave única.
    # {"campos": [{"nombre": "nick", "etiqueta": "Nick", "requerido": true}, ...],
    #  "clave_unica": ["id_juego", "server"]}
    campos_identidad: Mapped[dict] = mapped_column(JSON)

    esta_activo: Mapped[bool] = mapped_column(Boolean, default=True)

    def campos_requeridos(self) -> list[str]:
        return [
            c["nombre"] for c in self.campos_identidad["campos"] if c.get("requerido")
        ]

    def campos_clave(self) -> list[str]:
        return self.campos_identidad["clave_unica"]


class Torneo(Base):
    __tablename__ = "torneos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )

    ediciones: Mapped[list["Edicion"]] = relationship(back_populates="torneo")


class Edicion(Base):
    __tablename__ = "ediciones"
    __table_args__ = (UniqueConstraint("torneo_id", "numero", name="uq_edicion_numero"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    torneo_id: Mapped[int] = mapped_column(ForeignKey("torneos.id"), index=True)
    juego_id: Mapped[int] = mapped_column(ForeignKey("juegos.id"), index=True)

    numero: Mapped[int] = mapped_column(Integer)  # 1ra edición, 2da...
    nombre: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    estado: Mapped[EstadoEdicion] = mapped_column(
        Enum(EstadoEdicion, native_enum=False, length=40),
        default=EstadoEdicion.BORRADOR,
        index=True,
    )

    zona_horaria: Mapped[str] = mapped_column(String(60), default="America/La_Paz")
    max_equipos: Mapped[int | None] = mapped_column(Integer)
    inscripcion_abre: Mapped[datetime | None] = mapped_column(DateTimeUTC)
    inscripcion_cierra: Mapped[datetime | None] = mapped_column(DateTimeUTC)
    roster_lock: Mapped[datetime | None] = mapped_column(DateTimeUTC)
    fecha_inicio: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    bolsa_premios: Mapped[str | None] = mapped_column(String(120))

    reglamento_url: Mapped[str | None] = mapped_column(String(500))
    version_reglamento: Mapped[str | None] = mapped_column(String(40))

    # Si está en True, para inscribirse hay que elegir un equipo permanente
    # ya existente (y por lo tanto tener cuenta). En False —el default— se
    # puede seguir anotando un equipo suelto sin loguearse.
    #
    # Es configurable por edición, no global, copiando lo que hace
    # Toornament: forzar cuenta en todos los torneos agregaría fricción
    # justo en el embudo que más importa (que los equipos se anoten), así
    # que la decisión la toma el organizador de cada torneo. El que quiere
    # historial acumulado lo prende; el torneo de base sigue como está.
    requiere_equipo_permanente: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )

    # Canal de Discord al que se publican los avisos de esta edición. Solo
    # se aceptan URLs de webhook de Discord — ver PREFIJOS_WEBHOOK_VALIDOS
    # en app/core/notificaciones.py, es una guarda contra SSRF, no cosmética.
    discord_webhook_url: Mapped[str | None] = mapped_column(String(500))

    # False = torneo abierto: el equipo que se inscribe queda aprobado al
    # instante, sin que el organizador revise uno por uno. NO afecta ninguna
    # otra regla — cupos, plazo, roster y elegibilidad se siguen validando
    # exactamente igual y antes de aprobar nada.
    requiere_aprobacion: Mapped[bool] = mapped_column(Boolean, default=True)

    # Configurables, nunca hardcodeados
    sistema_puntaje: Mapped[dict] = mapped_column(JSON, default=dict)
    criterios_desempate: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )

    torneo: Mapped["Torneo"] = relationship(back_populates="ediciones")
    juego: Mapped["Juego"] = relationship()
    fases: Mapped[list["Fase"]] = relationship(
        back_populates="edicion", order_by="Fase.orden"
    )

    @property
    def acepta_inscripciones(self) -> bool:
        return self.estado == EstadoEdicion.INSCRIPCIONES_ABIERTAS


class Fase(Base):
    __tablename__ = "fases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    edicion_id: Mapped[int] = mapped_column(ForeignKey("ediciones.id"), index=True)
    orden: Mapped[int] = mapped_column(Integer)
    nombre: Mapped[str] = mapped_column(String(120))

    modelo_competencia: Mapped[ModeloCompetencia] = mapped_column(
        Enum(ModeloCompetencia, native_enum=False, length=40)
    )
    formato: Mapped[FormatoFase] = mapped_column(
        Enum(FormatoFase, native_enum=False, length=40)
    )

    # {"bo": 3, "cupos_avance": 2, "grupos": 8, "caidas_por_ronda": 6}
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    estado: Mapped[str] = mapped_column(String(40), default="pendiente", index=True)
    semilla_sorteo: Mapped[int | None] = mapped_column(Integer)

    edicion: Mapped["Edicion"] = relationship(back_populates="fases")
