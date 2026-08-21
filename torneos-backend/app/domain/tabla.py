"""Cálculo de tabla de posiciones para enfrentamiento directo.

Puro Python. No sabe nada de la DB — recibe partidas ya resueltas como datos
simples y devuelve la tabla ordenada. La tabla es siempre DERIVADA: se
recalcula desde las partidas confirmadas, nunca es la fuente de verdad.

Desempates configurables y ORDENADOS (nunca fijos en código). El criterio
"enfrentamiento_directo" entre tres o más equipos empatados se resuelve como
un mini-grupo (solo los resultados entre esos equipos), no como una
comparación par a par — es la regla que más se rompe en implementaciones
caseras.
"""

from dataclasses import dataclass

CRITERIOS_POR_DEFECTO = ["puntos", "enfrentamiento_directo", "diferencia_mapas", "mapas_ganados"]


@dataclass
class PartidaParaTabla:
    """Vista mínima de una partida jugada, desacoplada de SQLAlchemy."""

    equipo_a_id: int
    equipo_b_id: int
    mapas_a: int
    mapas_b: int


@dataclass
class FilaTabla:
    equipo_id: int
    jugados: int = 0
    victorias: int = 0
    derrotas: int = 0
    empates: int = 0
    mapas_favor: int = 0
    mapas_contra: int = 0
    puntos: int = 0
    posicion: int | None = None

    @property
    def diferencia_mapas(self) -> int:
        return self.mapas_favor - self.mapas_contra


def calcular_tabla(
    equipos_ids: list[int],
    partidas: list[PartidaParaTabla],
    sistema_puntaje: dict | None = None,
    criterios_desempate: list[str] | None = None,
) -> list[FilaTabla]:
    """Calcula y ordena la tabla. `equipos_ids` incluye a todos los equipos
    del grupo aunque todavía no hayan jugado — aparecen con 0 en todo, no
    desaparecen de la tabla.
    """
    puntaje = sistema_puntaje or {}
    pts_victoria = puntaje.get("victoria", 3)
    pts_empate = puntaje.get("empate", 1)
    pts_derrota = puntaje.get("derrota", 0)

    criterios = criterios_desempate or CRITERIOS_POR_DEFECTO

    filas = {eid: FilaTabla(equipo_id=eid) for eid in equipos_ids}
    enfrentamientos: dict[tuple[int, int], int] = {}  # (yo, rival) -> puntos que sumé contra él

    for p in partidas:
        if p.equipo_a_id not in filas or p.equipo_b_id not in filas:
            continue  # partida de un equipo fuera de este grupo/listado

        a, b = filas[p.equipo_a_id], filas[p.equipo_b_id]
        a.jugados += 1
        b.jugados += 1
        a.mapas_favor += p.mapas_a
        a.mapas_contra += p.mapas_b
        b.mapas_favor += p.mapas_b
        b.mapas_contra += p.mapas_a

        if p.mapas_a > p.mapas_b:
            a.victorias += 1
            b.derrotas += 1
            a.puntos += pts_victoria
            b.puntos += pts_derrota
            enfrentamientos[(p.equipo_a_id, p.equipo_b_id)] = pts_victoria
            enfrentamientos[(p.equipo_b_id, p.equipo_a_id)] = pts_derrota
        elif p.mapas_b > p.mapas_a:
            b.victorias += 1
            a.derrotas += 1
            b.puntos += pts_victoria
            a.puntos += pts_derrota
            enfrentamientos[(p.equipo_b_id, p.equipo_a_id)] = pts_victoria
            enfrentamientos[(p.equipo_a_id, p.equipo_b_id)] = pts_derrota
        else:
            a.empates += 1
            b.empates += 1
            a.puntos += pts_empate
            b.puntos += pts_empate
            enfrentamientos[(p.equipo_a_id, p.equipo_b_id)] = pts_empate
            enfrentamientos[(p.equipo_b_id, p.equipo_a_id)] = pts_empate

    ordenadas = _ordenar_con_desempates(list(filas.values()), criterios, enfrentamientos)
    for i, fila in enumerate(ordenadas, start=1):
        fila.posicion = i
    return ordenadas


_CRITERIOS_SIMPLES = {
    "puntos": lambda f: f.puntos,
    "diferencia_mapas": lambda f: f.diferencia_mapas,
    "mapas_ganados": lambda f: f.mapas_favor,
    "victorias": lambda f: f.victorias,
}


def _ordenar_con_desempates(
    filas: list[FilaTabla],
    criterios: list[str],
    enfrentamientos: dict[tuple[int, int], int],
) -> list[FilaTabla]:
    if len(filas) <= 1 or not criterios:
        return filas

    criterio, resto = criterios[0], criterios[1:]

    if criterio == "enfrentamiento_directo":
        ids_bloque = {f.equipo_id for f in filas}
        puntos_dentro_del_bloque = {
            f.equipo_id: sum(
                enfrentamientos.get((f.equipo_id, rival_id), 0)
                for rival_id in ids_bloque
                if rival_id != f.equipo_id
            )
            for f in filas
        }
        bloques = _agrupar_por_valor(filas, lambda f: puntos_dentro_del_bloque[f.equipo_id])
    else:
        valor_fn = _CRITERIOS_SIMPLES.get(criterio)
        if valor_fn is None:
            return _ordenar_con_desempates(filas, resto, enfrentamientos)
        bloques = _agrupar_por_valor(filas, valor_fn)

    resultado: list[FilaTabla] = []
    for bloque in bloques:
        resultado.extend(_ordenar_con_desempates(bloque, resto, enfrentamientos))
    return resultado


def _agrupar_por_valor(filas: list[FilaTabla], valor_fn) -> list[list[FilaTabla]]:
    """Ordena desc por `valor_fn` y agrupa en bloques de valor idéntico —
    cada bloque es un grupo de empate real que hay que seguir desempatando."""
    ordenadas = sorted(filas, key=valor_fn, reverse=True)
    bloques: list[list[FilaTabla]] = []
    for f in ordenadas:
        v = valor_fn(f)
        if bloques and valor_fn(bloques[-1][0]) == v:
            bloques[-1].append(f)
        else:
            bloques.append([f])
    return bloques


def clasificados_ordenados(
    tablas_por_grupo: dict[int | None, list[FilaTabla]], cupos_por_grupo: int
) -> list[int]:
    """Arma la lista de clasificados de una fase de grupos/suizo, en el
    orden que necesita el sorteo de la siguiente fase: todos los 1ros
    puesto de cada grupo primero (en orden de grupo), después todos los
    2dos, etc.

    Este orden importa — es el mismo criterio que usa Toornament
    ("Outgoing Participants... order them by rank"): reparte a los mejores
    de cada grupo lejos entre sí en la llave siguiente, en vez de que el
    1° y el 2° del mismo grupo puedan cruzarse en la primera ronda.
    """
    grupos_en_orden = sorted(tablas_por_grupo.keys(), key=lambda g: (g is None, g))
    clasificados: list[int] = []
    for posicion in range(cupos_por_grupo):
        for grupo in grupos_en_orden:
            tabla = tablas_por_grupo[grupo]
            if posicion < len(tabla):
                clasificados.append(tabla[posicion].equipo_id)
    return clasificados
