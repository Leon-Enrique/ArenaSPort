"""Roster permanente de un equipo, identidad de juego y invitaciones.

El token de una invitación se devuelve UNA sola vez, al crearla
(`InvitacionCreada`). Los listados usan `InvitacionOut`, que no lo incluye:
quien ya tiene acceso al equipo no necesita poder re-copiar el link de una
invitación ajena, y así el token no queda circulando en cada respuesta.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IdentidadEntrada(BaseModel):
    identidad: dict[str, str] = Field(
        description="Campos según el juego. Ej MLBB: {nick, id_juego, server}"
    )
    juego_id: int | None = Field(
        default=None,
        description="Se puede omitir mientras haya un solo juego activo.",
    )


class IdentidadDeJuegoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    juego_id: int
    identidad: dict
    actualizada_at: datetime


class MiembroOut(BaseModel):
    id: int
    usuario_id: int
    usuario_nombre: str | None = None

    # Null cuando la persona fue sumada al equipo pero todavía no cargó su
    # ID de juego. No es un error: el equipo se arma igual y el roster se
    # completa después.
    identidad: dict | None = None

    esta_activo: bool
    created_at: datetime


class AgregarMiembro(BaseModel):
    """Alta directa: el capitán suma a alguien que ya tiene cuenta.

    No lleva identidad de juego a propósito — se toma de la cuenta de esa
    persona. Que el capitán pudiera escribirla sería volver al problema que
    este rediseño resuelve.
    """

    usuario_id: int
    juego_id: int | None = None


class InvitacionCrear(BaseModel):
    usuario_destino_id: int | None = Field(
        default=None,
        description=(
            "Para dirigir la invitación a alguien puntual. Sin esto es un "
            "link abierto que acepta el primero que lo use."
        ),
    )
    juego_id: int | None = None
    dias_de_vida: int = Field(default=7, ge=1, le=30)


class InvitacionCreada(BaseModel):
    id: int
    token: str
    expira_at: datetime
    usuario_destino_id: int | None


class InvitacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    estado: str
    expira_at: datetime
    created_at: datetime
    usuario_destino_id: int | None
    aceptada_por_usuario_id: int | None


class InvitacionPreview(BaseModel):
    """Lo que ve el invitado antes de entrar.

    `ya_cargaste_tu_identidad` le dice al frontend si después de entrar hay
    que pedirle el ID de juego o no: entrar nunca lo exige, pero el roster
    queda incompleto hasta que lo cargue.
    """

    equipo_id: int
    equipo_nombre: str
    juego_id: int
    juego_nombre: str
    campos_requeridos: list[str]
    expira_at: datetime
    dirigida_a_vos: bool
    ya_cargaste_tu_identidad: bool
