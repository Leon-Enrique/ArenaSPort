"""Ciclo de vida de una partida: BO por ronda, validación de marcador y
resolución del check-in."""

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.partidas import (
    CHECKIN_MINUTOS_ANTES,
    ErrorPartida,
    ResultadoCheckin,
    bo_para_ronda,
    debe_auto_abrir_checkin,
    evaluar_checkin,
    validar_marcador,
)

AHORA = datetime(2026, 8, 21, 20, 0, tzinfo=UTC)


class TestBoPorRonda:
    def test_sin_config_es_bo1(self):
        assert bo_para_ronda(None, None) == 1
        assert bo_para_ronda({}, 1) == 1

    def test_usa_el_bo_base(self):
        assert bo_para_ronda({"bo": 3}, 1) == 3

    def test_sin_ronda_devuelve_el_base(self):
        assert bo_para_ronda({"bo": 3, "bo_por_ronda": [{"ronda": 4, "bo": 5}]}, None) == 3

    def test_escala_por_tramos(self):
        """BO1 hasta la ronda 3, BO3 desde la 4, BO5 desde la 6."""
        config = {
            "bo": 1,
            "bo_por_ronda": [{"ronda": 4, "bo": 3}, {"ronda": 6, "bo": 5}],
        }
        assert bo_para_ronda(config, 1) == 1
        assert bo_para_ronda(config, 3) == 1
        assert bo_para_ronda(config, 4) == 3
        assert bo_para_ronda(config, 5) == 3
        assert bo_para_ronda(config, 6) == 5
        assert bo_para_ronda(config, 9) == 5

    def test_gana_el_tramo_mas_alto_aplicable(self):
        config = {"bo": 1, "bo_por_ronda": [{"ronda": 2, "bo": 3}, {"ronda": 5, "bo": 5}]}
        assert bo_para_ronda(config, 4) == 3

    def test_ignora_tramos_incompletos(self):
        config = {"bo": 3, "bo_por_ronda": [{"ronda": None, "bo": 5}, {"bo": 7}]}
        assert bo_para_ronda(config, 9) == 3


class TestValidarMarcador:
    @pytest.mark.parametrize(
        "bo,propio,rival",
        [
            (1, 1, 0), (1, 0, 1),
            (3, 2, 0), (3, 2, 1), (3, 0, 2), (3, 1, 2),
            (5, 3, 0), (5, 3, 1), (5, 3, 2), (5, 2, 3),
        ],
    )
    def test_acepta_marcadores_posibles(self, bo, propio, rival):
        r = validar_marcador(bo, propio, rival)
        assert r.gana_reportante == (propio > rival)

    def test_rechaza_el_empate(self):
        with pytest.raises(ErrorPartida, match="empate"):
            validar_marcador(3, 1, 1)

    def test_rechaza_negativos(self):
        with pytest.raises(ErrorPartida, match="negativo"):
            validar_marcador(3, -1, 2)

    def test_rechaza_si_nadie_llego_a_ganar(self):
        with pytest.raises(ErrorPartida, match="hace falta llegar a 2"):
            validar_marcador(3, 1, 0)

    def test_rechaza_si_se_pasa_del_formato(self):
        with pytest.raises(ErrorPartida, match="supera el formato"):
            validar_marcador(3, 3, 1)

    @pytest.mark.parametrize(
        "bo,propio,rival",
        [
            (3, 3, 0),   # un BO3 termina en el 2do mapa ganado: no hay 3er mapa
            (5, 4, 1),   # un BO5 termina en el 3ro
            (5, 5, 0),
            (1, 2, 0),
        ],
    )
    def test_rechaza_marcadores_imposibles_para_el_formato(self, bo, propio, rival):
        """La serie se corta apenas alguien llega a los mapas necesarios, así
        que el ganador no puede tener MÁS que eso. Un 5-0 en un BO5 no es un
        resultado apretado ni holgado: no existe.

        No es cosmético: `mapas_favor` alimenta la diferencia de mapas, que
        es criterio de desempate en la tabla — un marcador inflado corre a
        un equipo de puesto y puede cambiar quién clasifica.
        """
        with pytest.raises(ErrorPartida):
            validar_marcador(bo, propio, rival)


class TestAutoAbrirCheckin:
    def test_sin_horario_no_abre_solo(self):
        assert debe_auto_abrir_checkin(None, AHORA) is False

    def test_abre_en_la_ventana_previa(self):
        programada = AHORA + timedelta(minutes=CHECKIN_MINUTOS_ANTES - 1)
        assert debe_auto_abrir_checkin(programada, AHORA) is True

    def test_justo_en_el_limite_abre(self):
        programada = AHORA + timedelta(minutes=CHECKIN_MINUTOS_ANTES)
        assert debe_auto_abrir_checkin(programada, AHORA) is True

    def test_todavia_falta_mucho(self):
        programada = AHORA + timedelta(hours=3)
        assert debe_auto_abrir_checkin(programada, AHORA) is False

    def test_una_partida_pasada_tambien_abre(self):
        programada = AHORA - timedelta(hours=1)
        assert debe_auto_abrir_checkin(programada, AHORA) is True


class TestEvaluarCheckin:
    def test_todos_confirmaron(self):
        r = evaluar_checkin({101: AHORA, 102: AHORA}, AHORA + timedelta(minutes=10), AHORA)
        assert r.resultado == ResultadoCheckin.TODOS_LISTOS

    def test_todos_confirmaron_aunque_haya_vencido(self):
        """Si están los dos, no importa que el reloj haya pasado."""
        r = evaluar_checkin({101: AHORA, 102: AHORA}, AHORA - timedelta(minutes=1), AHORA)
        assert r.resultado == ResultadoCheckin.TODOS_LISTOS

    def test_falta_alguien_pero_hay_tiempo(self):
        r = evaluar_checkin({101: AHORA, 102: None}, AHORA + timedelta(minutes=10), AHORA)
        assert r.resultado == ResultadoCheckin.EN_ESPERA
        assert r.equipo_ganador_id is None

    def test_walkover_para_el_que_se_presento(self):
        r = evaluar_checkin({101: AHORA, 102: None}, AHORA - timedelta(minutes=1), AHORA)
        assert r.resultado == ResultadoCheckin.WALKOVER
        assert r.equipo_ganador_id == 101

    def test_nadie_confirmo(self):
        """Sin nadie presente no hay a quién darle la victoria: la partida
        vuelve a programarse, no se resuelve sola."""
        r = evaluar_checkin({101: None, 102: None}, AHORA - timedelta(minutes=1), AHORA)
        assert r.resultado == ResultadoCheckin.NADIE_CONFIRMO
        assert r.equipo_ganador_id is None

    def test_multi_equipo_con_varios_presentes_no_declara_ganador(self):
        """En battle royale no hay un único ganador de walkover: los ausentes
        simplemente no puntúan esa caída."""
        confirmaciones = {101: AHORA, 102: AHORA, 103: None, 104: None}
        r = evaluar_checkin(confirmaciones, AHORA - timedelta(minutes=1), AHORA)
        assert r.resultado == ResultadoCheckin.WALKOVER
        assert r.equipo_ganador_id is None

    def test_sin_fecha_de_cierre_y_falta_alguien_resuelve_igual(self):
        r = evaluar_checkin({101: AHORA, 102: None}, None, AHORA)
        assert r.resultado == ResultadoCheckin.WALKOVER
        assert r.equipo_ganador_id == 101
