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
from app.domain.enums import EstadoEdicion, FormatoFase, ModeloCompetencia, RolStaff


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
    fecha_inicio: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    bolsa_premios: Mapped[str | None] = mapped_column(String(120))

    reglamento_url: Mapped[str | None] = mapped_column(String(500))
    version_reglamento: Mapped[str | None] = mapped_column(String(40))

    # Check-in DEL TORNEO: la confirmación de asistencia que se pide antes de
    # sortear, distinta del check-in de cada partida (que vive en `Partida`).
    #
    # Sirve para depurar equipos fantasma: entre que un equipo se inscribe y
    # que arranca el torneo pasan días, y siempre hay algunos que no aparecen.
    # Sortear con ellos deja llaves llenas de walkovers desde la primera
    # ronda, que es la forma más rápida de arruinar un cuadro.
    #
    # Ambos nulos = este torneo no pide check-in y el sorteo toma a todos los
    # aprobados, como siempre.
    checkin_abre_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)
    checkin_cierra_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    # Si está en True, el resultado de una partida solo lo carga el
    # organizador. En False —el default— lo reporta un capitán y el rival
    # confirma, que reparte el trabajo y deja rastro de los dos lados.
    #
    # Battlefy ofrece la misma opción. Sirve para torneos presenciales o con
    # árbitro en cada mesa, donde hacer que los equipos reporten solo agrega
    # pasos.
    solo_organizador_reporta: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )

    # Si está en True —el default— para inscribirse hay que elegir un equipo
    # permanente ya existente, y por lo tanto tener cuenta. En False se
    # puede anotar un equipo suelto sin loguearse.
    #
    # Sigue siendo por edición y no global, copiando lo que hace Toornament
    # con su "Permanent teams only": forzar cuenta en TODOS los torneos
    # agrega fricción justo en el embudo que más importa —que los equipos
    # se anoten— y esa es una decisión de cada torneo, no de la plataforma.
    #
    # El default se dio vuelta cuando la identidad de juego pasó a vivir en
    # la cuenta (ver IdentidadDeJuego): sin cuenta no hay dónde guardar el
    # ID, no hay a quién avisarle que lo sumaron, y no hay forma de que se
    # vaya solo del equipo. El torneo de base sigue siendo posible apagando
    # esto, y ahí se vuelve al roster tipeado por el capitán.
    requiere_equipo_permanente: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1"
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


class StaffDeTorneo(Base):
    """Alguien que ayuda a correr un torneo sin ser organizador global.

    `Usuario.es_organizador` es una bandera global: quien la tiene administra
    TODOS los torneos de la plataforma. Eso hace imposible pedir una mano
    puntual — para que alguien te ayude en una copa había que darle acceso a
    todo, o hacerlo vos.
    """

    __tablename__ = "staff_de_torneo"
    __table_args__ = (
        UniqueConstraint("torneo_id", "usuario_id", name="uq_staff_torneo_usuario"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    torneo_id: Mapped[int] = mapped_column(ForeignKey("torneos.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)

    rol: Mapped[RolStaff] = mapped_column(Enum(RolStaff, native_enum=False, length=40))

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )
