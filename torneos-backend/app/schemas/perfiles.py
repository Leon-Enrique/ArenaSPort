from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RecordOut(BaseModel):
    jugadas: int
    ganadas: int
    perdidas: int
    mapas_favor: int
    mapas_contra: int
    diferencia_mapas: int
    byes: int
    porcentaje_victorias: float | None


class JugadorDePerfilOut(BaseModel):
    """Un integrante del roster.

    Sin `discord_id`: es el identificador de una persona real —a veces menor
    de edad— y este endpoint es público. La misma regla que ya aplica
    `_redactar_para_publico` en inscripciones.py.
    """

    nick: str
    es_capitan: bool
    es_suplente: bool


class ParticipacionEnTorneoOut(BaseModel):
    edicion_id: int
    edicion_nombre: str
    edicion_slug: str
    torneo_nombre: str
    juego_nombre: str
    estado_edicion: str
    record: RecordOut
    ronda_maxima: int | None
    campeon: bool
    roster: list[JugadorDePerfilOut]


class PerfilEquipoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tag: str | None
    logo_url: str | None
    created_at: datetime

    # Quién administra el equipo. Es también quién queda de capitán en cada
    # inscripción, así que la pantalla de plantel lo necesita para marcarlo.
    # Va acá y no en el roster porque es del equipo, no de una membresía.
    # Es un id de cuenta, no un dato de contacto: Battlefy y Toornament
    # también muestran públicamente quién capitanea un equipo.
    propietario_usuario_id: int | None

    record_global: RecordOut
    torneos_jugados: int
    titulos: int
    historial: list[ParticipacionEnTorneoOut]


class EquipoEnListadoOut(BaseModel):
    id: int
    nombre: str
    tag: str | None
    logo_url: str | None
    torneos_jugados: int
    partidas_ganadas: int


class MiEquipoOut(BaseModel):
    """Un equipo permanente del usuario, para el selector de inscripción."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tag: str | None
    logo_url: str | None
    torneos_jugados: int = 0


class EquipoCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    tag: str | None = Field(default=None, max_length=12)
    logo_url: str | None = None


class EquipoUpdate(BaseModel):
    """Todo opcional: se manda solo lo que cambia."""

    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    tag: str | None = Field(default=None, max_length=12)
    logo_url: str | None = None


class EquipoDeJugadorOut(BaseModel):
    equipo_id: int
    equipo_nombre: str
    equipo_tag: str | None
    edicion_nombre: str
    edicion_slug: str
    torneo_nombre: str
    es_capitan: bool
    es_suplente: bool


class PerfilJugadorOut(BaseModel):
    """Carrera de un jugador.

    No trae estadísticas individuales, y no es un recorte: el modelo de datos
    no las tiene. `ParticipacionEnPartida` guarda mapas, posición y bajas por
    EQUIPO, nunca por persona, así que lo único que se puede afirmar de un
    jugador es dónde jugó. Inventar un KDA acá sería mostrar un número que no
    se corresponde con nada registrado.
    """

    clave_identidad: str
    juego_codigo: str
    juego_nombre: str
    nicks_usados: list[str]
    equipos: list[EquipoDeJugadorOut]
    torneos_jugados: int
