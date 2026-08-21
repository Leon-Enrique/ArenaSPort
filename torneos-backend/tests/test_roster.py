"""Reglas de roster: tamaño, identidad, suplentes y capitán.

Las reglas de suplente y capitán son "amables a propósito": en vez de
rechazar un formulario incompleto, el sistema asume lo razonable y avisa
qué asumió. Los tests cubren tanto lo que asume como el aviso, porque el
aviso es lo que le permite al equipo corregir.
"""

import pytest

from app.domain.roster import (
    ConfigJuego,
    ErrorRoster,
    JugadorEntrada,
    construir_clave_identidad,
    normalizar_roster,
)

MLBB = ConfigJuego(
    titulares_requeridos=5,
    suplentes_maximos=2,
    campos_requeridos=["nick", "id_juego", "server"],
    campos_clave=["id_juego", "server"],
)


def jugador(nick, id_juego=None, server="2001", **kwargs) -> JugadorEntrada:
    return JugadorEntrada(
        identidad={
            "nick": nick,
            "id_juego": id_juego or f"id-{nick}",
            "server": server,
        },
        **kwargs,
    )


def roster(cantidad: int, **kwargs) -> list[JugadorEntrada]:
    return [jugador(f"j{i}", **kwargs) for i in range(1, cantidad + 1)]


class TestClaveIdentidad:
    def test_une_los_campos_clave(self):
        clave = construir_clave_identidad(
            {"nick": "Lyon", "id_juego": "123456", "server": "2251"},
            ["id_juego", "server"],
        )
        assert clave == "123456|2251"

    def test_normaliza_mayusculas_y_espacios(self):
        """Los capitanes escriben el mismo ID de mil formas: si no se
        normaliza, el índice de elegibilidad no detecta al repetido."""
        a = construir_clave_identidad({"id_juego": " ABC123 ", "server": "2251"}, ["id_juego", "server"])
        b = construir_clave_identidad({"id_juego": "abc123", "server": "2251"}, ["id_juego", "server"])
        assert a == b == "abc123|2251"

    def test_campo_clave_vacio_es_error(self):
        with pytest.raises(ErrorRoster, match="obligatorio"):
            construir_clave_identidad({"id_juego": "", "server": "2251"}, ["id_juego", "server"])


class TestTamano:
    def test_acepta_el_minimo_exacto(self):
        r = normalizar_roster(roster(5), MLBB)
        assert len(r.jugadores) == 5
        assert all(not j.es_suplente for j in r.jugadores)

    def test_acepta_el_maximo(self):
        r = normalizar_roster(roster(7), MLBB)
        assert len(r.jugadores) == 7

    def test_rechaza_equipo_incompleto(self):
        with pytest.raises(ErrorRoster, match="se requieren al menos 5"):
            normalizar_roster(roster(4), MLBB)

    def test_rechaza_equipo_pasado_de_jugadores(self):
        with pytest.raises(ErrorRoster, match="el máximo es 7"):
            normalizar_roster(roster(8), MLBB)


class TestCamposObligatorios:
    def test_rechaza_si_falta_un_campo(self):
        entradas = roster(5)
        entradas[2].identidad["server"] = ""
        with pytest.raises(ErrorRoster, match="jugador #3"):
            normalizar_roster(entradas, MLBB)

    def test_el_error_nombra_todos_los_campos_faltantes(self):
        entradas = roster(5)
        entradas[0].identidad["nick"] = ""
        entradas[0].identidad["server"] = "   "
        with pytest.raises(ErrorRoster, match="nick, server"):
            normalizar_roster(entradas, MLBB)

    def test_rechaza_jugadores_repetidos_en_el_mismo_equipo(self):
        entradas = roster(5)
        entradas[4].identidad["id_juego"] = entradas[0].identidad["id_juego"]
        with pytest.raises(ErrorRoster, match="repetidos"):
            normalizar_roster(entradas, MLBB)


class TestSuplentes:
    def test_si_nadie_marca_se_asignan_los_ultimos(self):
        r = normalizar_roster(roster(7), MLBB)
        assert [j.es_suplente for j in r.jugadores] == [False] * 5 + [True] * 2
        assert any("no marcó suplentes" in a for a in r.avisos)

    def test_sin_sobrantes_no_hay_suplentes_ni_aviso(self):
        r = normalizar_roster(roster(5), MLBB)
        assert not any(j.es_suplente for j in r.jugadores)
        assert not any("suplentes" in a for a in r.avisos)

    def test_respeta_los_suplentes_marcados_a_mano(self):
        entradas = roster(7)
        entradas[0].es_suplente = True
        entradas[1].es_suplente = True
        for e in entradas[2:]:
            e.es_suplente = False
        r = normalizar_roster(entradas, MLBB)
        assert [j.es_suplente for j in r.jugadores] == [True, True] + [False] * 5

    def test_rechaza_si_quedan_mal_los_titulares(self):
        entradas = roster(7)
        entradas[0].es_suplente = True
        for e in entradas[1:]:
            e.es_suplente = False
        with pytest.raises(ErrorRoster, match="Quedan 6 titulares"):
            normalizar_roster(entradas, MLBB)


class TestCapitan:
    def test_respeta_al_marcado_explicitamente(self):
        entradas = roster(5)
        entradas[2].es_capitan = True
        r = normalizar_roster(entradas, MLBB)
        assert [j.es_capitan for j in r.jugadores] == [False, False, True, False, False]

    def test_lo_busca_por_nick_declarado(self):
        r = normalizar_roster(roster(5), MLBB, capitan_declarado="j3")
        assert r.jugadores[2].es_capitan
        assert r.avisos == []

    def test_el_nick_declarado_no_distingue_mayusculas(self):
        r = normalizar_roster(roster(5), MLBB, capitan_declarado="  J3  ")
        assert r.jugadores[2].es_capitan

    def test_si_el_declarado_no_coincide_toma_al_primero_y_avisa(self):
        """Caso típico: el equipo pone el nombre real de la persona, no su
        nick del juego."""
        r = normalizar_roster(roster(5), MLBB, capitan_declarado="Juan Pérez")
        assert r.jugadores[0].es_capitan
        assert any("no coincide con ningún nick" in a for a in r.avisos)

    def test_sin_capitan_toma_al_primero_y_avisa(self):
        r = normalizar_roster(roster(5), MLBB)
        assert r.jugadores[0].es_capitan
        assert any("No se indicó capitán" in a for a in r.avisos)

    def test_hay_siempre_exactamente_un_capitan(self):
        for cantidad in (5, 6, 7):
            r = normalizar_roster(roster(cantidad), MLBB)
            assert sum(j.es_capitan for j in r.jugadores) == 1

    def test_avisa_si_el_capitan_quedo_de_suplente(self):
        entradas = roster(7)
        entradas[6].es_capitan = True  # el último, que cae en la zona de suplentes
        r = normalizar_roster(entradas, MLBB)
        assert r.jugadores[6].es_capitan and r.jugadores[6].es_suplente
        assert any("capitán quedó marcado como suplente" in a for a in r.avisos)


class TestSalida:
    def test_conserva_el_orden_de_carga(self):
        r = normalizar_roster(roster(6), MLBB)
        assert [j.orden for j in r.jugadores] == [0, 1, 2, 3, 4, 5]
        assert [j.identidad["nick"] for j in r.jugadores] == ["j1", "j2", "j3", "j4", "j5", "j6"]

    def test_arrastra_el_discord_id(self):
        entradas = roster(5)
        entradas[1].discord_id = "999888777"
        r = normalizar_roster(entradas, MLBB)
        assert r.jugadores[1].discord_id == "999888777"
        assert r.jugadores[0].discord_id is None

    def test_calcula_la_clave_de_cada_jugador(self):
        r = normalizar_roster(roster(5), MLBB)
        assert r.jugadores[0].clave_identidad == "id-j1|2001"
