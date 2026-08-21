from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificacionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    titulo: str
    cuerpo: str
    url: str | None
    edicion_id: int | None
    leida_at: datetime | None
    created_at: datetime


class BandejaNotificaciones(BaseModel):
    """La campanita necesita las dos cosas en el mismo pedido: qué mostrar en
    el desplegable y qué número pintar en el badge. `no_leidas` cuenta TODAS
    las no leídas del usuario, no solo las que entran en `items`."""

    items: list[NotificacionRead]
    no_leidas: int
