"""Tipos compartidos por los generadores de llave. Puro Python.

Todo lo que sigue describe ESTRUCTURA (quién juega contra quién, y a dónde
avanza cada uno), nunca toca la base de datos. La persistencia vive en la
capa de rutas, que traduce esta estructura a filas de `Partida`.
"""

from dataclasses import dataclass, field
from enum import StrEnum


class ErrorFormato(Exception):
    """Error de negocio al generar o avanzar un formato de competencia."""


class TipoFuente(StrEnum):
    EQUIPO = "equipo"  # equipo_id conocido de entrada (siembra)
    GANADOR_DE = "ganador_de"  # el ganador de un cruce ya definido
    PERDEDOR_DE = "perdedor_de"  # el perdedor de un cruce de la llave alta
    VACIO = "vacio"  # hueco de bye: nunca va a llegar nadie a este slot


@dataclass(frozen=True)
class Fuente:
    """De dónde sale el equipo que ocupa un slot de un cruce.

    Si tipo es EQUIPO, `valor` es un equipo_id.
    Si es GANADOR_DE o PERDEDOR_DE, `valor` es el índice del cruce origen
    dentro de la lista que se está construyendo.
    """

    tipo: TipoFuente
    valor: int


@dataclass
class Cruce:
    """Un enfrentamiento dentro de la llave, todavía sin persistir.

    `indice` es la posición del cruce dentro de la lista completa que arma el
    generador — se usa para que otros cruces lo referencien como fuente antes
    de que exista ningún ID de base de datos.
    """

    indice: int
    lado: str  # ver LadoLlave: "unica" | "alta" | "baja" | "gran_final"
    ronda: int
    fuente_a: Fuente
    fuente_b: Fuente
    es_bye: bool = False


@dataclass
class ResultadoGeneracion:
    cruces: list[Cruce] = field(default_factory=list)
    total_rondas: int = 0
