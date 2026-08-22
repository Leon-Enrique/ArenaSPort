"""Récord histórico de un equipo, acumulado entre torneos.

Puro Python, sin DB: recibe partidas ya resueltas como datos simples. La ruta
se encarga de traerlas.

Dos decisiones que definen qué significa el récord, y que conviene tener a la
vista porque cambian los números que ve la gente:

  - Los BYE no cuentan. Un bye es un lugar libre en el cuadro, no una
    partida: nadie juega y no hay rival. Contarlos como victorias infla el
    récord de quien tuvo suerte con la siembra, y dos equipos con el mismo
    desempeño real quedarían con récords distintos según cómo cayó el
    sorteo.
  - Los WALKOVER sí cuentan. El rival no se presentó, pero es un resultado
    decidido con un ganador y así se registra en cualquier liga.
"""

from dataclasses import dataclass, field

# Estados en los que una partida ya tiene un resultado definitivo.
ESTADOS_RESUELTOS = ("confirmada", "walkover")
ESTADO_BYE = "bye"


@dataclass
class PartidaDeEquipo:
    """Una partida vista desde el lado de UN equipo."""

    partida_id: int
    edicion_id: int
    estado: str
    es_ganador: bool | None
    mapas_propios: int | None = None
    mapas_rival: int | None = None
    ronda: int | None = None
    fase_id: int | None = None


@dataclass
class Record:
    jugadas: int = 0
    ganadas: int = 0
    perdidas: int = 0
    mapas_favor: int = 0
    mapas_contra: int = 0
    byes: int = 0

    @property
    def diferencia_mapas(self) -> int:
        return self.mapas_favor - self.mapas_contra

    @property
    def porcentaje_victorias(self) -> float | None:
        """None cuando todavía no jugó nada: mostrar 0% sería mentir sobre un
        equipo que no perdió nunca, simplemente no debutó."""
        if self.jugadas == 0:
            return None
        return round(self.ganadas * 100 / self.jugadas, 1)


def calcular_record(partidas: list[PartidaDeEquipo]) -> Record:
    """Récord acumulado a partir de las partidas resueltas de un equipo."""
    record = Record()
    for p in partidas:
        if p.estado == ESTADO_BYE:
            record.byes += 1
            continue
        if p.estado not in ESTADOS_RESUELTOS:
            continue

        record.jugadas += 1
        if p.es_ganador:
            record.ganadas += 1
        else:
            record.perdidas += 1

        # Un walkover puede no tener marcador cargado: se cuenta la partida
        # pero no se inventan mapas.
        if p.mapas_propios is not None:
            record.mapas_favor += p.mapas_propios
        if p.mapas_rival is not None:
            record.mapas_contra += p.mapas_rival

    return record


@dataclass
class ResumenDeEdicion:
    edicion_id: int
    record: Record = field(default_factory=Record)
    ronda_maxima: int | None = None


def resumir_por_edicion(partidas: list[PartidaDeEquipo]) -> list[ResumenDeEdicion]:
    """Un récord por cada edición en la que el equipo jugó, ordenado por
    edición. `ronda_maxima` es lo más lejos que llegó en esa edición —
    incluye los byes, porque avanzar por bye igual es avanzar."""
    por_edicion: dict[int, list[PartidaDeEquipo]] = {}
    for p in partidas:
        por_edicion.setdefault(p.edicion_id, []).append(p)

    resumenes = []
    for edicion_id in sorted(por_edicion):
        del_grupo = por_edicion[edicion_id]
        rondas = [p.ronda for p in del_grupo if p.ronda is not None]
        resumenes.append(
            ResumenDeEdicion(
                edicion_id=edicion_id,
                record=calcular_record(del_grupo),
                ronda_maxima=max(rondas) if rondas else None,
            )
        )
    return resumenes


def gano_la_final(
    partidas_de_la_fase: list[PartidaDeEquipo], equipo_id: int, ganadores: dict[int, int | None]
) -> bool:
    """True si el equipo ganó la partida de ronda más alta de una fase.

    Sirve para marcar campeón en una fase de eliminación. Es deliberadamente
    conservador: solo mira la última ronda de la fase que se le pase, así que
    el llamador tiene que darle la fase FINAL de la edición. No intenta
    deducir el campeón de un round robin ni de un suizo — ahí el primer
    puesto sale de la tabla, no de una partida, y mezclar las dos cosas daría
    "campeones" inventados en formatos donde no hay una final.
    """
    if not partidas_de_la_fase:
        return False
    rondas = [p.ronda for p in partidas_de_la_fase if p.ronda is not None]
    if not rondas:
        return False
    ultima = max(rondas)
    finales = [p for p in partidas_de_la_fase if p.ronda == ultima]
    return any(ganadores.get(p.partida_id) == equipo_id for p in finales)
