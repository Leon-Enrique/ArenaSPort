from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import EstadoEdicion, EstadoInscripcion, ModeloCompetencia


# --- Juegos ---
class CampoIdentidad(BaseModel):
    nombre: str
    etiqueta: str
    requerido: bool = True


class JuegoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    modelo_competencia_default: ModeloCompetencia
    titulares_requeridos: int
    suplentes_maximos: int
    campos_identidad: dict


# --- Ediciones ---
class EdicionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    torneo_id: int
    juego: JuegoRead
    numero: int
    nombre: str
    slug: str
    estado: EstadoEdicion
    zona_horaria: str
    max_equipos: int | None
    inscripcion_abre: datetime | None
    inscripcion_cierra: datetime | None
    roster_lock: datetime | None
    fecha_inicio: datetime | None
    bolsa_premios: str | None
    reglamento_url: str | None
    equipos_aprobados: int = 0


class EdicionCreate(BaseModel):
    torneo_id: int
    juego_id: int
    numero: int = Field(ge=1)
    nombre: str = Field(min_length=3, max_length=160)
    max_equipos: int | None = Field(default=None, ge=2)
    zona_horaria: str = "America/La_Paz"
    fecha_inicio: datetime | None = None
    bolsa_premios: str | None = Field(default=None, max_length=120)

    @field_validator("fecha_inicio")
    @classmethod
    def _con_zona_horaria(cls, value: datetime | None) -> datetime | None:
        # Un <input type="date"> del frontend (u otro cliente) manda una
        # fecha sin offset ("2026-09-01"), que Pydantic parsea como
        # datetime 'naive' — DateTimeUTC (ver app/db/database.py) rechaza
        # guardar eso. Interpretarla como UTC evita el 500 sin obligar al
        # cliente a mandar un ISO con offset.
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


# --- Torneos ---
class TorneoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    slug: str
    descripcion: str | None
    logo_url: str | None


class TorneoCreate(BaseModel):
    nombre: str = Field(min_length=3, max_length=160)
    descripcion: str | None = None
    logo_url: str | None = None


# --- Inscripción ---
class JugadorEntradaIn(BaseModel):
    """Un jugador tal como llega del formulario público."""

    identidad: dict[str, str] = Field(
        description="Campos según el juego. Ej MLBB: {nick, id_juego, server}"
    )
    es_suplente: bool | None = Field(
        default=None,
        description="Si no se envía, el sistema asigna suplentes automáticamente.",
    )
    es_capitan: bool = False
    discord_id: str | None = Field(
        default=None,
        description=(
            "ID de Discord de este jugador, si ya inició sesión al inscribirse. "
            "Sin esto, el capitán no va a poder reportar resultados hasta que "
            "el organizador lo vincule manualmente."
        ),
    )


class InscripcionCreate(BaseModel):
    nombre_equipo: str = Field(min_length=2, max_length=120)
    tag: str | None = Field(default=None, max_length=12)
    logo_url: str | None = None
    contacto_nombre: str | None = None
    contacto_whatsapp: str | None = None
    contacto_discord: str | None = None
    capitan_declarado: str | None = Field(
        default=None,
        description="Nombre que el equipo indica como capitán. Puede ser nombre real.",
    )
    jugadores: list[JugadorEntradaIn] = Field(min_length=1)


class JugadorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    identidad: dict
    orden: int
    es_suplente: bool
    es_capitan: bool
    discord_id: str | None


class EquipoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tag: str | None
    logo_url: str | None


class InscripcionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edicion_id: int
    estado: EstadoInscripcion
    seed: int | None
    created_at: datetime
    equipo: EquipoRead
    jugadores: list[JugadorRead]


class InscripcionCreada(BaseModel):
    """Respuesta del registro: incluye lo que el sistema asumió."""

    inscripcion: InscripcionRead
    avisos: list[str] = []


class RevisionInscripcion(BaseModel):
    estado: EstadoInscripcion
    motivo_rechazo: str | None = None
