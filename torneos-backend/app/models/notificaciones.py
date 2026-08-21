"""Notificaciones in-app.

Cada fila es "esto le pasó a ESTE usuario": un evento se expande en N filas,
una por destinatario. No hay tabla de evento compartido con una tabla de
lecturas aparte — con el volumen de un torneo (decenas de destinatarios por
evento, no millones) la duplicación es más barata de leer y de borrar que el
join, y deja que cada usuario marque como leída sin tocar nada compartido.

El envío a Discord es un camino separado (ver app/core/notificaciones.py):
esta tabla es el registro durable y consultable, el webhook es el aviso que
llega afuera. Uno puede fallar sin el otro.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base, DateTimeUTC


class Notificacion(Base):
    __tablename__ = "notificaciones"
    __table_args__ = (
        # El contador de no leídas se pide en cada carga de página del
        # frontend: tiene que resolverse por índice, no escaneando.
        Index("ix_notificacion_usuario_leida", "usuario_id", "leida_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)

    tipo: Mapped[str] = mapped_column(String(40))
    titulo: Mapped[str] = mapped_column(String(160))
    cuerpo: Mapped[str] = mapped_column(Text)

    # A dónde lleva el click en el frontend. Ruta relativa, nunca absoluta.
    url: Mapped[str | None] = mapped_column(String(500))

    edicion_id: Mapped[int | None] = mapped_column(ForeignKey("ediciones.id"), index=True)

    leida_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)
    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone(), index=True
    )
