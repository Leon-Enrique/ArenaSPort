"""Récord histórico de equipos.

Los dos casos que definen el significado del número que ve la gente son el
bye y el walkover: si se cuentan mal, dos equipos con el mismo desempeño real
terminan con récords distintos según cómo cayó el sorteo.
"""

import pytest

from app.domain.perfiles import (
    PartidaDeEquipo,
    Record,
    calcular_record,
    gano_la_final,
    resumir_por_edicion,
)


def partida(
    pid: int, edicion: int = 1, estado: str = "confirmada",
    gano: bool | None = True, propios: int | None = 2, rival: int | None = 0,
    ronda: int | None = 1,
) -> PartidaDeEquipo:
    return PartidaDeEquipo(
        partida_id=pid, edicion_id=edicion, estado=estado, es_ganador=gano,
        mapas_propios=propios, mapas_rival=rival, ronda=ronda,
    )


class TestRecord:
    def test_sin_partidas_esta_todo_en_cero(self):
        r = calcular_record([])
        assert (r.jugadas, r.ganadas, r.perdidas) == (0, 0, 0)

    def test_sin_partidas_el_porcentaje_es_none(self):
        """Mostrar 0% sería mentir sobre un equipo que no perdió nunca:
        simplemente todavía no debutó."""
        assert calcular_record([]).porcentaje_victorias is None

    def test_cuenta_victorias_y_derrotas(self):
        r = calcular_record([
            partida(1, gano=True),
            partida(2, gano=True),
            partida(3, gano=False, propios=0, rival=2),
        ])
        assert (r.jugadas, r.ganadas, r.perdidas) == (3, 2, 1)

    def test_acumula_mapas(self):
        r = calcular_record([
            partida(1, propios=2, rival=1),
            partida(2, gano=False, propios=0, rival=2),
        ])
        assert (r.mapas_favor, r.mapas_contra) == (2, 3)
        assert r.diferencia_mapas == -1

    def test_porcentaje_de_victorias(self):
        r = calcular_record([
            partida(1, gano=True), partida(2, gano=True),
            partida(3, gano=False), partida(4, gano=False),
        ])
        assert r.porcentaje_victorias == 50.0

    def test_ignora_partidas_sin_resolver(self):
        """Una partida en curso o en disputa todavía no es un resultado."""
        r = calcular_record([
            partida(1, estado="confirmada"),
            partida(2, estado="en_curso", gano=None),
            partida(3, estado="en_disputa", gano=None),
            partida(4, estado="programada", gano=None),
        ])
        assert r.jugadas == 1


class TestByesYWalkovers:
    def test_un_bye_no_cuenta_como_partida_jugada(self):
        """Un bye es un lugar libre en el cuadro: nadie juega y no hay rival.
        Contarlo como victoria infla el récord de quien tuvo suerte con la
        siembra."""
        r = calcular_record([partida(1, estado="bye", gano=True)])
        assert r.jugadas == 0
        assert r.ganadas == 0
        assert r.byes == 1

    def test_los_byes_se_informan_aparte(self):
        r = calcular_record([
            partida(1, estado="bye", gano=True),
            partida(2, estado="bye", gano=True),
            partida(3, gano=True),
        ])
        assert (r.jugadas, r.ganadas, r.byes) == (1, 1, 2)

    def test_un_bye_no_ensucia_el_porcentaje(self):
        """Dos equipos con el mismo desempeño real tienen que dar el mismo
        porcentaje, con o sin bye en el camino."""
        con_bye = calcular_record([partida(1, estado="bye", gano=True), partida(2, gano=True)])
        sin_bye = calcular_record([partida(2, gano=True)])
        assert con_bye.porcentaje_victorias == sin_bye.porcentaje_victorias == 100.0

    def test_un_walkover_si_cuenta(self):
        """El rival no se presentó, pero es un resultado decidido con
        ganador: así se registra en cualquier liga."""
        r = calcular_record([partida(1, estado="walkover", gano=True)])
        assert (r.jugadas, r.ganadas) == (1, 1)

    def test_un_walkover_sin_marcador_no_inventa_mapas(self):
        r = calcular_record([partida(1, estado="walkover", gano=True, propios=None, rival=None)])
        assert (r.jugadas, r.mapas_favor, r.mapas_contra) == (1, 0, 0)

    def test_un_walkover_perdido_cuenta_como_derrota(self):
        r = calcular_record([partida(1, estado="walkover", gano=False, propios=None, rival=None)])
        assert (r.jugadas, r.ganadas, r.perdidas) == (1, 0, 1)


class TestResumenPorEdicion:
    def test_separa_los_torneos(self):
        resumenes = resumir_por_edicion([
            partida(1, edicion=1, gano=True),
            partida(2, edicion=1, gano=False),
            partida(3, edicion=2, gano=True),
        ])
        assert [r.edicion_id for r in resumenes] == [1, 2]
        assert resumenes[0].record.jugadas == 2
        assert resumenes[1].record.jugadas == 1

    def test_guarda_la_ronda_mas_lejana(self):
        resumenes = resumir_por_edicion([
            partida(1, ronda=1), partida(2, ronda=3), partida(3, ronda=2),
        ])
        assert resumenes[0].ronda_maxima == 3

    def test_un_bye_tambien_cuenta_para_la_ronda_alcanzada(self):
        """Avanzar por bye igual es avanzar: el equipo estuvo en esa ronda."""
        resumenes = resumir_por_edicion([partida(1, estado="bye", ronda=4)])
        assert resumenes[0].ronda_maxima == 4
        assert resumenes[0].record.jugadas == 0

    def test_sin_rondas_la_ronda_maxima_es_none(self):
        """Round robin sin rondas numeradas: no hay 'hasta dónde llegó'."""
        resumenes = resumir_por_edicion([partida(1, ronda=None)])
        assert resumenes[0].ronda_maxima is None

    def test_sin_partidas_no_hay_resumenes(self):
        assert resumir_por_edicion([]) == []


class TestCampeon:
    def test_ganar_la_ultima_ronda_es_ser_campeon(self):
        partidas = [partida(10, ronda=1), partida(11, ronda=2)]
        assert gano_la_final(partidas, equipo_id=7, ganadores={10: 7, 11: 7}) is True

    def test_perder_la_final_no_es_ser_campeon(self):
        partidas = [partida(10, ronda=1), partida(11, ronda=2)]
        assert gano_la_final(partidas, equipo_id=7, ganadores={10: 7, 11: 99}) is False

    def test_ganar_una_ronda_previa_no_alcanza(self):
        """Llegar a la final y perderla no puede figurar como título."""
        partidas = [partida(10, ronda=1), partida(11, ronda=2), partida(12, ronda=3)]
        assert gano_la_final(partidas, equipo_id=7, ganadores={10: 7, 11: 7, 12: 99}) is False

    def test_sin_partidas_no_hay_campeon(self):
        assert gano_la_final([], equipo_id=7, ganadores={}) is False

    def test_sin_rondas_no_arriesga_un_campeon(self):
        """En un round robin el primer puesto sale de la tabla, no de una
        partida: acá no se inventa."""
        partidas = [partida(10, ronda=None)]
        assert gano_la_final(partidas, equipo_id=7, ganadores={10: 7}) is False

    def test_una_final_sin_ganador_definido_no_corona(self):
        partidas = [partida(11, ronda=2)]
        assert gano_la_final(partidas, equipo_id=7, ganadores={11: None}) is False
