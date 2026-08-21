"""Reglas del ciclo de vida de una partida: check-in y su resolución.

Puro Python, sin dependencias de framework ni DB — se testea solo.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

CHECKIN_MINUTOS_ANTES = 15


def debe_auto_abrir_checkin(programada_para: datetime | None, ahora: datetime) -> bool:
    """Una partida con horario cargado abre su check-in sola, sin que el
    organizador tenga que apretar nada — CHECKIN_MINUTOS_ANTES antes de la
    hora programada. Partidas sin horario (`programada_para` en None)
    siguen necesitando que alguien las abra a mano con /abrir-checkin.
    """
    if programada_para is None:
        return False
    return ahora >= programada_para - timedelta(minutes=CHECKIN_MINUTOS_ANTES)


class ErrorPartida(Exception):
    """Error de negocio en el ciclo de vida de una partida."""


class ResultadoCheckin(StrEnum):
    EN_ESPERA = "en_espera"  # no venció el tiempo, todavía puede confirmar el resto
    TODOS_LISTOS = "todos_listos"  # confirmaron todos, arranca la partida
    WALKOVER = "walkover"  # venció el tiempo, al menos uno no confirmó
    NADIE_CONFIRMO = "nadie_confirmo"  # venció el tiempo, no confirmó nadie


@dataclass
class EvaluacionCheckin:
    resultado: ResultadoCheckin
    equipo_ganador_id: int | None = None


@dataclass
class ResultadoValidado:
    gana_reportante: bool  # True si el marcador propio (reportante) es mayor


def bo_para_ronda(config: dict | None, ronda: int | None) -> int:
    """BO (mejor de) efectivo para una ronda puntual de la fase.

    Por defecto todas las rondas usan `config["bo"]`. La fase puede definir
    `bo_por_ronda`, una lista de tramos `{"ronda": N, "bo": M}` — cualquier
    cantidad, no solo uno — para escalar el formato progresivamente (ej.
    BO1 hasta la ronda 3, BO3 en la ronda 4, BO5 en la gran final). Se
    aplica el tramo con el `ronda` más alto que sea <= la ronda pedida; si
    ningún tramo aplica (o no hay ninguno), se usa el BO base.
    """
    config = config or {}
    bo_base = config.get("bo", 1)
    tramos = config.get("bo_por_ronda") or []

    if ronda is None:
        return bo_base

    aplicables = [
        t for t in tramos
        if t.get("ronda") is not None and t.get("bo") is not None and ronda >= t["ronda"]
    ]
    if not aplicables:
        return bo_base
    return max(aplicables, key=lambda t: t["ronda"])["bo"]


def validar_marcador(bo: int, marcador_propio: int, marcador_rival: int) -> ResultadoValidado:
    """Valida un marcador de enfrentamiento directo contra el formato BO
    (mejor de 1/3/5) configurado en la fase.

    No decide nada por fuera del marcador en sí — no sabe de partidas, de
    equipos reales, ni de quién reporta. Solo la aritmética.
    """
    if marcador_propio < 0 or marcador_rival < 0:
        raise ErrorPartida("El marcador no puede ser negativo.")

    if marcador_propio + marcador_rival > bo:
        raise ErrorPartida(
            f"La suma de mapas ({marcador_propio + marcador_rival}) "
            f"supera el formato configurado (BO{bo})."
        )

    if marcador_propio == marcador_rival:
        raise ErrorPartida("El marcador no puede terminar en empate.")

    mapas_para_ganar = bo // 2 + 1
    if max(marcador_propio, marcador_rival) < mapas_para_ganar:
        raise ErrorPartida(
            f"En un BO{bo} hace falta llegar a {mapas_para_ganar} mapas para ganar."
        )

    return ResultadoValidado(gana_reportante=marcador_propio > marcador_rival)


def evaluar_checkin(
    confirmaciones: dict[int, datetime | None],
    checkin_cierra_at: datetime | None,
    ahora: datetime,
) -> EvaluacionCheckin:
    """Decide qué corresponde hacer con una partida en checkin.

    No muta nada — el llamador aplica el resultado a la base de datos.

    Args:
        confirmaciones: equipo_id -> instante de checkin, o None si no confirmó.
        checkin_cierra_at: fin de la ventana de check-in.
        ahora: instante actual (inyectado para poder testear sin esperar).
    """
    faltantes = [eid for eid, ts in confirmaciones.items() if ts is None]
    confirmados = [eid for eid, ts in confirmaciones.items() if ts is not None]

    if not faltantes:
        return EvaluacionCheckin(ResultadoCheckin.TODOS_LISTOS)

    if checkin_cierra_at is not None and ahora < checkin_cierra_at:
        return EvaluacionCheckin(ResultadoCheckin.EN_ESPERA)

    # Venció el tiempo y falta alguien.
    if not confirmados:
        return EvaluacionCheckin(ResultadoCheckin.NADIE_CONFIRMO)

    if len(confirmados) == 1:
        # Caso claro de enfrentamiento directo: el presente gana por walkover.
        return EvaluacionCheckin(ResultadoCheckin.WALKOVER, equipo_ganador_id=confirmados[0])

    # Multi-equipo con varias confirmaciones y algunas faltantes: no hay un
    # único "ganador" de walkover — los ausentes simplemente no puntúan esta
    # caída. El llamador decide qué hacer con cada participación.
    return EvaluacionCheckin(ResultadoCheckin.WALKOVER)
