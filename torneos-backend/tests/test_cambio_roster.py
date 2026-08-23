"""Cambiar el plantel con el torneo ya empezado.

El caso que motivó esto es concreto y frecuente: a un titular se le rompe el
celular en cuartos de final y el equipo necesita reemplazarlo. Antes no había
salida — el roster se congelaba al sortear y el bloqueo no tenía excepción ni
siquiera para el organizador. Peor: el mensaje de error mandaba a hacerlo
"directamente", algo que ningún endpoint permitía.

Lo que se prueba es el equilibrio: que el caso legítimo se pueda resolver sin
abrir la puerta a meter un refuerzo antes de la final.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.enums import (
    EstadoEdicion,
    EstadoInscripcion,
    FormatoFase,
    ModeloCompetencia,
)
from app.main import app
from app.models import (
    CambioDeRoster,
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


@pytest.fixture
def escenario(db):
    """Un equipo aprobado y YA sorteado: tiene partida, así que su plantel
    está congelado."""
    juego = Juego(
        codigo="mlbb", nombre="MLBB",
        modelo_competencia_default=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        titulares_requeridos=2, suplentes_maximos=0,
        campos_identidad={
            "campos": [
                {"nombre": "nick", "etiqueta": "Nick", "requerido": True},
                {"nombre": "id_juego", "etiqueta": "ID", "requerido": True},
            ],
            "clave_unica": ["id_juego"],
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

    capitan = Usuario(discord_id="cap", discord_username="Cap")
    org = Usuario(discord_id="org", discord_username="Org", es_organizador=True)
    db.add_all([capitan, org])
    db.commit()

    return {"edicion": edicion, "capitan": capitan, "organizador": org, "juego": juego}


def auth(u: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(u.id, u.discord_id, u.es_organizador)}"}


def roster(*nicks, discord_capitan=None):
    return [
        {
            "identidad": {"nick": n, "id_juego": f"id-{n}"},
            "es_capitan": i == 0,
            **({"discord_id": discord_capitan} if i == 0 and discord_capitan else {}),
        }
        for i, n in enumerate(nicks)
    ]


def inscribir_y_sortear(cliente, db, escenario, nicks=("ana", "beto")):
    """Inscribe, aprueba y crea una partida: deja el plantel congelado."""
    ed = escenario["edicion"]
    creada = cliente.post(
        f"/api/ediciones/{ed.id}/inscripciones",
        json={
            "nombre_equipo": "Dragons",
            "jugadores": roster(*nicks, discord_capitan=escenario["capitan"].discord_id),
        },
    )
    assert creada.status_code == 201, creada.text
    insc_id = creada.json()["inscripcion"]["id"]

    insc = db.get(Inscripcion, insc_id)
    insc.estado = EstadoInscripcion.APROBADA

    fase = Fase(
        edicion_id=ed.id, orden=1, nombre="Llave",
        modelo_competencia=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        formato=FormatoFase.ELIMINACION_SIMPLE, config={"bo": 3},
    )
    db.add(fase)
    db.flush()
    partida = Partida(fase_id=fase.id, ronda=1)
    db.add(partida)
    db.flush()
    db.add(ParticipacionEnPartida(partida_id=partida.id, equipo_id=insc.equipo_id, slot=0))
    db.commit()
    return insc_id


def editar(cliente, escenario, insc_id, nicks, quien):
    return cliente.patch(
        f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc_id}",
        json={
            "nombre_equipo": "Dragons",
            "jugadores": roster(*nicks, discord_capitan=escenario["capitan"].discord_id),
        },
        headers=auth(quien),
    )


class TestElBloqueoSigueEnPie:
    def test_sin_permiso_no_se_puede_cambiar(self, cliente, db, escenario):
        """Lo normal: el torneo arrancó, el plantel está congelado."""
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        r = editar(cliente, escenario, insc_id, ("ana", "carlos"), escenario["capitan"])
        assert r.status_code == 409

    def test_el_error_dice_como_resolverlo(self, cliente, db, escenario):
        """Antes mandaba a hacerlo 'directamente' y no existía ningún
        endpoint para eso: un callejón sin salida."""
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        r = editar(cliente, escenario, insc_id, ("ana", "carlos"), escenario["capitan"])
        assert "permitir-cambio-roster" in r.json()["detail"]

    def test_ni_el_organizador_puede_sin_habilitarlo(self, cliente, db, escenario):
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        r = editar(cliente, escenario, insc_id, ("ana", "carlos"), escenario["organizador"])
        assert r.status_code == 409


class TestConPermiso:
    def _habilitar(self, cliente, escenario, insc_id, horas=24):
        return cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc_id}/permitir-cambio-roster",
            json={"motivo": "Se le rompio el celular al titular", "horas": horas},
            headers=auth(escenario["organizador"]),
        )

    def test_solo_el_organizador_habilita(self, cliente, db, escenario):
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc_id}/permitir-cambio-roster",
            json={"motivo": "me conviene"},
            headers=auth(escenario["capitan"]),
        )
        assert r.status_code == 403

    def test_habilitado_el_capitan_puede_cambiar(self, cliente, db, escenario):
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        assert self._habilitar(cliente, escenario, insc_id).status_code == 200

        r = editar(cliente, escenario, insc_id, ("ana", "carlos"), escenario["capitan"])
        assert r.status_code == 200, r.text

    def test_el_cambio_queda_registrado(self, cliente, db, escenario):
        """Sin rastro, un cambio en cuartos es la palabra de uno contra la
        del otro."""
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        self._habilitar(cliente, escenario, insc_id)
        editar(cliente, escenario, insc_id, ("ana", "carlos"), escenario["capitan"])

        cambios = db.query(CambioDeRoster).filter(
            CambioDeRoster.inscripcion_id == insc_id
        ).all()
        assert len(cambios) == 1
        assert cambios[0].entraron == "carlos"
        assert cambios[0].salieron == "beto"
        assert "celular" in cambios[0].motivo_autorizacion

    def test_el_permiso_se_consume_con_un_cambio(self, cliente, db, escenario):
        """Autorizar un reemplazo no puede habilitar rehacer el plantel
        entero durante 24 horas."""
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        self._habilitar(cliente, escenario, insc_id)

        assert editar(cliente, escenario, insc_id, ("ana", "carlos"), escenario["capitan"]).status_code == 200
        segundo = editar(cliente, escenario, insc_id, ("ana", "diego"), escenario["capitan"])
        assert segundo.status_code == 409

    def test_un_permiso_vencido_no_sirve(self, cliente, db, escenario):
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        self._habilitar(cliente, escenario, insc_id)

        from datetime import UTC, datetime, timedelta

        insc = db.get(Inscripcion, insc_id)
        insc.cambio_roster_hasta = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

        r = editar(cliente, escenario, insc_id, ("ana", "carlos"), escenario["capitan"])
        assert r.status_code == 409

    def test_la_ventana_esta_acotada(self, cliente, db, escenario):
        """Un permiso abierto para siempre es lo mismo que no tener el
        bloqueo."""
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        r = self._habilitar(cliente, escenario, insc_id, horas=999)
        assert r.status_code == 422

    def test_el_motivo_es_obligatorio(self, cliente, db, escenario):
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc_id}/permitir-cambio-roster",
            json={"motivo": ""},
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 422


class TestElHistorialEsPublico:
    def test_cualquiera_puede_consultarlo(self, cliente, db, escenario):
        """La transparencia es el punto: convierte una sospecha en un dato
        verificable."""
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc_id}/permitir-cambio-roster",
            json={"motivo": "celular roto"},
            headers=auth(escenario["organizador"]),
        )
        editar(cliente, escenario, insc_id, ("ana", "carlos"), escenario["capitan"])

        r = cliente.get(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc_id}/cambios-de-roster"
        )
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["entraron"] == "carlos"

    def test_sin_cambios_devuelve_vacio(self, cliente, db, escenario):
        insc_id = inscribir_y_sortear(cliente, db, escenario)
        r = cliente.get(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc_id}/cambios-de-roster"
        )
        assert r.json() == []


class TestAntesDelSorteo:
    def test_editar_sin_partidas_no_deja_rastro(self, cliente, db, escenario):
        """Editar mientras la inscripción está pendiente es parte normal de
        anotarse: no necesita permiso ni registro."""
        ed = escenario["edicion"]
        creada = cliente.post(
            f"/api/ediciones/{ed.id}/inscripciones",
            json={
                "nombre_equipo": "Dragons",
                "jugadores": roster("ana", "beto", discord_capitan=escenario["capitan"].discord_id),
            },
        )
        insc_id = creada.json()["inscripcion"]["id"]

        r = editar(cliente, escenario, insc_id, ("ana", "carlos"), escenario["capitan"])
        assert r.status_code == 200, r.text
        assert db.query(CambioDeRoster).count() == 0
