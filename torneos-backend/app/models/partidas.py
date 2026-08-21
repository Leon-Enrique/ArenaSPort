"""Partidas, participaciones y disputas.

La tabla clave del sistema: una partida tiene N participaciones, nunca
equipo_a_id / equipo_b_id. Dos participaciones representan un enfrentamiento
directo (MLBB); dieciocho representan una caída de battle royale (Free Fire).
Mismo esquema para cualquier juego.
"""

from datetime import datetime

from sqlalchemy import (
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
from app.domain.enums import EstadoPartida, LadoLlave


class Partida(Base):
    __tablename__ = "partidas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fase_id: Mapped[int] = mapped_column(ForeignKey("fases.id"), index=True)
    numero_caida: Mapped[int | None] = mapped_column(Integer)  # solo multi-equipo

    lado: Mapped[LadoLlave] = mapped_column(
        Enum(LadoLlave, native_enum=False, length=20), default=LadoLlave.UNICA
    )
    ronda: Mapped[int | None] = mapped_column(Integer)
    grupo_numero: Mapped[int | None] = mapped_column(Integer, index=True)  # round robin con grupos

    estado: Mapped[EstadoPartida] = mapped_column(
        Enum(EstadoPartida, native_enum=False, length=40),
        default=EstadoPartida.PROGRAMADA,
        index=True,
    )

    # A dónde avanza el GANADOR de esta partida (cualquier formato de llave).
    siguiente_partida_ganador_id: Mapped[int | None] = mapped_column(
        ForeignKey("partidas.id")
    )
    siguiente_slot_ganador: Mapped[int | None] = mapped_column(Integer)  # 0 o 1

    # A dónde cae el PERDEDOR (solo llave alta de eliminación doble).
    siguiente_partida_perdedor_id: Mapped[int | None] = mapped_column(
        ForeignKey("partidas.id")
    )
    siguiente_slot_perdedor: Mapped[int | None] = mapped_column(Integer)

    programada_para: Mapped[datetime | None] = mapped_column(DateTimeUTC)
    checkin_abre_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)
    checkin_cierra_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)
    confirmada_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )

    participaciones: Mapped[list["ParticipacionEnPartida"]] = relationship(
        back_populates="partida",
        cascade="all, delete-orphan",
        foreign_keys="ParticipacionEnPartida.partida_id",
    )
    disputas: Mapped[list["Disputa"]] = relationship(back_populates="partida")


class ParticipacionEnPartida(Base):
    __tablename__ = "participaciones_partida"
    __table_args__ = (
        UniqueConstraint("partida_id", "equipo_id", name="uq_participacion_equipo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id"), index=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipos.id"), index=True)

    # Slot dentro del cruce (0 o 1) — solo tiene sentido en enfrentamiento
    # directo, para saber a qué lado del próximo cruce avanza. En
    # multi-equipo queda en None.
    slot: Mapped[int | None] = mapped_column(Integer)

    # Enfrentamiento directo
    mapas_ganados: Mapped[int | None] = mapped_column(Integer)
    es_ganador: Mapped[bool | None] = mapped_column(Boolean)

    # Multi-equipo (battle royale)
    posicion: Mapped[int | None] = mapped_column(Integer)
    bajas: Mapped[int | None] = mapped_column(Integer)

    puntos: Mapped[int | None] = mapped_column(Integer)

    checkin_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    partida: Mapped["Partida"] = relationship(
        back_populates="participaciones", foreign_keys=[partida_id]
    )
    equipo: Mapped["Equipo"] = relationship()  # noqa: F821 (resuelto por registry)


class Disputa(Base):
    """'Reportar problema' — escalamiento directo al organizador, separado del
    flujo normal de reporte de resultado. El rival no aparece, hay lag,
    sospecha de trampa.
    """

    __tablename__ = "disputas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id"), index=True)
    abierta_por_equipo_id: Mapped[int] = mapped_column(ForeignKey("equipos.id"))

    motivo: Mapped[str] = mapped_column(Text)
    evidencia_url: Mapped[str | None] = mapped_column(String(500))

    estado: Mapped[str] = mapped_column(String(20), default="abierta", index=True)
    resolucion: Mapped[str | None] = mapped_column(Text)
    resuelta_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )

    partida: Mapped["Partida"] = relationship(back_populates="disputas")


class ReporteResultado(Base):
    """Un reporte de marcador pendiente de confirmación, O una corrección
    aplicada directamente por el organizador.

    Append-only en espíritu: cada reporte/corrección es su propio registro
    (quién, cuándo, qué marcador, con qué motivo). Nunca se sobrescribe un
    registro existente — corregir crea uno nuevo con `es_correccion=True`.
    """

    __tablename__ = "reportes_resultado"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id"), index=True)

    # En un reporte normal (capitán): quién reportó.
    # En una corrección (organizador): queda en None — se usa
    # aplicado_por_usuario_id en su lugar.
    equipo_reportante_id: Mapped[int | None] = mapped_column(ForeignKey("equipos.id"))

    marcador_propio: Mapped[int] = mapped_column(Integer)  # mapas del reportante
    marcador_rival: Mapped[int] = mapped_column(Integer)  # mapas del rival
    evidencia_url: Mapped[str | None] = mapped_column(String(500))

    # pendiente | confirmado | impugnado | resuelto_por_organizador | corregido
    estado: Mapped[str] = mapped_column(String(30), default="pendiente", index=True)

    vencimiento: Mapped[datetime | None] = mapped_column(DateTimeUTC)
    confirmado_por_equipo_id: Mapped[int | None] = mapped_column(ForeignKey("equipos.id"))
    confirmado_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    # Corrección de un resultado ya confirmado, sin que nadie lo haya
    # impugnado (el organizador nota un error días después). Distinto del
    # camino de disputa: ahí ya existe `resolver_disputa` con la acción
    # `confirmar_resultado`.
    es_correccion: Mapped[bool] = mapped_column(Boolean, default=False)
    motivo: Mapped[str | None] = mapped_column(Text)
    aplicado_por_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )


class MensajePartida(Base):
    """Chat de coordinación entre los dos capitanes de una partida puntual
    — no es un chat general, vive atado a la partida para que quede claro
    de qué cruce se está hablando. Se lee con polling (GET cada pocos
    segundos mientras el modal está abierto), no hay tiempo real de
    verdad todavía: no hace falta para coordinar un horario de partida.
    """

    __tablename__ = "mensajes_partida"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id"), index=True)

    # None = lo escribió el organizador, no un equipo.
    equipo_id: Mapped[int | None] = mapped_column(ForeignKey("equipos.id"))
    autor_nombre: Mapped[str] = mapped_column(String(120))
    texto: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone(), index=True
    )
