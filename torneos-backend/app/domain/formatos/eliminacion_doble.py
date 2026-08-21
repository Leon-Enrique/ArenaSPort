"""Eliminación doble: llave alta (winners) + llave baja (losers) + gran final.

Reutiliza el generador de eliminación simple para la llave alta completa.
La llave baja se construye con una simulación round-by-round: en cada
"ronda mixta" absorbe los perdedores que caen de la llave alta junto con
los sobrevivientes de la llave baja; en cada "ronda pura" los sobrevivientes
de la llave baja juegan entre sí para reducirse antes de la próxima mezcla.

Cuando en una ronda sobra un equipo sin pareja (por los byes de la llave
alta), NO se crea un cruce fantasma para esa espera — la fuente pasa
directo a la ronda siguiente como si ya hubiera ganado. Esto evita crear
partidas con un solo lado ocupado que nunca se van a poder jugar; el
"bye estructural" es invisible salvo que el organizador audite el árbol.

Cuentas verificadas por tests para n=3..64 (ver tests/test_eliminacion_doble.py):

  - Partidas JUGABLES (las que no son bye): siempre 2n-2. Es la cuenta que
    importa — cada equipo salvo el campeón pierde dos veces y cada partida
    real produce una sola derrota.
  - Filas generadas en total: n + cuadro - 2, donde `cuadro` es la potencia
    de 2 que envuelve a n. Incluye los cruces bye de la llave alta, que se
    auto-resuelven sin jugarse. Solo coincide con 2n-2 cuando n ya es
    potencia de 2 y por lo tanto no hay ningún bye.

La distinción no es cosmética: contar las filas totales y esperar 2n-2 da un
falso error para todo n irregular, que es la mayoría de los torneos reales.
"""

from dataclasses import dataclass

from app.domain.formatos import eliminacion_simple
from app.domain.formatos.base import (
    Cruce,
    ErrorFormato,
    Fuente,
    ResultadoGeneracion,
    TipoFuente,
)


@dataclass
class _FuentePendiente:
    """Una fuente que todavía no jugó su próximo cruce en la llave baja."""

    fuente: Fuente


def generar(equipos_seed: list[int]) -> ResultadoGeneracion:
    n = len(equipos_seed)
    if n < 3:
        raise ErrorFormato("La eliminación doble necesita al menos 3 equipos.")

    llave_alta = eliminacion_simple.generar(equipos_seed)
    cruces: list[Cruce] = []

    # Copiar la llave alta tal cual, marcando el lado.
    for c in llave_alta.cruces:
        cruces.append(
            Cruce(
                indice=c.indice,
                lado="alta",
                ronda=c.ronda,
                fuente_a=c.fuente_a,
                fuente_b=c.fuente_b,
                es_bye=c.es_bye,
            )
        )
    siguiente_indice = len(cruces)

    # Perdedores reales por ronda de la llave alta (los cruces bye no
    # producen perdedor: el hueco no existe).
    rondas_alta = llave_alta.total_rondas
    perdedores_por_ronda: dict[int, list[Fuente]] = {r: [] for r in range(1, rondas_alta + 1)}
    for c in llave_alta.cruces:
        if not c.es_bye:
            perdedores_por_ronda[c.ronda].append(Fuente(TipoFuente.PERDEDOR_DE, c.indice))

    def emparejar_ronda_baja(
        entrantes: list[Fuente], ronda_baja: int
    ) -> list[Fuente]:
        """Empareja de a 2. El que sobra pasa directo (bye estructural,
        sin cruce) a la lista de ganadores que se devuelve.
        """
        nonlocal siguiente_indice
        ganadores: list[Fuente] = []
        i = 0
        while i + 1 < len(entrantes):
            idx = siguiente_indice
            cruces.append(
                Cruce(
                    indice=idx,
                    lado="baja",
                    ronda=ronda_baja,
                    fuente_a=entrantes[i],
                    fuente_b=entrantes[i + 1],
                )
            )
            siguiente_indice += 1
            ganadores.append(Fuente(TipoFuente.GANADOR_DE, idx))
            i += 2
        if i < len(entrantes):
            ganadores.append(entrantes[i])  # bye estructural
        return ganadores

    ronda_baja = 1
    espera = emparejar_ronda_baja(perdedores_por_ronda[1], ronda_baja)

    for r in range(2, rondas_alta + 1):
        if r >= 3:
            ronda_baja += 1
            espera = emparejar_ronda_baja(espera, ronda_baja)
        ronda_baja += 1
        espera = emparejar_ronda_baja(espera + perdedores_por_ronda[r], ronda_baja)

    # Consolidar si queda más de un sobreviviente tras absorber la final de
    # la llave alta (puede pasar con conteos irregulares).
    while len(espera) > 1:
        ronda_baja += 1
        espera = emparejar_ronda_baja(espera, ronda_baja)

    if len(espera) != 1:
        # No debería ocurrir nunca si el algoritmo está bien — lo dejamos
        # como aserción explícita en vez de fallar en silencio más adelante.
        raise ErrorFormato(
            f"No se pudo reducir la llave baja a un único campeón "
            f"(quedaron {len(espera)}). Revisar el generador con n={n}."
        )

    campeon_alta = Fuente(TipoFuente.GANADOR_DE, _indice_final_alta(llave_alta))
    campeon_baja = espera[0]

    idx_gran_final = siguiente_indice
    cruces.append(
        Cruce(
            indice=idx_gran_final,
            lado="gran_final",
            ronda=ronda_baja + 1,
            fuente_a=campeon_alta,
            fuente_b=campeon_baja,
        )
    )

    total_rondas = ronda_baja + 1
    return ResultadoGeneracion(cruces=cruces, total_rondas=total_rondas)


def _indice_final_alta(llave_alta: ResultadoGeneracion) -> int:
    return max(c.indice for c in llave_alta.cruces if c.ronda == llave_alta.total_rondas)
