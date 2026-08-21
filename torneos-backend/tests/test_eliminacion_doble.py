"""Eliminación doble: llave alta + baja + gran final.

Es el formato con más superficie para equivocarse, y el más caro de
depurar a mano una vez que el torneo arrancó: un perdedor que no cae a
ningún lado, o un cruce que nunca se puede jugar, recién se nota cuando
hay equipos esperando. Por eso acá pesan más los invariantes estructurales
sobre todo n que los casos puntuales.
"""

import pytest

from app.domain.formatos import eliminacion_doble as ed
from app.domain.formatos import eliminacion_simple as es
from app.domain.formatos.base import ErrorFormato, TipoFuente

TODOS_LOS_N = list(range(3, 65))


def _referencias(cruces, tipo):
    return [f.valor for c in cruces for f in (c.fuente_a, c.fuente_b) if f.tipo == tipo]


class TestValidaciones:
    @pytest.mark.parametrize("n", [0, 1, 2])
    def test_necesita_al_menos_tres_equipos(self, n):
        with pytest.raises(ErrorFormato, match="al menos 3"):
            ed.generar(list(range(101, 101 + n)))


class TestEstructura:
    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_las_partidas_jugables_son_2n_menos_2(self, n):
        """Cada equipo salvo el campeón tiene que perder dos veces, y cada
        partida real produce exactamente una derrota: 2(n-1) derrotas
        necesarias = 2n-2 partidas.

        Cuenta solo los cruces JUGABLES. Los marcados `es_bye` son filas que
        se auto-resuelven sin que nadie juegue, así que no producen derrota y
        no entran en la cuenta — incluirlos rompe la igualdad para todo n que
        no sea potencia de 2 (ver el test de abajo).
        """
        r = ed.generar(list(range(101, 101 + n)))
        jugables = [c for c in r.cruces if not c.es_bye]
        assert len(jugables) == 2 * n - 2

    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_el_total_de_cruces_incluye_los_byes(self, n):
        """El total de filas generadas (jugables + byes) es n + cuadro - 2,
        donde cuadro es la potencia de 2 que envuelve a n. Solo coincide con
        2n-2 cuando n ya es potencia de 2 y por lo tanto no hay byes."""
        r = ed.generar(list(range(101, 101 + n)))
        cuadro = es.siguiente_potencia_de_dos(n)
        assert len(r.cruces) == n + cuadro - 2

    @pytest.mark.parametrize("n", [4, 8, 16, 32, 64])
    def test_sin_byes_ambas_cuentas_coinciden(self, n):
        r = ed.generar(list(range(101, 101 + n)))
        assert len(r.cruces) == 2 * n - 2
        assert not any(c.es_bye for c in r.cruces)

    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_hay_exactamente_una_gran_final(self, n):
        r = ed.generar(list(range(101, 101 + n)))
        finales = [c for c in r.cruces if c.lado == "gran_final"]
        assert len(finales) == 1

    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_la_gran_final_cruza_al_campeon_de_cada_llave(self, n):
        r = ed.generar(list(range(101, 101 + n)))
        final = next(c for c in r.cruces if c.lado == "gran_final")
        # Ambos lados vienen de ganar algo; nadie entra sembrado a la final.
        assert final.fuente_a.tipo == TipoFuente.GANADOR_DE
        assert final.fuente_b.tipo == TipoFuente.GANADOR_DE
        assert final.fuente_a.valor != final.fuente_b.valor

    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_cada_equipo_entra_exactamente_una_vez(self, n):
        equipos = list(range(101, 101 + n))
        r = ed.generar(equipos)
        colocados = _referencias(r.cruces, TipoFuente.EQUIPO)
        assert sorted(colocados) == equipos

    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_los_equipos_solo_entran_por_la_llave_alta(self, n):
        """Nadie arranca en la llave baja: a la baja se llega perdiendo."""
        r = ed.generar(list(range(101, 101 + n)))
        for c in r.cruces:
            if c.lado != "alta":
                for f in (c.fuente_a, c.fuente_b):
                    assert f.tipo != TipoFuente.EQUIPO, (
                        f"un equipo entra directo a un cruce de lado '{c.lado}'"
                    )


class TestCaidaDeLosPerdedores:
    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_todo_perdedor_de_la_llave_alta_cae_en_algun_lado(self, n):
        """El invariante que más duele si se rompe: un equipo pierde su
        primera partida y no aparece en ninguna parte de la llave baja."""
        r = ed.generar(list(range(101, 101 + n)))
        cruces_alta_reales = {c.indice for c in r.cruces if c.lado == "alta" and not c.es_bye}
        caen = set(_referencias(r.cruces, TipoFuente.PERDEDOR_DE))
        assert cruces_alta_reales == caen

    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_ningun_perdedor_cae_en_dos_lugares(self, n):
        r = ed.generar(list(range(101, 101 + n)))
        caen = _referencias(r.cruces, TipoFuente.PERDEDOR_DE)
        assert len(caen) == len(set(caen))

    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_los_cruces_bye_no_generan_perdedor(self, n):
        """Un bye no se juega: no hay nadie que pueda caer de ahí a la baja."""
        r = ed.generar(list(range(101, 101 + n)))
        byes = {c.indice for c in r.cruces if c.es_bye}
        caen = set(_referencias(r.cruces, TipoFuente.PERDEDOR_DE))
        assert byes & caen == set()


class TestResolubilidad:
    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_todo_cruce_depende_solo_de_cruces_anteriores(self, n):
        """Sin esto la llave tendría un ciclo y no se podría jugar en ningún
        orden."""
        r = ed.generar(list(range(101, 101 + n)))
        indices = {c.indice for c in r.cruces}
        for c in r.cruces:
            for f in (c.fuente_a, c.fuente_b):
                if f.tipo in (TipoFuente.GANADOR_DE, TipoFuente.PERDEDOR_DE):
                    assert f.valor in indices
                    assert f.valor < c.indice, (
                        f"el cruce {c.indice} ({c.lado}) depende del {f.valor}, posterior"
                    )

    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_el_ganador_de_cada_cruce_avanza_a_lo_sumo_a_un_lugar(self, n):
        r = ed.generar(list(range(101, 101 + n)))
        destinos: dict[int, int] = {}
        for v in _referencias(r.cruces, TipoFuente.GANADOR_DE):
            destinos[v] = destinos.get(v, 0) + 1
        assert all(cant == 1 for cant in destinos.values())

    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_solo_la_gran_final_no_avanza_a_ningun_lado(self, n):
        """Todo cruce alimenta a otro, salvo el último. Si hubiera dos
        callejones sin salida, media llave no llevaría a ninguna parte."""
        r = ed.generar(list(range(101, 101 + n)))
        alimentan = set(_referencias(r.cruces, TipoFuente.GANADOR_DE))
        sin_salida = {c.indice for c in r.cruces} - alimentan
        final = next(c for c in r.cruces if c.lado == "gran_final")
        assert sin_salida == {final.indice}

    @pytest.mark.parametrize("n", TODOS_LOS_N)
    def test_ningun_cruce_se_enfrenta_a_si_mismo(self, n):
        r = ed.generar(list(range(101, 101 + n)))
        for c in r.cruces:
            assert (c.fuente_a.tipo, c.fuente_a.valor) != (c.fuente_b.tipo, c.fuente_b.valor)


class TestCasoConcreto:
    def test_cuatro_equipos(self):
        """El caso chico, verificable a mano: 4 equipos -> 6 cruces
        (2 de alta r1, 1 final de alta, 2 de baja, 1 gran final)."""
        r = ed.generar([101, 102, 103, 104])
        assert len(r.cruces) == 6
        por_lado: dict[str, int] = {}
        for c in r.cruces:
            por_lado[c.lado] = por_lado.get(c.lado, 0) + 1
        assert por_lado == {"alta": 3, "baja": 2, "gran_final": 1}
