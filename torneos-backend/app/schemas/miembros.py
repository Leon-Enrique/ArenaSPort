"""Roster permanente de un equipo, e invitaciones para entrar en él.

El token de una invitación se devuelve UNA sola vez, al crearla
(`InvitacionCreada`). Los listados usan `InvitacionOut`, que no lo incluye:
quien ya tiene acceso al equipo no necesita poder re-copiar el link de una
invitación ajena, y así el token no queda circulando en cada respuesta.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MiembroOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    identidad: dict
    usuario_id: int
    esta_activo: bool
    created_at: datetime

    # Para mostrar de quién es la fila sin que el frontend tenga que
    # resolver cada usuario_id por separado.
    usuario_nombre: str | None = None


class InvitacionCrear(BaseModel):
    usuario_destino_id: int | None = Field(
        default=None,
        description=(
            "Para invitar a alguien puntual, buscado por nombre. Sin esto la "
            "invitación es un link abierto que acepta el primero que lo use."
        ),
    )
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
    """Lo que ve el invitado ANTES de aceptar.

    Incluye `campos_requeridos` porque el jugador carga su propia identidad
    de juego al aceptar, y el formulario tiene que saber qué pedirle según
    el juego del equipo.
    """

    equipo_id: int
    equipo_nombre: str
    juego_nombre: str
    campos_requeridos: list[str]
    expira_at: datetime
    dirigida_a_vos: bool


class AceptarInvitacion(BaseModel):
    identidad: dict[str, str] = Field(
        description="Campos según el juego. Ej MLBB: {nick, id_juego, server}"
    )
