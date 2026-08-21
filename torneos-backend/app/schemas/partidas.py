from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import EstadoPartida, LadoLlave


class PartidaCreate(BaseModel):
    """Alta manual de una partida. El generador de llaves (pendiente) va a
    llamar a esta misma lógica en lote una vez que exista.
    """

    equipo_ids: list[int] = Field(min_length=2)
    programada_para: datetime | None = None
    numero_caida: int | None = None


class EquipoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    tag: str | None


class ParticipacionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipo: EquipoResumen
    slot: int | None
    mapas_ganados: int | None
    es_ganador: bool | None
    posicion: int | None
    bajas: int | None
    puntos: int | None
    checkin_at: datetime | None


class PartidaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fase_id: int
    lado: LadoLlave
    ronda: int | None
    numero_caida: int | None
    estado: EstadoPartida
    siguiente_partida_ganador_id: int | None
    siguiente_partida_perdedor_id: int | None
    programada_para: datetime | None
    checkin_abre_at: datetime | None
    checkin_cierra_at: datetime | None
    participaciones: list[ParticipacionRead]


class AbrirCheckinIn(BaseModel):
    minutos: int = Field(default=15, ge=0, le=180)


class ProgramarPartidaIn(BaseModel):
    programada_para: datetime


class MensajePartidaIn(BaseModel):
    equipo_id: int | None = None
    texto: str = Field(min_length=1, max_length=500)


class MensajePartidaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipo_id: int | None
    autor_nombre: str
    texto: str
    created_at: datetime


class ConfirmarCheckinIn(BaseModel):
    equipo_id: int


class ReportarProblemaIn(BaseModel):
    equipo_id: int
    motivo: str = Field(min_length=5)
    evidencia_url: str | None = None


class DisputaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partida_id: int
    abierta_por_equipo_id: int
    motivo: str
    evidencia_url: str | None
    estado: str
    resolucion: str | None
    created_at: datetime
    resuelta_at: datetime | None


class ResultadoEquipoIn(BaseModel):
    equipo_id: int
    mapas_ganados: int = Field(ge=0)


class ResolverDisputaIn(BaseModel):
    resolucion: str = Field(min_length=5)
    accion: str = Field(description="'reprogramar' | 'walkover' | 'confirmar_resultado'")
    equipo_ganador_id: int | None = None
    resultados: list[ResultadoEquipoIn] | None = None


class ReportarResultadoIn(BaseModel):
    equipo_id: int = Field(description="El equipo que reporta")
    marcador_propio: int = Field(ge=0, description="Mapas ganados por quien reporta")
    marcador_rival: int = Field(ge=0, description="Mapas ganados por el rival")
    evidencia_url: str | None = Field(
        default=None,
        description="Sin evidencia, este reporte no se puede auto-confirmar por tiempo.",
    )
    horas_para_confirmar: int = Field(default=3, ge=1, le=48)


class ConfirmarResultadoIn(BaseModel):
    equipo_id: int = Field(description="El equipo que confirma (nunca el que reportó)")


class ImpugnarResultadoIn(BaseModel):
    equipo_id: int
    motivo: str = Field(min_length=5)


class ReporteResultadoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partida_id: int
    equipo_reportante_id: int | None
    marcador_propio: int
    marcador_rival: int
    evidencia_url: str | None
    estado: str
    vencimiento: datetime | None
    confirmado_por_equipo_id: int | None
    confirmado_at: datetime | None
    es_correccion: bool
    motivo: str | None
    aplicado_por_usuario_id: int | None
    created_at: datetime


class CorregirResultadoIn(BaseModel):
    resultados: list[ResultadoEquipoIn] = Field(min_length=2, max_length=2)
    motivo: str = Field(min_length=10, description="Por qué se corrige — queda auditado.")


class CorreccionAplicadaOut(BaseModel):
    partida: PartidaRead
    reporte: ReporteResultadoRead
    advertencia: str | None = Field(
        default=None,
        description=(
            "Si el ganador cambió y esta partida ya había avanzado a la "
            "siguiente, acá se explica qué revisar a mano — la corrección "
            "NO deshace el avance en cascada solo."
        ),
    )
