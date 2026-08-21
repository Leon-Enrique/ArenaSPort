from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import FormatoFase, ModeloCompetencia
from app.schemas.inscripciones import EdicionRead


class FaseCreate(BaseModel):
    """Alta manual de una fase.

    El generador de llaves (pendiente) va a crear fases automáticamente a
    partir de la configuración de la edición; esto es lo mínimo para poder
    colgar partidas mientras tanto.
    """

    orden: int = Field(ge=1)
    nombre: str = Field(min_length=2, max_length=120)
    modelo_competencia: ModeloCompetencia
    formato: FormatoFase
    config: dict = Field(default_factory=dict)


class SortearDesdeFaseAnteriorIn(BaseModel):
    fase_origen_id: int = Field(description="La fase de la que salen los clasificados.")
    cupos_por_grupo: int | None = Field(
        default=None,
        description=(
            "Si la fase de origen es round_robin/suizo (tiene tabla): cuántos "
            "avanzan de cada grupo. La fase de origen tiene que estar 'cerrada'."
        ),
    )
    ronda_origen: int | None = Field(
        default=None,
        description=(
            "Si la fase de origen es una eliminación simple (tiene bracket, no "
            "tabla): de qué ronda tomar los ganadores — ej. ronda 1 de una llave "
            "de 16 da los 8 ganadores, sin necesidad de que el resto de esa "
            "llave (rondas 2 en adelante) se juegue ni se cierre nunca."
        ),
    )


class FilaTablaRead(BaseModel):
    equipo_id: int
    equipo_nombre: str
    posicion: int
    jugados: int
    victorias: int
    empates: int
    derrotas: int
    mapas_favor: int
    mapas_contra: int
    diferencia_mapas: int
    puntos: int


class TablaGrupoRead(BaseModel):
    grupo: int | None  # None si la fase no está dividida en grupos
    filas: list[FilaTablaRead]


class FaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    edicion_id: int
    orden: int
    nombre: str
    modelo_competencia: ModeloCompetencia
    formato: FormatoFase
    estado: str
    config: dict


class PartidaResumen(BaseModel):
    """Versión liviana de una partida para la vista general — no trae la
    estructura completa de participaciones, solo lo que se necesita para
    mostrar una fila en 'Últimos resultados' o 'Próximas partidas'."""

    id: int
    fase_id: int
    fase_nombre: str
    ronda: int | None
    estado: str
    equipo_a_nombre: str | None
    equipo_b_nombre: str | None
    mapas_a: int | None
    mapas_b: int | None
    confirmada_at: datetime | None
    programada_para: datetime | None


class InfoJuegoResumen(BaseModel):
    codigo: str
    nombre: str


class ResumenEdicionOut(BaseModel):
    """Todo lo que necesita la pantalla de 'Vista general' de un torneo en
    un solo pedido — últimos resultados, próximas partidas, info y fases —
    en vez de que el frontend arme eso pegándole a media docena de
    endpoints distintos y combinando client-side."""

    edicion: EdicionRead
    juego: InfoJuegoResumen
    equipos_aprobados: int
    fases: list[FaseRead]
    ultimos_resultados: list[PartidaResumen]
    proximas_partidas: list[PartidaResumen]
