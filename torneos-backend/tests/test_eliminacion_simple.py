"""Eliminación simple: siembra, byes y estructura de la llave."""

import pytest

from app.domain.formatos import eliminacion_simple as es
from app.domain.formatos.base import ErrorFormato, TipoFuente

# Ids de equipo separados de los seeds a propósito: si el generador confundiera
# "posición de siembra" con "id de equipo", con ids 1..N el test pasaría igual.
IDS = [101, 102, 103, 104, 105, 106, 107, 108]


class TestOrdenSiembra:
    def test_ocho_equipos_da_el_orden_estandar(self):
        assert es.orden_siembra(8) == [1, 8, 4, 5, 2, 7, 3, 6]

    @pytest.mark.parametrize("tamano", [1, 2, 4, 8, 16, 32, 64])
    def test_es_una_permutacion_sin_huecos(self, tamano):
        assert sorted(es.orden_siembra(tamano)) == list(range(1, tamano + 1))

    @pytest.mark.parametrize("tamano", [4, 8, 16, 32, 64])
    def test_los_dos_mejores_solo_pueden_cruzarse_en_la_final(self, tamano):
        """El 1 y el 2 tienen que caer en mitades opuestas del cuadro. Es la
        propiedad que justifica sembrar: si se cruzan antes, la siembra no
        sirvió de nada."""
        orden = es.orden_siembra(tamano)
        mitad = tamano // 2
        assert orden.index(1) < mitad, "el seed 1 debería estar en la mitad de arriba"
        assert orden.index(2) >= mitad, "el seed 2 debería estar en la mitad de abajo"

    @pytest.mark.parametrize("tamano", [8, 16, 32])
    def test_el_1_y_el_3_no_se_cruzan_antes_de_semis(self, tamano):
        """Corolario del anterior un nivel más abajo: 1 y 3 comparten mitad
        pero no cuarto."""
        orden = es.orden_siembra(tamano)
        cuarto = tamano // 4
        assert orden.index(1) // cuarto != orden.index(3) // cuarto


class TestSiguientePotenciaDeDos:
    @pytest.mark.parametrize(
        "n,esperado", [(1, 1), (2, 2), (3, 4), (4, 4), (5, 8), (8, 8), (9, 16), (33, 64)]
    )
    def test_redondea_hacia_arriba(self, n, esperado):
        assert es.siguiente_potencia_de_dos(n) == esperado


class TestGenerar:
    def test_menos_de_dos_equipos_es_error(self):
        with pytest.raises(ErrorFormato, match="al menos 2"):
            es.generar([101])
        with pytest.raises(ErrorFormato):
            es.generar([])

    def test_ocho_equipos_arma_los_cruces_esperados(self):
        r = es.generar(IDS)
        ronda1 = [c for c in r.cruces if c.ronda == 1]
        cruces = [(c.fuente_a.valor, c.fuente_b.valor) for c in ronda1]
        # orden de siembra [1,8,4,5,2,7,3,6] sobre los ids 101..108
        assert cruces == [(101, 108), (104, 105), (102, 107), (103, 106)]
        assert r.total_rondas == 3
        assert not any(c.es_bye for c in ronda1)

    @pytest.mark.parametrize("n", range(2, 65))
    def test_el_total_de_cruces_cierra_para_cualquier_n(self, n):
        """Una llave de eliminación simple sobre un cuadro de T posiciones
        tiene siempre T-1 cruces, con o sin byes."""
        r = es.generar(list(range(101, 101 + n)))
        tamano = es.siguiente_potencia_de_dos(n)
        assert len(r.cruces) == tamano - 1

    @pytest.mark.parametrize("n", range(2, 65))
    def test_cada_equipo_entra_exactamente_una_vez(self, n):
        equipos = list(range(101, 101 + n))
        r = es.generar(equipos)
        colocados = [
            f.valor
            for c in r.cruces
            for f in (c.fuente_a, c.fuente_b)
            if f.tipo == TipoFuente.EQUIPO
        ]
        assert sorted(colocados) == equipos

    @pytest.mark.parametrize("n", range(2, 65))
    def test_la_cantidad_de_byes_es_la_que_falta_para_llenar_el_cuadro(self, n):
        r = es.generar(list(range(101, 101 + n)))
        tamano = es.siguiente_potencia_de_dos(n)
        byes = [c for c in r.cruces if c.es_bye]
        assert len(byes) == tamano - n

    @pytest.mark.parametrize("n", range(2, 65))
    def test_nunca_se_enfrentan_dos_huecos(self, n):
        """Un cruce hueco-contra-hueco sería una partida que nadie puede
        jugar y que igual tiene que avanzar a alguien."""
        r = es.generar(list(range(101, 101 + n)))
        for c in r.cruces:
            vacios = [
                f for f in (c.fuente_a, c.fuente_b) if f.tipo == TipoFuente.VACIO
            ]
            assert len(vacios) <= 1, f"cruce {c.indice} tiene dos huecos"

    def test_los_byes_van_a_los_mejores_sembrados(self):
        """Con 5 equipos en un cuadro de 8 sobran 3 lugares: el descanso le
        toca a los seeds 1, 2 y 3, no a cualquiera."""
        r = es.generar([101, 102, 103, 104, 105])
        con_bye = {
            f.valor
            for c in r.cruces
            if c.es_bye
            for f in (c.fuente_a, c.fuente_b)
            if f.tipo == TipoFuente.EQUIPO
        }
        assert con_bye == {101, 102, 103}

    @pytest.mark.parametrize("n", range(2, 65))
    def test_los_avances_apuntan_siempre_a_un_cruce_anterior(self, n):
        """Invariante de resolubilidad: si un cruce dependiera del ganador de
        uno posterior, la llave no se podría jugar en orden."""
        r = es.generar(list(range(101, 101 + n)))
        indices = {c.indice for c in r.cruces}
        for c in r.cruces:
            for f in (c.fuente_a, c.fuente_b):
                if f.tipo == TipoFuente.GANADOR_DE:
                    assert f.valor in indices, "referencia a un cruce inexistente"
                    assert f.valor < c.indice, (
                        f"el cruce {c.indice} depende del {f.valor}, que va después"
                    )

    @pytest.mark.parametrize("n", range(2, 65))
    def test_cada_cruce_alimenta_a_lo_sumo_un_cruce_siguiente(self, n):
        """Nadie puede avanzar a dos lugares distintos del cuadro."""
        r = es.generar(list(range(101, 101 + n)))
        destinos: dict[int, int] = {}
        for c in r.cruces:
            for f in (c.fuente_a, c.fuente_b):
                if f.tipo == TipoFuente.GANADOR_DE:
                    destinos[f.valor] = destinos.get(f.valor, 0) + 1
        assert all(v == 1 for v in destinos.values())

    @pytest.mark.parametrize("n", range(2, 65))
    def test_hay_exactamente_una_final(self, n):
        r = es.generar(list(range(101, 101 + n)))
        finales = [c for c in r.cruces if c.ronda == r.total_rondas]
        assert len(finales) == 1
