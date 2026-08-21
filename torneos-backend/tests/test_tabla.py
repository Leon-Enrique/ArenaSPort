"""Tabla de posiciones y desempates.

El caso que más importa acá es `enfrentamiento_directo`: se resuelve como
mini-grupo entre los empatados y se aplica ANTES que la diferencia de mapas.
Es la regla que el módulo señala como la que más se rompe en
implementaciones caseras, así que los tests la atacan de frente.
"""

import pytest

from app.domain.tabla import (
    FilaTabla,
    PartidaParaTabla,
    calcular_tabla,
    clasificados_ordenados,
)

A, B, C, D = 101, 102, 103, 104


def p(a, b, ma, mb) -> PartidaParaTabla:
    return PartidaParaTabla(equipo_a_id=a, equipo_b_id=b, mapas_a=ma, mapas_b=mb)


def posiciones(filas) -> list[int]:
    return [f.equipo_id for f in filas]


class TestConteoBasico:
    def test_una_victoria_suma_tres_puntos(self):
        filas = calcular_tabla([A, B], [p(A, B, 2, 0)])
        por_id = {f.equipo_id: f for f in filas}
        assert por_id[A].puntos == 3
        assert por_id[A].victorias == 1
        assert por_id[B].derrotas == 1
        assert por_id[B].puntos == 0

    def test_cuenta_mapas_a_favor_y_en_contra(self):
        filas = calcular_tabla([A, B], [p(A, B, 2, 1)])
        por_id = {f.equipo_id: f for f in filas}
        assert (por_id[A].mapas_favor, por_id[A].mapas_contra) == (2, 1)
        assert (por_id[B].mapas_favor, por_id[B].mapas_contra) == (1, 2)
        assert por_id[A].diferencia_mapas == 1
        assert por_id[B].diferencia_mapas == -1

    def test_el_empate_suma_a_los_dos(self):
        filas = calcular_tabla([A, B], [p(A, B, 1, 1)])
        assert all(f.puntos == 1 and f.empates == 1 for f in filas)

    def test_los_equipos_sin_jugar_igual_aparecen(self):
        """Un equipo que todavía no jugó tiene que estar en la tabla en cero,
        no desaparecer hasta su primera partida."""
        filas = calcular_tabla([A, B, C], [p(A, B, 2, 0)])
        assert len(filas) == 3
        sin_jugar = next(f for f in filas if f.equipo_id == C)
        assert (sin_jugar.jugados, sin_jugar.puntos) == (0, 0)

    def test_ignora_partidas_de_equipos_de_otro_grupo(self):
        """calcular_tabla se llama por grupo: una partida cuyo rival no está
        en la lista no puede contaminar este grupo."""
        filas = calcular_tabla([A, B], [p(A, B, 2, 0), p(A, C, 2, 0)])
        por_id = {f.equipo_id: f for f in filas}
        assert por_id[A].jugados == 1

    def test_asigna_posiciones_consecutivas_desde_uno(self):
        filas = calcular_tabla([A, B, C], [p(A, B, 2, 0), p(A, C, 2, 0), p(B, C, 2, 0)])
        assert [f.posicion for f in filas] == [1, 2, 3]

    def test_el_sistema_de_puntaje_es_configurable(self):
        filas = calcular_tabla(
            [A, B], [p(A, B, 2, 0)], sistema_puntaje={"victoria": 10, "derrota": -1}
        )
        por_id = {f.equipo_id: f for f in filas}
        assert por_id[A].puntos == 10
        assert por_id[B].puntos == -1


class TestEnfrentamientoDirecto:
    """El escenario armado a propósito: A y B empatan en puntos, A tiene
    MEJOR diferencia de mapas, pero B le ganó en el mano a mano.

    Con el orden de criterios por defecto gana B. Si alguien reordenara los
    criterios o comparara mal, A subiría a la punta y este test lo caza.
    """

    PARTIDAS = [
        p(A, C, 2, 0),   # A: +2
        p(A, D, 2, 0),   # A: +2
        p(B, A, 2, 1),   # B le gana a A por poco
        p(B, D, 2, 1),
        p(C, B, 2, 0),   # C le gana a B
        p(D, C, 2, 0),
    ]

    def test_el_mano_a_mano_manda_sobre_la_diferencia_de_mapas(self):
        filas = calcular_tabla([A, B, C, D], self.PARTIDAS)
        por_id = {f.equipo_id: f for f in filas}

        # Punto de partida: empatados en puntos, con A mejor en diferencia.
        assert por_id[A].puntos == por_id[B].puntos == 6
        assert por_id[A].diferencia_mapas == 3
        assert por_id[B].diferencia_mapas == 0

        # Y aun así B queda arriba, porque le ganó a A.
        assert posiciones(filas) == [B, A, D, C]

    def test_sin_el_criterio_gana_la_diferencia_de_mapas(self):
        """El mismo torneo con otros criterios da vuelta el podio: prueba
        que el orden configurado se respeta de verdad y no está fijo en el
        código."""
        filas = calcular_tabla(
            [A, B, C, D], self.PARTIDAS, criterios_desempate=["puntos", "diferencia_mapas"]
        )
        assert posiciones(filas)[:2] == [A, B]

    def test_se_calcula_solo_entre_los_empatados(self):
        """El mini-grupo mira únicamente los partidos entre los equipos del
        bloque empatado — los resultados contra el resto ya se contaron en
        los puntos y no se pueden contar dos veces."""
        filas = calcular_tabla([A, B, C, D], self.PARTIDAS)
        # C le ganó a B, pero eso no rescata a C del último puesto: contra
        # D (su verdadero rival de bloque, empatados en 3) perdió.
        assert posiciones(filas)[-2:] == [D, C]

    def test_un_criterio_desconocido_se_saltea_sin_romper(self):
        filas = calcular_tabla(
            [A, B], [p(A, B, 2, 0)], criterios_desempate=["inventado", "puntos"]
        )
        assert posiciones(filas) == [A, B]


class TestClasificados:
    def test_ordena_primeros_de_cada_grupo_antes_que_los_segundos(self):
        """Los 1° de cada grupo primero, después los 2°. Así el 1° y el 2°
        del mismo grupo no pueden cruzarse en la primera ronda de la fase
        siguiente."""
        tablas = {
            0: [FilaTabla(equipo_id=11), FilaTabla(equipo_id=12), FilaTabla(equipo_id=13)],
            1: [FilaTabla(equipo_id=21), FilaTabla(equipo_id=22), FilaTabla(equipo_id=23)],
        }
        assert clasificados_ordenados(tablas, cupos_por_grupo=2) == [11, 21, 12, 22]

    def test_un_cupo_por_grupo(self):
        tablas = {
            0: [FilaTabla(equipo_id=11), FilaTabla(equipo_id=12)],
            1: [FilaTabla(equipo_id=21), FilaTabla(equipo_id=22)],
        }
        assert clasificados_ordenados(tablas, cupos_por_grupo=1) == [11, 21]

    def test_grupo_unico_sin_numero(self):
        tablas = {None: [FilaTabla(equipo_id=11), FilaTabla(equipo_id=12)]}
        assert clasificados_ordenados(tablas, cupos_por_grupo=2) == [11, 12]

    def test_no_falla_si_un_grupo_tiene_menos_equipos_que_cupos(self):
        tablas = {
            0: [FilaTabla(equipo_id=11)],
            1: [FilaTabla(equipo_id=21), FilaTabla(equipo_id=22)],
        }
        assert clasificados_ordenados(tablas, cupos_por_grupo=2) == [11, 21, 22]
