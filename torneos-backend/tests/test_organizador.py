"""Herramientas de control del organizador.

Tres huecos que las plataformas de referencia tienen y este proyecto no:

  - Elegir quién carga los resultados. En Battlefy el organizador decide si
    reportan los jugadores o solo los admins; acá era siempre "capitán
    reporta, rival confirma", que no sirve para un torneo presencial con
    árbitro en cada mesa.
  - Sembrar por puntos. Solo había siembra aleatoria o número por número a
    mano.
  - Borrar una edición. Solo se podía borrar el torneo ENTERO, lo que no
    servía para el caso normal: una edición creada por error dentro de un
    torneo que sí querés conservar.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.enums import (
    EstadoEdicion,
    EstadoInscripcion,
    EstadoPartida,
    FormatoFase,
    ModeloCompetencia,
)
from app.main import app
from app.models import (
    Edicion,
    Fase,
    Inscripcion,
    Juego,
    Partida,
    ParticipacionEnPartida,
    Torneo,
    Usuario,
)


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
def escenario(db):
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
        # Este archivo no prueba la regla de equipo permanente: inscribe
        # rosters sueltos. Explícito para no depender del default, que
        # ahora exige cuenta (ver Edicion.requiere_equipo_permanente).
        requiere_equipo_permanente=False,
    )
    db.add(edicion)
    db.flush()
    org = Usuario(discord_id="org", discord_username="Org", es_organizador=True)
    caps = [Usuario(discord_id=f"cap{i}", discord_username=f"Cap{i}") for i in range(4)]
    db.add_all([org, *caps])
    db.commit()
    return {"torneo": torneo, "edicion": edicion, "organizador": org, "capitanes": caps}


def inscribir(cliente, escenario, i, nombre):
    return cliente.post(
        f"/api/ediciones/{escenario['edicion'].id}/inscripciones",
        json={
            "nombre_equipo": nombre,
            "jugadores": [{"identidad": {"nick": nombre.lower()}, "es_capitan": True}],
        },
        headers=auth(escenario["capitanes"][i]),
    )


class TestQuienReporta:
    def _partida_lista(self, cliente, db, escenario):
        """Dos equipos aprobados con una partida en curso."""
        ids = []
        for i in range(2):
            r = inscribir(cliente, escenario, i, f"Equipo{i}")
            insc = db.get(Inscripcion, r.json()["inscripcion"]["id"])
            insc.estado = EstadoInscripcion.APROBADA
            ids.append(insc.equipo_id)
        fase = Fase(
            edicion_id=escenario["edicion"].id, orden=1, nombre="F",
            modelo_competencia=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
            formato=FormatoFase.ELIMINACION_SIMPLE, config={"bo": 3},
        )
        db.add(fase)
        db.flush()
        partida = Partida(fase_id=fase.id, ronda=1, estado=EstadoPartida.EN_CURSO)
        db.add(partida)
        db.flush()
        for slot, eq in enumerate(ids):
            db.add(ParticipacionEnPartida(partida_id=partida.id, equipo_id=eq, slot=slot))
        db.commit()
        return fase.id, partida.id, ids

    def test_por_defecto_reporta_el_capitan(self, cliente, db, escenario):
        fase_id, partida_id, equipos = self._partida_lista(cliente, db, escenario)
        r = cliente.post(
            f"/api/fases/{fase_id}/partidas/{partida_id}/reportar",
            json={"equipo_id": equipos[0], "marcador_propio": 2, "marcador_rival": 0},
            headers=auth(escenario["capitanes"][0]),
        )
        assert r.status_code == 200, r.text

    def test_en_modo_organizador_el_capitan_no_puede(self, cliente, db, escenario):
        """Torneo presencial con árbitro: los equipos no cargan nada."""
        fase_id, partida_id, equipos = self._partida_lista(cliente, db, escenario)
        escenario["edicion"].solo_organizador_reporta = True
        db.commit()

        r = cliente.post(
            f"/api/fases/{fase_id}/partidas/{partida_id}/reportar",
            json={"equipo_id": equipos[0], "marcador_propio": 2, "marcador_rival": 0},
            headers=auth(escenario["capitanes"][0]),
        )
        assert r.status_code == 403
        assert "organizador" in r.json()["detail"]

    def test_en_modo_organizador_el_organizador_si(self, cliente, db, escenario):
        fase_id, partida_id, equipos = self._partida_lista(cliente, db, escenario)
        escenario["edicion"].solo_organizador_reporta = True
        db.commit()

        r = cliente.post(
            f"/api/fases/{fase_id}/partidas/{partida_id}/reportar",
            json={"equipo_id": equipos[0], "marcador_propio": 2, "marcador_rival": 0},
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 200, r.text


class TestSiembraPorPuntos:
    def _aprobar_con_puntos(self, cliente, db, escenario, puntos):
        for i, pts in enumerate(puntos):
            r = inscribir(cliente, escenario, i, f"Equipo{i}")
            insc = db.get(Inscripcion, r.json()["inscripcion"]["id"])
            insc.estado = EstadoInscripcion.APROBADA
            insc.puntos_siembra = pts
        db.commit()

    def test_sin_puntos_sigue_siendo_al_azar(self, cliente, db, escenario):
        """Comportamiento de siempre para quien no los usa."""
        self._aprobar_con_puntos(cliente, db, escenario, [None, None, None, None])
        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/sembrar-automatico?semilla=1",
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 200
        assert sorted(i["seed"] for i in r.json()) == [1, 2, 3, 4]

    def test_el_de_mas_puntos_queda_primero(self, cliente, db, escenario):
        self._aprobar_con_puntos(cliente, db, escenario, [10, 50, 30, 20])
        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/sembrar-automatico",
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 200, r.text
        por_seed = {i["seed"]: i["puntos_siembra"] for i in r.json()}
        assert por_seed[1] == 50
        assert por_seed[4] == 10

    def test_los_seeds_no_se_repiten(self, cliente, db, escenario):
        self._aprobar_con_puntos(cliente, db, escenario, [10, 50, 30, 20])
        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/sembrar-automatico",
            headers=auth(escenario["organizador"]),
        )
        seeds = [i["seed"] for i in r.json()]
        assert sorted(seeds) == [1, 2, 3, 4]

    def test_los_empatados_no_se_ordenan_por_antiguedad(self, cliente, db, escenario):
        """Con todos empatados el orden tiene que ser sorteado, no el de
        inscripción disfrazado."""
        self._aprobar_con_puntos(cliente, db, escenario, [10, 10, 10, 10])
        ordenes = set()
        for semilla in range(12):
            r = cliente.post(
                f"/api/ediciones/{escenario['edicion'].id}/inscripciones/"
                f"sembrar-automatico?semilla={semilla}",
                headers=auth(escenario["organizador"]),
            )
            ordenes.add(tuple(i["id"] for i in sorted(r.json(), key=lambda x: x["seed"])))
        assert len(ordenes) > 1


class TestBorrarEdicion:
    def test_una_edicion_limpia_se_borra(self, cliente, db, escenario):
        ed_id = escenario["edicion"].id
        r = cliente.delete(
            f"/api/ediciones/{ed_id}", headers=auth(escenario["organizador"])
        )
        assert r.status_code == 204
        assert db.get(Edicion, ed_id) is None

    def test_se_lleva_sus_inscripciones_y_jugadores(self, cliente, db, escenario):
        inscribir(cliente, escenario, 0, "Equipo0")
        ed_id = escenario["edicion"].id

        cliente.delete(f"/api/ediciones/{ed_id}", headers=auth(escenario["organizador"]))
        assert db.query(Inscripcion).filter(Inscripcion.edicion_id == ed_id).count() == 0

    def test_el_torneo_sobrevive(self, cliente, db, escenario):
        """El punto de tener esto: borrar una edición creada por error sin
        perder el torneo."""
        torneo_id = escenario["torneo"].id
        cliente.delete(
            f"/api/ediciones/{escenario['edicion'].id}",
            headers=auth(escenario["organizador"]),
        )
        assert db.get(Torneo, torneo_id) is not None

    def test_no_se_borra_una_edicion_con_resultados(self, cliente, db, escenario):
        """Una edición jugada es historia, no se tira desde un endpoint."""
        fase = Fase(
            edicion_id=escenario["edicion"].id, orden=1, nombre="F",
            modelo_competencia=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
            formato=FormatoFase.ELIMINACION_SIMPLE, config={},
        )
        db.add(fase)
        db.flush()
        db.add(Partida(fase_id=fase.id, ronda=1, estado=EstadoPartida.CONFIRMADA))
        db.commit()

        r = cliente.delete(
            f"/api/ediciones/{escenario['edicion'].id}",
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 409

    def test_solo_el_organizador(self, cliente, db, escenario):
        r = cliente.delete(
            f"/api/ediciones/{escenario['edicion'].id}",
            headers=auth(escenario["capitanes"][0]),
        )
        assert r.status_code == 403

    def test_una_edicion_inexistente_da_404(self, cliente, escenario):
        r = cliente.delete("/api/ediciones/99999", headers=auth(escenario["organizador"]))
        assert r.status_code == 404
