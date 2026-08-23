"""Check-in del torneo y partido por el tercer puesto.

Dos huecos que se notan en cuanto corrés un torneo de verdad.

El check-in de torneo es distinto del de cada partida: se hace una vez, antes
de sortear. Entre que un equipo se inscribe y arranca el torneo pasan días y
siempre hay algunos que no aparecen; sortear con ellos deja el cuadro lleno
de walkovers desde la primera ronda.

El tercer puesto simplemente no existía: la llave simple generaba final y
nada más, así que un torneo con premio al tercero tenía que armar ese cruce
a mano.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.formatos import eliminacion_simple
from app.domain.formatos.base import TipoFuente
from app.domain.enums import (
    EstadoEdicion,
    EstadoInscripcion,
    FormatoFase,
    ModeloCompetencia,
)
from app.main import app
from app.models import Edicion, Fase, Inscripcion, Juego, Torneo, Usuario


@pytest.fixture
def cliente(db):
    from app.db.database import get_db

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth(u: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(u.id, u.discord_id, u.es_organizador)}"}


@pytest.fixture
def torneo_con_equipos(db):
    juego = Juego(
        codigo="mlbb", nombre="MLBB",
        modelo_competencia_default=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        titulares_requeridos=1, suplentes_maximos=0,
        campos_identidad={
            "campos": [{"nombre": "nick", "etiqueta": "Nick", "requerido": True}],
            "clave_unica": ["nick"],
        },
    )
    db.add(juego)
    db.flush()
    torneo = Torneo(nombre="Copa", slug="copa")
    db.add(torneo)
    db.flush()
    edicion = Edicion(
        torneo_id=torneo.id, juego_id=juego.id, numero=1, nombre="T1",
        slug="copa-t1", estado=EstadoEdicion.INSCRIPCIONES_ABIERTAS,
    )
    db.add(edicion)
    db.flush()

    org = Usuario(discord_id="org", discord_username="Org", es_organizador=True)
    db.add(org)
    db.flush()

    capitanes = []
    for i in range(1, 5):
        u = Usuario(discord_id=f"cap{i}", discord_username=f"Cap{i}")
        db.add(u)
        capitanes.append(u)
    db.commit()
    return {"edicion": edicion, "organizador": org, "capitanes": capitanes}


def inscribir(cliente, escenario, capitan, nombre):
    return cliente.post(
        f"/api/ediciones/{escenario['edicion'].id}/inscripciones",
        json={
            "nombre_equipo": nombre,
            "jugadores": [{"identidad": {"nick": nombre.lower()}, "es_capitan": True}],
        },
        headers=auth(capitan),
    )


def inscribir_y_aprobar(cliente, db, escenario, cuantos=4):
    ids = []
    for i in range(cuantos):
        r = inscribir(cliente, escenario, escenario["capitanes"][i], f"Equipo{i}")
        insc_id = r.json()["inscripcion"]["id"]
        db.get(Inscripcion, insc_id).estado = EstadoInscripcion.APROBADA
        ids.append(insc_id)
    db.commit()
    return ids


class TestCheckinDeTorneo:
    def test_sin_checkin_abierto_no_se_puede_confirmar(self, cliente, db, torneo_con_equipos):
        ids = inscribir_y_aprobar(cliente, db, torneo_con_equipos, 1)
        r = cliente.post(
            f"/api/ediciones/{torneo_con_equipos['edicion'].id}/inscripciones/{ids[0]}/checkin",
            headers=auth(torneo_con_equipos["capitanes"][0]),
        )
        assert r.status_code == 409
        assert "no pide check-in" in r.json()["detail"]

    def test_solo_el_organizador_lo_abre(self, cliente, db, torneo_con_equipos):
        r = cliente.post(
            f"/api/ediciones/{torneo_con_equipos['edicion'].id}/abrir-checkin",
            headers=auth(torneo_con_equipos["capitanes"][0]),
        )
        assert r.status_code == 403

    def test_el_capitan_confirma(self, cliente, db, torneo_con_equipos):
        ids = inscribir_y_aprobar(cliente, db, torneo_con_equipos, 1)
        cliente.post(
            f"/api/ediciones/{torneo_con_equipos['edicion'].id}/abrir-checkin",
            headers=auth(torneo_con_equipos["organizador"]),
        )
        r = cliente.post(
            f"/api/ediciones/{torneo_con_equipos['edicion'].id}/inscripciones/{ids[0]}/checkin",
            headers=auth(torneo_con_equipos["capitanes"][0]),
        )
        assert r.status_code == 200, r.text
        assert db.get(Inscripcion, ids[0]).checkin_at is not None

    def test_un_equipo_no_aprobado_no_puede(self, cliente, db, torneo_con_equipos):
        r = inscribir(cliente, torneo_con_equipos, torneo_con_equipos["capitanes"][0], "Pendiente")
        insc_id = r.json()["inscripcion"]["id"]
        cliente.post(
            f"/api/ediciones/{torneo_con_equipos['edicion'].id}/abrir-checkin",
            headers=auth(torneo_con_equipos["organizador"]),
        )
        r2 = cliente.post(
            f"/api/ediciones/{torneo_con_equipos['edicion'].id}/inscripciones/{insc_id}/checkin",
            headers=auth(torneo_con_equipos["capitanes"][0]),
        )
        assert r2.status_code == 409

    def test_la_ventana_esta_acotada(self, cliente, torneo_con_equipos):
        r = cliente.post(
            f"/api/ediciones/{torneo_con_equipos['edicion'].id}/abrir-checkin?horas=9999",
            headers=auth(torneo_con_equipos["organizador"]),
        )
        assert r.status_code == 422


class TestElSorteoRespetaElCheckin:
    def _fase(self, db, edicion):
        fase = Fase(
            edicion_id=edicion.id, orden=1, nombre="Llave",
            modelo_competencia=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
            formato=FormatoFase.ELIMINACION_SIMPLE, config={"bo": 3},
        )
        db.add(fase)
        db.commit()
        return fase

    def test_sin_checkin_entran_todos(self, cliente, db, torneo_con_equipos):
        """Comportamiento de siempre para los torneos que no lo piden."""
        ids = inscribir_y_aprobar(cliente, db, torneo_con_equipos, 4)
        ed = torneo_con_equipos["edicion"]
        fase = self._fase(db, ed)
        cliente.post(
            f"/api/ediciones/{ed.id}/inscripciones/sembrar-automatico",
            headers=auth(torneo_con_equipos["organizador"]),
        )
        r = cliente.post(
            f"/api/ediciones/{ed.id}/fases/{fase.id}/sortear",
            headers=auth(torneo_con_equipos["organizador"]),
        )
        assert r.status_code == 200, r.text
        colocados = {p["equipo"]["id"] for pa in r.json() for p in pa["participaciones"]}
        assert len(colocados) == 4

    def test_los_que_no_confirmaron_quedan_afuera(self, cliente, db, torneo_con_equipos):
        """El punto de todo esto."""
        ids = inscribir_y_aprobar(cliente, db, torneo_con_equipos, 4)
        ed = torneo_con_equipos["edicion"]
        cliente.post(f"/api/ediciones/{ed.id}/abrir-checkin", headers=auth(torneo_con_equipos["organizador"]))

        # Solo confirman dos de los cuatro.
        for i in (0, 1):
            cliente.post(
                f"/api/ediciones/{ed.id}/inscripciones/{ids[i]}/checkin",
                headers=auth(torneo_con_equipos["capitanes"][i]),
            )

        fase = self._fase(db, ed)
        cliente.post(
            f"/api/ediciones/{ed.id}/inscripciones/sembrar-automatico",
            headers=auth(torneo_con_equipos["organizador"]),
        )
        r = cliente.post(
            f"/api/ediciones/{ed.id}/fases/{fase.id}/sortear",
            headers=auth(torneo_con_equipos["organizador"]),
        )
        assert r.status_code == 200, r.text
        colocados = {p["equipo"]["id"] for pa in r.json() for p in pa["participaciones"]}
        assert len(colocados) == 2

    def test_si_casi_nadie_confirma_avisa_en_vez_de_sortear(self, cliente, db, torneo_con_equipos):
        ids = inscribir_y_aprobar(cliente, db, torneo_con_equipos, 4)
        ed = torneo_con_equipos["edicion"]
        cliente.post(f"/api/ediciones/{ed.id}/abrir-checkin", headers=auth(torneo_con_equipos["organizador"]))
        cliente.post(
            f"/api/ediciones/{ed.id}/inscripciones/{ids[0]}/checkin",
            headers=auth(torneo_con_equipos["capitanes"][0]),
        )
        fase = self._fase(db, ed)
        cliente.post(
            f"/api/ediciones/{ed.id}/inscripciones/sembrar-automatico",
            headers=auth(torneo_con_equipos["organizador"]),
        )
        r = cliente.post(
            f"/api/ediciones/{ed.id}/fases/{fase.id}/sortear",
            headers=auth(torneo_con_equipos["organizador"]),
        )
        assert r.status_code == 422
        assert "1 de 4" in r.json()["detail"]


class TestTercerPuesto:
    def test_no_se_genera_si_no_se_pide(self):
        r = eliminacion_simple.generar([1, 2, 3, 4])
        assert len(r.cruces) == 3  # 2 semis + final

    def test_se_agrega_el_cruce_de_perdedores(self, ):
        r = eliminacion_simple.generar([1, 2, 3, 4], con_tercer_puesto=True)
        assert len(r.cruces) == 4

        tercero = r.cruces[-1]
        assert tercero.fuente_a.tipo == TipoFuente.PERDEDOR_DE
        assert tercero.fuente_b.tipo == TipoFuente.PERDEDOR_DE

    def test_lo_juegan_los_perdedores_de_las_semis(self):
        r = eliminacion_simple.generar([1, 2, 3, 4], con_tercer_puesto=True)
        semis = [c.indice for c in r.cruces if c.ronda == 1]
        tercero = r.cruces[-1]
        assert {tercero.fuente_a.valor, tercero.fuente_b.valor} == set(semis)

    def test_va_en_la_misma_ronda_que_la_final(self):
        """Se juega el mismo día: ponerlo después lo dejaría 'más lejos' que
        la final en cualquier vista ordenada por ronda."""
        r = eliminacion_simple.generar([1, 2, 3, 4], con_tercer_puesto=True)
        assert r.cruces[-1].ronda == r.total_rondas

    def test_con_dos_equipos_no_hay_tercer_puesto(self):
        """No hay semifinales de las que sacar perdedores."""
        r = eliminacion_simple.generar([1, 2], con_tercer_puesto=True)
        assert len(r.cruces) == 1

    @pytest.mark.parametrize("n", [4, 8, 16, 32])
    def test_agrega_exactamente_un_cruce(self, n):
        equipos = list(range(1, n + 1))
        sin = eliminacion_simple.generar(equipos)
        con = eliminacion_simple.generar(equipos, con_tercer_puesto=True)
        assert len(con.cruces) == len(sin.cruces) + 1

    def test_se_persiste_si_la_fase_lo_pide(self, db, fabrica_fase):
        from app.domain import sorteo

        fase, equipos = fabrica_fase(
            4, FormatoFase.ELIMINACION_SIMPLE, config={"bo": 3, "tercer_puesto": True}
        )
        partidas = sorteo.sortear_fase(db, fase, equipos)
        assert len(partidas) == 4

        # El cruce del tercer puesto es el único que recibe perdedores.
        con_perdedor = [p for p in partidas if p.siguiente_partida_perdedor_id]
        assert len(con_perdedor) == 2  # las dos semifinales
