"""Suizo: la ronda 1 se siembra (mitad superior vs mitad inferior); las
rondas siguientes se generan una por una, después de conocer los resultados
de la anterior — no se pueden precalcular todas de una, es la naturaleza del
formato.

Puro Python.
"""

from dataclasses import dataclass

from app.domain.formatos.base import ErrorFormato


def generar_ronda_1(equipos_seed: list[int]) -> tuple[list[tuple[int, int]], int | None]:
    """Mitad superior contra mitad inferior: 1 vs N/2+1, 2 vs N/2+2, etc.
    Es el emparejamiento suizo estándar de arranque.

    Si `equipos_seed` tiene cantidad impar, el de peor seed (el último de
    la lista) recibe el bye de la ronda 1 — no hay tabla de puntos todavía
    para decidirlo de otra forma, así que se usa la siembra: dárselo al
    mejor sembrado sería injusto, dárselo al peor es lo estándar.

    Devuelve (pares, equipo_bye_id) — equipo_bye_id es None si la cantidad
    era par.
    """
    n = len(equipos_seed)
    if n < 2:
        raise ErrorFormato("Se necesitan al menos 2 equipos.")

    equipo_bye = None
    activos = equipos_seed
    if n % 2 != 0:
        equipo_bye = equipos_seed[-1]
        activos = equipos_seed[:-1]

    mitad = len(activos) // 2
    pares = [(activos[i], activos[i + mitad]) for i in range(mitad)]
    return pares, equipo_bye


@dataclass
class EquipoConPuntaje:
    equipo_id: int
    puntos: int
    diferencia: int = 0  # criterio de desempate para el emparejamiento
    victorias: int = 0
    derrotas: int = 0


def generar_siguiente_ronda(
    tabla: list[EquipoConPuntaje],
    enfrentamientos_previos: set[tuple[int, int]],
    meta_victorias: int | None = None,
    meta_derrotas: int | None = None,
) -> list[tuple[int, int]]:
    """Empareja por récord (o puntaje) similar, evitando repetir rivales
    cuando es posible.

    Si se pasan `meta_victorias`/`meta_derrotas` (el suizo "con corte" tipo
    MPL/M7: 3 victorias clasifica, 3 derrotas elimina), primero se sacan de
    la ronda los equipos que ya llegaron a cualquiera de los dos límites —
    esos ya terminaron su suizo — y el resto se ordena y empareja por
    récord exacto (mismas victorias, luego menos derrotas), que es
    justamente el emparejamiento "1-0 contra 1-0, 0-1 contra 0-1" de la
    imagen de referencia. Sin metas, se mantiene el comportamiento genérico
    anterior: ordenar por puntaje.

    Algoritmo greedy estándar: ordena, y empareja de a dos consecutivos; si
    el emparejamiento natural ya se jugó, busca el próximo candidato
    compatible más cercano en la tabla. Si no hay ninguno compatible
    (típico en la última ronda con pocos equipos), permite repetir y lo
    señala — mejor un rival repetido que un equipo sin partida.

    Devuelve pares (equipo_a, equipo_b). Si la cantidad de equipos activos
    es impar, el último de la tabla (el de peor récord) queda libre — el
    llamador decide qué hacer con ese bye (típicamente puntos/una victoria
    gratis).
    """
    activos = [
        e for e in tabla
        if (meta_victorias is None or e.victorias < meta_victorias)
        and (meta_derrotas is None or e.derrotas < meta_derrotas)
    ]

    if meta_victorias is not None or meta_derrotas is not None:
        ordenados = sorted(activos, key=lambda e: (-e.victorias, e.derrotas, -e.diferencia))
    else:
        ordenados = sorted(activos, key=lambda e: (-e.puntos, -e.diferencia))
    pendientes = [e.equipo_id for e in ordenados]

    pares: list[tuple[int, int]] = []
    while len(pendientes) >= 2:
        a = pendientes.pop(0)
        candidato_idx = 0
        while candidato_idx < len(pendientes):
            b = pendientes[candidato_idx]
            clave = (min(a, b), max(a, b))
            if clave not in enfrentamientos_previos:
                pendientes.pop(candidato_idx)
                pares.append((a, b))
                break
            candidato_idx += 1
        else:
            # No hay ningún rival nuevo disponible: repetir con el más cercano.
            b = pendientes.pop(0)
            pares.append((a, b))

    return pares


def equipo_libre(
    tabla: list[EquipoConPuntaje],
    ya_emparejados: set[int],
    meta_victorias: int | None = None,
    meta_derrotas: int | None = None,
) -> int | None:
    """El equipo sin partida cuando la cantidad de activos es impar (recibe bye)."""
    activos = [
        e for e in tabla
        if (meta_victorias is None or e.victorias < meta_victorias)
        and (meta_derrotas is None or e.derrotas < meta_derrotas)
    ]
    for e in sorted(activos, key=lambda e: (e.victorias, -e.derrotas, e.puntos, e.diferencia)):
        if e.equipo_id not in ya_emparejados:
            return e.equipo_id
    return None
