"""Round robin: todos contra todos. Con división opcional en grupos.

Puro Python.
"""

from app.domain.formatos.base import ErrorFormato


def dividir_en_grupos(equipos_seed: list[int], cantidad_grupos: int) -> list[list[int]]:
    """Reparte los equipos en grupos balanceados usando siembra en serpentina
    (1° al grupo A, 2° al B, ..., último grupo, y vuelve en sentido inverso)
    para que los mejores sembrados queden repartidos parejo.
    """
    if cantidad_grupos < 1:
        raise ErrorFormato("La cantidad de grupos debe ser al menos 1.")
    if cantidad_grupos > len(equipos_seed):
        raise ErrorFormato("No puede haber más grupos que equipos.")

    grupos: list[list[int]] = [[] for _ in range(cantidad_grupos)]
    ida = True
    i = 0
    idx_grupo = 0
    while i < len(equipos_seed):
        grupos[idx_grupo].append(equipos_seed[i])
        i += 1
        if ida:
            idx_grupo += 1
            if idx_grupo == cantidad_grupos:
                idx_grupo -= 1
                ida = False
        else:
            idx_grupo -= 1
            if idx_grupo < 0:
                idx_grupo = 0
                ida = True
    return grupos


def generar_partidos_grupo(equipos: list[int]) -> list[tuple[int, int]]:
    """Todos contra todos dentro de un solo grupo. Orden estable, no aleatorio
    (el calendario real de quién juega cuándo lo arma el organizador aparte)."""
    if len(equipos) < 2:
        raise ErrorFormato("Un grupo necesita al menos 2 equipos.")
    partidos = []
    for i in range(len(equipos)):
        for j in range(i + 1, len(equipos)):
            partidos.append((equipos[i], equipos[j]))
    return partidos
