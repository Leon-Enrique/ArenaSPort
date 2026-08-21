"""Round robin: reparto en grupos y calendario todos-contra-todos."""

import pytest

from app.domain.formatos import round_robin as rr
from app.domain.formatos.base import ErrorFormato

IDS8 = [101, 102, 103, 104, 105, 106, 107, 108]


class TestDividirEnGrupos:
    def test_reparte_en_serpentina(self):
        """1° al grupo A, 2° al B, y de vuelta: el 3° va al B y el 4° al A.
        Reparte a los mejores sembrados en vez de amontonarlos."""
        grupos = rr.dividir_en_grupos(IDS8, 2)
        assert grupos == [[101, 104, 105, 108], [102, 103, 106, 107]]

    def test_tres_grupos(self):
        grupos = rr.dividir_en_grupos(list(range(1, 10)), 3)
        assert grupos == [[1, 6, 7], [2, 5, 8], [3, 4, 9]]

    @pytest.mark.parametrize("cantidad", [1, 2, 3, 4, 5, 6, 7, 8])
    def test_no_pierde_ni_repite_equipos(self, cantidad):
        grupos = rr.dividir_en_grupos(IDS8, cantidad)
        planos = [e for g in grupos for e in g]
        assert sorted(planos) == sorted(IDS8)

    @pytest.mark.parametrize("cantidad", [1, 2, 3, 4, 5, 6, 7, 8])
    def test_los_grupos_quedan_balanceados(self, cantidad):
        """Ningún grupo puede tener dos equipos más que otro."""
        grupos = rr.dividir_en_grupos(IDS8, cantidad)
        tamanos = [len(g) for g in grupos]
        assert max(tamanos) - min(tamanos) <= 1

    def test_un_solo_grupo_devuelve_todo_junto(self):
        assert rr.dividir_en_grupos(IDS8, 1) == [IDS8]

    def test_cero_grupos_es_error(self):
        with pytest.raises(ErrorFormato, match="al menos 1"):
            rr.dividir_en_grupos(IDS8, 0)

    def test_mas_grupos_que_equipos_es_error(self):
        with pytest.raises(ErrorFormato, match="más grupos que equipos"):
            rr.dividir_en_grupos([101, 102], 3)


class TestGenerarPartidosGrupo:
    def test_cuatro_equipos_juegan_seis_partidos(self):
        partidos = rr.generar_partidos_grupo([101, 102, 103, 104])
        assert len(partidos) == 6
        assert partidos == [
            (101, 102), (101, 103), (101, 104),
            (102, 103), (102, 104),
            (103, 104),
        ]

    @pytest.mark.parametrize("n", range(2, 17))
    def test_la_cantidad_es_la_combinatoria(self, n):
        equipos = list(range(101, 101 + n))
        partidos = rr.generar_partidos_grupo(equipos)
        assert len(partidos) == n * (n - 1) // 2

    @pytest.mark.parametrize("n", range(2, 17))
    def test_cada_par_juega_exactamente_una_vez(self, n):
        equipos = list(range(101, 101 + n))
        partidos = rr.generar_partidos_grupo(equipos)
        pares = {(min(a, b), max(a, b)) for a, b in partidos}
        assert len(pares) == len(partidos), "hay un cruce repetido"
        esperados = {
            (equipos[i], equipos[j])
            for i in range(n)
            for j in range(i + 1, n)
        }
        assert pares == esperados

    @pytest.mark.parametrize("n", range(2, 17))
    def test_nadie_juega_contra_si_mismo(self, n):
        partidos = rr.generar_partidos_grupo(list(range(101, 101 + n)))
        assert all(a != b for a, b in partidos)

    @pytest.mark.parametrize("n", range(2, 17))
    def test_todos_juegan_la_misma_cantidad(self, n):
        equipos = list(range(101, 101 + n))
        partidos = rr.generar_partidos_grupo(equipos)
        apariciones = {e: 0 for e in equipos}
        for a, b in partidos:
            apariciones[a] += 1
            apariciones[b] += 1
        assert set(apariciones.values()) == {n - 1}

    def test_un_grupo_de_uno_es_error(self):
        with pytest.raises(ErrorFormato, match="al menos 2"):
            rr.generar_partidos_grupo([101])
