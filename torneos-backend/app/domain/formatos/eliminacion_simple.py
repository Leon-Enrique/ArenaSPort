"""Eliminación simple: llave de N posiciones, byes para cualquier cantidad
de equipos.

Puro Python. `generar()` devuelve la estructura completa (todas las rondas);
la ronda 1 tiene equipos concretos, las siguientes solo referencias a
"el ganador del cruce X" — se completan cuando esos cruces resuelven.
"""

from app.domain.formatos.base import Cruce, ErrorFormato, Fuente, ResultadoGeneracion, TipoFuente


def orden_siembra(tamano: int) -> list[int]:
    """Orden de siembra estándar: separa a los mejores puestos lo más posible.

    tamano=8 -> [1,8,4,5,2,7,3,6]  (cruces 1v8, 4v5, 2v7, 3v6)
    Requiere que tamano sea potencia de 2.
    """
    if tamano == 1:
        return [1]
    mitad = orden_siembra(tamano // 2)
    resultado: list[int] = []
    for p in mitad:
        resultado.append(p)
        resultado.append(tamano + 1 - p)
    return resultado


def siguiente_potencia_de_dos(n: int) -> int:
    tamano = 1
    while tamano < n:
        tamano *= 2
    return tamano


def generar(
    equipos_seed: list[int], con_tercer_puesto: bool = False
) -> ResultadoGeneracion:
    """equipos_seed: ids de equipo en orden de siembra (mejor a peor).

    Devuelve la llave completa. Los cruces de ronda 1 que enfrentan a un
    equipo contra un hueco (bye) quedan marcados `es_bye=True` con
    `fuente_b` apuntando igual al equipo — el llamador los resuelve de
    inmediato sin esperar que se jueguen.
    """
    n = len(equipos_seed)
    if n < 2:
        raise ErrorFormato("Se necesitan al menos 2 equipos para una llave.")

    tamano = siguiente_potencia_de_dos(n)
    orden = orden_siembra(tamano)

    def equipo_de_seed(seed: int) -> int | None:
        return equipos_seed[seed - 1] if seed <= n else None

    cruces: list[Cruce] = []
    indice = 0

    # Ronda 1: slots concretos.
    inicio_ronda1 = 0
    partidos_r1 = tamano // 2
    for pos in range(partidos_r1):
        seed_a = orden[pos * 2]
        seed_b = orden[pos * 2 + 1]
        equipo_a = equipo_de_seed(seed_a)
        equipo_b = equipo_de_seed(seed_b)

        # Solo uno de los dos puede ser None: la siembra recursiva garantiza
        # que nunca se empareja un hueco contra otro hueco (los huecos son
        # siempre menos de la mitad del cuadro).
        es_bye = equipo_a is None or equipo_b is None
        cruces.append(
            Cruce(
                indice=indice,
                lado="unica",
                ronda=1,
                fuente_a=Fuente(TipoFuente.EQUIPO, equipo_a) if equipo_a else Fuente(TipoFuente.VACIO, 0),
                fuente_b=Fuente(TipoFuente.EQUIPO, equipo_b) if equipo_b else Fuente(TipoFuente.VACIO, 0),
                es_bye=es_bye,
            )
        )
        indice += 1

    # Rondas siguientes: referencian a los ganadores de la ronda anterior.
    inicio_ronda_anterior = inicio_ronda1
    partidos_ronda_anterior = partidos_r1
    ronda = 2
    while partidos_ronda_anterior > 1:
        partidos_esta_ronda = partidos_ronda_anterior // 2
        for pos in range(partidos_esta_ronda):
            idx_a = inicio_ronda_anterior + pos * 2
            idx_b = inicio_ronda_anterior + pos * 2 + 1
            cruces.append(
                Cruce(
                    indice=indice,
                    lado="unica",
                    ronda=ronda,
                    fuente_a=Fuente(TipoFuente.GANADOR_DE, idx_a),
                    fuente_b=Fuente(TipoFuente.GANADOR_DE, idx_b),
                )
            )
            indice += 1
        inicio_ronda_anterior += partidos_ronda_anterior
        partidos_ronda_anterior = partidos_esta_ronda
        ronda += 1

    total_rondas = ronda - 1

    # Partido por el tercer puesto: lo juegan los PERDEDORES de las dos
    # semifinales. Es la única partida de una llave simple que se alimenta de
    # perdedores, y por eso necesita `PERDEDOR_DE` — el mismo mecanismo que
    # usa la llave baja de eliminación doble.
    #
    # Va en la misma ronda que la final a propósito: se juega el mismo día y
    # ordenarlo después la dejaría "más lejos" que la final en cualquier
    # vista que ordene por ronda.
    #
    # Con menos de 4 equipos no hay semifinales de las que sacar perdedores,
    # así que simplemente no se crea.
    if con_tercer_puesto and total_rondas >= 2:
        semifinales = [c for c in cruces if c.ronda == total_rondas - 1]
        if len(semifinales) == 2:
            cruces.append(
                Cruce(
                    indice=indice,
                    lado="unica",
                    ronda=total_rondas,
                    fuente_a=Fuente(TipoFuente.PERDEDOR_DE, semifinales[0].indice),
                    fuente_b=Fuente(TipoFuente.PERDEDOR_DE, semifinales[1].indice),
                )
            )

    return ResultadoGeneracion(cruces=cruces, total_rondas=total_rondas)
