"""Sorteo: persistir la estructura pura como filas y propagar ganadores.

Es la costura entre el dominio puro y la base — donde un generador correcto
igual puede terminar en una llave rota si los enlaces de avance se guardan
mal. Estos tests usan SQLite en memoria (ver conftest).
"""

import pytest

from app.domain import sorteo
from app.domain.enums import EstadoFase, EstadoPartida, FormatoFase, LadoLlave
from app.models import Partida, ParticipacionEnPartida


def equipos_de(partida: Partida) -> set[int]:
    return {p.equipo_id for p in partida.participaciones}


class TestEliminacionSimple:
    def test_persiste_una_fila_por_cruce(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(8, FormatoFase.ELIMINACION_SIMPLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        assert len(partidas) == 7
        assert db.query(Partida).filter(Partida.fase_id == fase.id).count() == 7

    def test_deja_la_fase_sorteada(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(8, FormatoFase.ELIMINACION_SIMPLE)
        sorteo.sortear_fase(db, fase, equipos)
        assert fase.estado == EstadoFase.SORTEADA

    def test_la_primera_ronda_tiene_a_los_ocho_equipos(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(8, FormatoFase.ELIMINACION_SIMPLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        ronda1 = [p for p in partidas if p.ronda == 1]
        colocados = [pp.equipo_id for p in ronda1 for pp in p.participaciones]
        assert sorted(colocados) == sorted(equipos)

    def test_las_rondas_siguientes_arrancan_vacias(self, db, fabrica_fase):
        """Nadie está colocado en semis antes de que se juegue nada."""
        fase, equipos = fabrica_fase(8, FormatoFase.ELIMINACION_SIMPLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        for p in partidas:
            if p.ronda and p.ronda > 1:
                assert p.participaciones == []

    def test_guarda_los_enlaces_de_avance(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(8, FormatoFase.ELIMINACION_SIMPLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        final = next(p for p in partidas if p.ronda == 3)
        # Todas menos la final tienen a dónde mandar al ganador.
        for p in partidas:
            if p.id == final.id:
                assert p.siguiente_partida_ganador_id is None
            else:
                assert p.siguiente_partida_ganador_id is not None
                assert p.siguiente_slot_ganador in (0, 1)

    def test_dos_partidas_de_una_ronda_alimentan_slots_distintos(self, db, fabrica_fase):
        """Si las dos semifinales apuntaran al mismo slot de la final, una
        pisaría a la otra."""
        fase, equipos = fabrica_fase(8, FormatoFase.ELIMINACION_SIMPLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        semis = [p for p in partidas if p.ronda == 2]
        assert len(semis) == 2
        assert semis[0].siguiente_partida_ganador_id == semis[1].siguiente_partida_ganador_id
        assert {semis[0].siguiente_slot_ganador, semis[1].siguiente_slot_ganador} == {0, 1}


class TestByes:
    def test_los_byes_quedan_resueltos_y_avanzados(self, db, fabrica_fase):
        """Con 5 equipos hay 3 byes: esos equipos tienen que aparecer ya
        colocados en la ronda 2 sin que nadie juegue nada."""
        fase, equipos = fabrica_fase(5, FormatoFase.ELIMINACION_SIMPLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)

        byes = [p for p in partidas if p.estado == EstadoPartida.BYE]
        assert len(byes) == 3
        for b in byes:
            assert b.confirmada_at is not None
            assert any(pp.es_ganador for pp in b.participaciones)

        ronda2 = [p for p in partidas if p.ronda == 2]
        ya_colocados = {pp.equipo_id for p in ronda2 for pp in p.participaciones}
        ganadores_bye = {
            pp.equipo_id for b in byes for pp in b.participaciones if pp.es_ganador
        }
        assert ganadores_bye <= ya_colocados

    def test_un_bye_nunca_coloca_a_dos_equipos(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(5, FormatoFase.ELIMINACION_SIMPLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        for p in partidas:
            if p.estado == EstadoPartida.BYE:
                assert len(p.participaciones) == 1


class TestAvanzarGanador:
    def _sortear_y_resolver_primera(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(4, FormatoFase.ELIMINACION_SIMPLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        primera = next(p for p in partidas if p.ronda == 1)
        ganador = primera.participaciones[0]
        perdedor = primera.participaciones[1]
        ganador.es_ganador = True
        perdedor.es_ganador = False
        primera.estado = EstadoPartida.CONFIRMADA
        db.commit()
        return fase, primera, ganador.equipo_id

    def test_coloca_al_ganador_en_la_partida_siguiente(self, db, fabrica_fase):
        fase, primera, ganador_id = self._sortear_y_resolver_primera(db, fabrica_fase)
        sorteo.avanzar_ganador(db, primera)

        siguiente = db.get(Partida, primera.siguiente_partida_ganador_id)
        assert ganador_id in equipos_de(siguiente)

    def test_lo_pone_en_el_slot_que_corresponde(self, db, fabrica_fase):
        fase, primera, ganador_id = self._sortear_y_resolver_primera(db, fabrica_fase)
        sorteo.avanzar_ganador(db, primera)

        siguiente = db.get(Partida, primera.siguiente_partida_ganador_id)
        colocado = next(p for p in siguiente.participaciones if p.equipo_id == ganador_id)
        assert colocado.slot == primera.siguiente_slot_ganador

    def test_llamarlo_dos_veces_no_duplica(self, db, fabrica_fase):
        """Idempotencia: el mismo avance puede dispararse más de una vez
        (confirmar, corregir, resolver una disputa sobre la misma partida) y
        no puede terminar con el equipo cargado dos veces."""
        fase, primera, ganador_id = self._sortear_y_resolver_primera(db, fabrica_fase)
        sorteo.avanzar_ganador(db, primera)
        sorteo.avanzar_ganador(db, primera)
        sorteo.avanzar_ganador(db, primera)

        siguiente = db.get(Partida, primera.siguiente_partida_ganador_id)
        cuantas = [p for p in siguiente.participaciones if p.equipo_id == ganador_id]
        assert len(cuantas) == 1

    def test_sin_ganador_marcado_no_avanza_nada(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(4, FormatoFase.ELIMINACION_SIMPLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        primera = next(p for p in partidas if p.ronda == 1)
        sorteo.avanzar_ganador(db, primera)

        siguiente = db.get(Partida, primera.siguiente_partida_ganador_id)
        assert siguiente.participaciones == []


class TestEliminacionDoble:
    def test_persiste_las_tres_zonas(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(4, FormatoFase.ELIMINACION_DOBLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        lados = {}
        for p in partidas:
            lados[p.lado] = lados.get(p.lado, 0) + 1
        assert lados == {LadoLlave.ALTA: 3, LadoLlave.BAJA: 2, LadoLlave.GRAN_FINAL: 1}

    def test_los_cruces_de_la_alta_saben_a_donde_mandar_al_perdedor(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(4, FormatoFase.ELIMINACION_DOBLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        alta = [p for p in partidas if p.lado == LadoLlave.ALTA]
        assert all(p.siguiente_partida_perdedor_id is not None for p in alta)

    def test_el_perdedor_cae_a_la_llave_baja(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(4, FormatoFase.ELIMINACION_DOBLE)
        partidas = sorteo.sortear_fase(db, fase, equipos)

        primera = next(p for p in partidas if p.lado == LadoLlave.ALTA and p.ronda == 1)
        primera.participaciones[0].es_ganador = True
        primera.participaciones[1].es_ganador = False
        perdedor_id = primera.participaciones[1].equipo_id
        db.commit()

        sorteo.avanzar_ganador(db, primera)

        destino = db.get(Partida, primera.siguiente_partida_perdedor_id)
        assert destino.lado == LadoLlave.BAJA
        assert perdedor_id in equipos_de(destino)


class TestRoundRobin:
    def test_genera_todos_contra_todos(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(5, FormatoFase.ROUND_ROBIN)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        assert len(partidas) == 10  # 5*4/2

    def test_sin_grupos_no_numera_el_grupo(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(4, FormatoFase.ROUND_ROBIN)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        assert all(p.grupo_numero is None for p in partidas)

    def test_con_grupos_numera_y_reparte(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(8, FormatoFase.ROUND_ROBIN, config={"grupos": 2})
        partidas = sorteo.sortear_fase(db, fase, equipos)
        assert len(partidas) == 12  # dos grupos de 4: 6 + 6
        assert {p.grupo_numero for p in partidas} == {0, 1}

    def test_cada_partida_tiene_exactamente_dos_equipos(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(5, FormatoFase.ROUND_ROBIN)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        assert all(len(p.participaciones) == 2 for p in partidas)


class TestSuizo:
    def test_solo_genera_la_ronda_uno(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(8, FormatoFase.SUIZO)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        assert len(partidas) == 4
        assert all(p.ronda == 1 for p in partidas)

    def test_cantidad_impar_crea_la_partida_de_bye(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(7, FormatoFase.SUIZO)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        byes = [p for p in partidas if p.estado == EstadoPartida.BYE]
        assert len(byes) == 1
        assert len(byes[0].participaciones) == 1
        assert byes[0].participaciones[0].es_ganador is True

    def test_todos_los_equipos_juegan_la_primera_ronda(self, db, fabrica_fase):
        fase, equipos = fabrica_fase(7, FormatoFase.SUIZO)
        partidas = sorteo.sortear_fase(db, fase, equipos)
        colocados = [pp.equipo_id for p in partidas for pp in p.participaciones]
        assert sorted(colocados) == sorted(equipos)
