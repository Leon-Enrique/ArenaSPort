"""Sistema suizo: siembra de la ronda 1, emparejamiento por récord y el
corte tipo MPL/M7 (N victorias clasifica, N derrotas elimina)."""

import pytest

from app.domain.formatos import suizo
from app.domain.formatos.base import ErrorFormato

IDS8 = [101, 102, 103, 104, 105, 106, 107, 108]


def tabla(*filas) -> list[suizo.EquipoConPuntaje]:
    """(equipo_id, puntos, victorias, derrotas) -> lista de EquipoConPuntaje."""
    return [
        suizo.EquipoConPuntaje(equipo_id=e, puntos=p, victorias=v, derrotas=d)
        for e, p, v, d in filas
    ]


class TestRondaUno:
    def test_mitad_superior_contra_mitad_inferior(self):
        pares, bye = suizo.generar_ronda_1(IDS8)
        assert pares == [(101, 105), (102, 106), (103, 107), (104, 108)]
        assert bye is None

    def test_cantidad_impar_le_da_el_bye_al_peor_sembrado(self):
        """Dárselo al mejor sembrado sería regalarle una victoria al que ya
        venía mejor: el estándar es que descanse el último."""
        pares, bye = suizo.generar_ronda_1([101, 102, 103, 104, 105, 106, 107])
        assert bye == 107
        assert pares == [(101, 104), (102, 105), (103, 106)]

    @pytest.mark.parametrize("n", range(2, 33))
    def test_nadie_queda_afuera_ni_repetido(self, n):
        equipos = list(range(101, 101 + n))
        pares, bye = suizo.generar_ronda_1(equipos)
        vistos = [e for par in pares for e in par]
        if bye is not None:
            vistos.append(bye)
        assert sorted(vistos) == equipos

    @pytest.mark.parametrize("n", range(2, 33))
    def test_el_bye_aparece_solo_con_cantidad_impar(self, n):
        _, bye = suizo.generar_ronda_1(list(range(101, 101 + n)))
        assert (bye is not None) == (n % 2 != 0)

    def test_menos_de_dos_equipos_es_error(self):
        with pytest.raises(ErrorFormato, match="al menos 2"):
            suizo.generar_ronda_1([101])


class TestSiguienteRonda:
    def test_empareja_por_puntaje_cercano(self):
        t = tabla((101, 9, 3, 0), (102, 9, 3, 0), (103, 3, 1, 2), (104, 3, 1, 2))
        pares = suizo.generar_siguiente_ronda(t, set())
        assert pares == [(101, 102), (103, 104)]

    def test_evita_repetir_un_cruce_ya_jugado(self):
        """Si el emparejamiento natural ya se jugó, busca el siguiente
        compatible en vez de repetir."""
        t = tabla((101, 9, 3, 0), (102, 9, 3, 0), (103, 6, 2, 1), (104, 6, 2, 1))
        previos = {(101, 102)}
        pares = suizo.generar_siguiente_ronda(t, previos)
        cruces = {(min(a, b), max(a, b)) for a, b in pares}
        assert (101, 102) not in cruces
        assert cruces == {(101, 103), (102, 104)}

    def test_si_no_queda_ningun_rival_nuevo_permite_repetir(self):
        """Última ronda con pocos equipos: mejor un rival repetido que un
        equipo sin partida."""
        t = tabla((101, 9, 3, 0), (102, 9, 3, 0))
        pares = suizo.generar_siguiente_ronda(t, {(101, 102)})
        assert pares == [(101, 102)]

    @pytest.mark.parametrize("n", range(2, 21))
    def test_nadie_juega_dos_veces_en_la_misma_ronda(self, n):
        t = tabla(*[(100 + i, (n - i) * 3, n - i, i) for i in range(1, n + 1)])
        pares = suizo.generar_siguiente_ronda(t, set())
        vistos = [e for par in pares for e in par]
        assert len(vistos) == len(set(vistos))

    @pytest.mark.parametrize("n", range(2, 21))
    def test_queda_libre_como_mucho_uno(self, n):
        t = tabla(*[(100 + i, (n - i) * 3, n - i, i) for i in range(1, n + 1)])
        pares = suizo.generar_siguiente_ronda(t, set())
        emparejados = {e for par in pares for e in par}
        assert len(t) - len(emparejados) == n % 2

    def test_nadie_se_enfrenta_a_si_mismo(self):
        t = tabla(*[(100 + i, 0, 0, 0) for i in range(1, 12)])
        pares = suizo.generar_siguiente_ronda(t, set())
        assert all(a != b for a, b in pares)


class TestCorteMplM7:
    """Suizo con meta: 3 victorias clasifica y deja de jugar, 3 derrotas
    elimina. Es el formato de la MPL/M7."""

    def test_los_clasificados_salen_de_la_ronda(self):
        t = tabla((101, 9, 3, 0), (102, 6, 2, 1), (103, 6, 2, 1), (104, 3, 1, 2))
        pares = suizo.generar_siguiente_ronda(t, set(), meta_victorias=3, meta_derrotas=3)
        involucrados = {e for par in pares for e in par}
        assert 101 not in involucrados, "el que ya clasificó no debería seguir jugando"

    def test_los_eliminados_salen_de_la_ronda(self):
        t = tabla((101, 6, 2, 1), (102, 6, 2, 1), (103, 3, 1, 2), (104, 0, 0, 3))
        pares = suizo.generar_siguiente_ronda(t, set(), meta_victorias=3, meta_derrotas=3)
        involucrados = {e for par in pares for e in par}
        assert 104 not in involucrados, "el eliminado no debería seguir jugando"

    def test_empareja_por_record_exacto(self):
        """El 1-0 juega contra el 1-0 y el 0-1 contra el 0-1, que es lo que
        define al formato."""
        t = tabla(
            (101, 3, 1, 0), (102, 3, 1, 0),
            (103, 0, 0, 1), (104, 0, 0, 1),
        )
        pares = suizo.generar_siguiente_ronda(t, set(), meta_victorias=3, meta_derrotas=3)
        cruces = {(min(a, b), max(a, b)) for a, b in pares}
        assert cruces == {(101, 102), (103, 104)}


class TestEquipoLibre:
    def test_le_toca_al_de_peor_record(self):
        t = tabla((101, 9, 3, 0), (102, 6, 2, 1), (103, 0, 0, 3))
        assert suizo.equipo_libre(t, ya_emparejados={101, 102}) == 103

    def test_no_elige_a_alguien_ya_emparejado(self):
        t = tabla((101, 9, 3, 0), (102, 6, 2, 1), (103, 0, 0, 3))
        libre = suizo.equipo_libre(t, ya_emparejados={103})
        assert libre != 103

    def test_devuelve_none_si_estan_todos_emparejados(self):
        t = tabla((101, 9, 3, 0), (102, 6, 2, 1))
        assert suizo.equipo_libre(t, ya_emparejados={101, 102}) is None

    def test_ignora_a_los_que_ya_llegaron_al_corte(self):
        t = tabla((101, 9, 3, 0), (102, 0, 0, 3), (103, 3, 1, 1))
        libre = suizo.equipo_libre(t, set(), meta_victorias=3, meta_derrotas=3)
        assert libre == 103
