from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.inscripciones import InscripcionRead


class MiInscripcionOut(BaseModel):
    """Un equipo del que el usuario logueado es capitán (o jugador), en
    cualquier edición — se arma cruzando Jugador.discord_id con el
    discord_id del usuario, no depende de que Equipo tenga dueño."""

    edicion_id: int
    edicion_nombre: str
    edicion_slug: str
    torneo_nombre: str
    torneo_slug: str
    es_capitan: bool
    inscripcion: InscripcionRead


class MiPartidaOut(BaseModel):
    """Una partida de alguno de los equipos que capitanea el usuario
    logueado — pensado para el 'Mis Partidas' del perfil, para que sepa
    que le toca actuar sin tener que ir a buscar el torneo a mano."""

    partida_id: int
    fase_id: int
    fase_nombre: str
    edicion_nombre: str
    edicion_slug: str
    torneo_nombre: str
    estado: str
    ronda: int | None
    mi_equipo_id: int | None
    mi_equipo_nombre: str | None
    rival_equipo_nombre: str | None
    checkin_cierra_at: datetime | None
    programada_para: datetime | None


class UsuarioAdminOut(BaseModel):
    """Vista de un usuario para el panel de organizador — nunca se expone
    a nadie que no sea organizador (ver app/api/routes/usuarios.py)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    discord_id: str
    discord_username: str
    discord_avatar_url: str | None
    es_organizador: bool
    puede_gestionar_organizadores: bool
    esta_activo: bool
    created_at: datetime
    ultimo_login_at: datetime


class CambiarRolIn(BaseModel):
    es_organizador: bool = Field(
        description="true para promover a organizador, false para sacarle el rol."
    )
    puede_gestionar_organizadores: bool | None = Field(
        default=None,
        description=(
            "Segundo nivel: quién puede tocar la lista de organizadores en sí. "
            "Solo alguien que YA lo tiene puede otorgarlo o quitarlo — de ahí que "
            "todo este endpoint ya exija ese permiso para poder llamarse. "
            "Si se omite, no se toca el valor actual."
        ),
    )


class UsuarioBusquedaOut(BaseModel):
    """Lo mínimo para elegir a alguien de una lista: quién es, y si ya
    tiene acceso global.

    Deliberadamente más chico que `UsuarioAdminOut`. El buscador lo usa
    cualquier organizador para armar el staff de su torneo, y para eso no
    necesita — ni debería — ver el estado de permisos de toda la
    plataforma. `es_organizador` sí viaja, pero por lo contrario: para
    poder avisar que agregar a esa persona no cambiaría nada, porque ya
    entra a todos los torneos.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    discord_id: str
    discord_username: str
    discord_avatar_url: str | None
    es_organizador: bool
