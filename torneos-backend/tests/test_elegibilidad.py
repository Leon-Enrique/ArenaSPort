"""Elegibilidad: un jugador en un solo equipo por edición.

La regla siempre estuvo, pero ignoraba el estado de la inscripción: rechazar
un equipo dejaba a sus cinco jugadores bloqueados para el resto de la
edición, atados a una inscripción muerta. En la base de desarrollo había 6
jugadores en esa situación.

Lo que se prueba acá es la parte fina: qué estados liberan el cupo y cuáles
no. Descalificada NO libera, y eso es deliberado — si los jugadores de un
equipo descalificado pudieran reinscribirse con otro nombre, la sanción no
significaría nada.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.enums import (
    ESTADOS_QUE_OCUPAN_CUPO,
    EstadoEdicion,
    EstadoInscripcion,
    ModeloCompetencia,
)
from app.main import app
from app.models import Edicion, Inscripcion, Jugador, Juego, Torneo, Usuario


@pytest.fixture
def cliente(db):
    from app.db.database import get_db

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def edicion(db):
    juego = Juego(
        codigo="mlbb",
        nombre="MLBB",
        modelo_competencia_default=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        titulares_requeridos=2,
        suplentes_maximos=0,
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
    ed = Edicion(
        torneo_id=torneo.id, juego_id=juego.id, numero=1, nombre="T1", slug="copa-t1",
        estado=EstadoEdicion.INSCRIPCIONES_ABIERTAS,
        # Este archivo no prueba la regla de equipo permanente: inscribe
        # rosters sueltos. Explícito para no depender del default, que
        # ahora exige cuenta (ver Edicion.requiere_equipo_permanente).
        requiere_equipo_permanente=False,
    )
    db.add(ed)
    db.commit()
    return ed


def roster(prefijo: str, id_compartido: str):
    """Dos jugadores; el primero lleva el id que se comparte entre equipos."""
    return [
        {"identidad": {"nick": f"{prefijo}1", "id_juego": id_compartido}, "es_capitan": True},
        {"identidad": {"nick": f"{prefijo}2", "id_juego": f"{prefijo}-otro"}},
    ]


def inscribir(cliente, edicion_id, equipo, id_compartido, prefijo=None):
    return cliente.post(
        f"/api/ediciones/{edicion_id}/inscripciones",
        json={"nombre_equipo": equipo, "jugadores": roster(prefijo or equipo[:3].lower(), id_compartido)},
    )


def revisar(cliente, db, edicion_id, inscripcion_id, estado, motivo="por algo"):
    org = db.query(Usuario).filter(Usuario.es_organizador.is_(True)).first()
    if not org:
        org = Usuario(discord_id="org", discord_username="Org", es_organizador=True)
        db.add(org)
        db.commit()
    headers = {"Authorization": f"Bearer {crear_access_token(org.id, org.discord_id, True)}"}
    return cliente.post(
        f"/api/ediciones/{edicion_id}/inscripciones/{inscripcion_id}/revisar",
        json={"estado": estado, "motivo_rechazo": motivo},
        headers=headers,
    )


class TestLaReglaBasica:
    def test_el_mismo_jugador_no_entra_en_dos_equipos(self, cliente, edicion):
        assert inscribir(cliente, edicion.id, "Equipo A", "999").status_code == 201
        r = inscribir(cliente, edicion.id, "Equipo B", "999")
        assert r.status_code == 409
        assert "no puede estar en dos equipos" in r.json()["detail"]

    def test_el_error_nombra_el_equipo_donde_ya_esta(self, cliente, edicion):
        """Sin el nombre, el capitán no sabe si es un homónimo o si alguien de
        su plantel se anotó por su cuenta en otro lado."""
        inscribir(cliente, edicion.id, "Equipo A", "999")
        r = inscribir(cliente, edicion.id, "Equipo B", "999")
        assert "Equipo A" in r.json()["detail"]


class TestQueEstadosLiberanElCupo:
    def test_rechazar_libera_a_los_jugadores(self, cliente, db, edicion):
        """El bug que se venía arreglar: el equipo nunca entró al torneo, así
        que retener a su gente solo los deja sin poder jugar con nadie."""
        primera = inscribir(cliente, edicion.id, "Equipo A", "999")
        revisar(cliente, db, edicion.id, primera.json()["inscripcion"]["id"], "rechazada")

        r = inscribir(cliente, edicion.id, "Equipo B", "999")
        assert r.status_code == 201, r.text

    def test_retirar_tambien_libera(self, cliente, db, edicion):
        primera = inscribir(cliente, edicion.id, "Equipo A", "999")
        revisar(cliente, db, edicion.id, primera.json()["inscripcion"]["id"], "retirada")

        assert inscribir(cliente, edicion.id, "Equipo B", "999").status_code == 201

    def test_descalificar_NO_libera(self, cliente, db, edicion):
        """A propósito: si los jugadores de un equipo descalificado pudieran
        reinscribirse con otro nombre, la sanción no serviría de nada."""
        primera = inscribir(cliente, edicion.id, "Equipo A", "999")
        revisar(cliente, db, edicion.id, primera.json()["inscripcion"]["id"], "descalificada")

        r = inscribir(cliente, edicion.id, "Equipo B", "999")
        assert r.status_code == 409

    def test_aprobar_mantiene_el_bloqueo(self, cliente, db, edicion):
        primera = inscribir(cliente, edicion.id, "Equipo A", "999")
        revisar(cliente, db, edicion.id, primera.json()["inscripcion"]["id"], "aprobada")

        assert inscribir(cliente, edicion.id, "Equipo B", "999").status_code == 409

    def test_pendiente_bloquea(self, cliente, edicion):
        """Todavía sin revisar, pero está en la carrera."""
        inscribir(cliente, edicion.id, "Equipo A", "999")
        assert inscribir(cliente, edicion.id, "Equipo B", "999").status_code == 409


class TestElFlagDerivado:
    def test_el_flag_sigue_al_estado(self, cliente, db, edicion):
        creada = inscribir(cliente, edicion.id, "Equipo A", "999")
        insc_id = creada.json()["inscripcion"]["id"]

        assert all(j.ocupa_cupo for j in db.get(Inscripcion, insc_id).jugadores)

        revisar(cliente, db, edicion.id, insc_id, "rechazada")
        db.expire_all()
        assert not any(j.ocupa_cupo for j in db.get(Inscripcion, insc_id).jugadores)

    def test_volver_a_aprobar_lo_vuelve_a_ocupar(self, cliente, db, edicion):
        """Un rechazo revertido tiene que volver a bloquear, o el jugador
        podría quedar en dos equipos a la vez."""
        creada = inscribir(cliente, edicion.id, "Equipo A", "999")
        insc_id = creada.json()["inscripcion"]["id"]

        revisar(cliente, db, edicion.id, insc_id, "rechazada")
        revisar(cliente, db, edicion.id, insc_id, "aprobada")
        db.expire_all()

        assert all(j.ocupa_cupo for j in db.get(Inscripcion, insc_id).jugadores)
        assert inscribir(cliente, edicion.id, "Equipo B", "999").status_code == 409

    def test_el_conjunto_de_estados_es_el_esperado(self):
        """Fija la decisión para que cambiarla sea deliberado y no un
        descuido: agregar un estado nuevo al enum no lo mete acá solo."""
        assert ESTADOS_QUE_OCUPAN_CUPO == {
            EstadoInscripcion.PENDIENTE,
            EstadoInscripcion.APROBADA,
            EstadoInscripcion.DESCALIFICADA,
        }


class TestOtrasEdiciones:
    def test_el_bloqueo_es_por_edicion(self, cliente, db, edicion):
        """Jugar dos torneos distintos al mismo tiempo es normal y tiene que
        seguir permitido."""
        otra = Edicion(
            torneo_id=edicion.torneo_id, juego_id=edicion.juego_id, numero=2,
            nombre="T2", slug="copa-t2", estado=EstadoEdicion.INSCRIPCIONES_ABIERTAS,
        # Este archivo no prueba la regla de equipo permanente: inscribe
        # rosters sueltos como antes. Explicito para no depender del
        # default, que ahora exige cuenta (ver Edicion.requiere_equipo_permanente).
        requiere_equipo_permanente=False,
        )
        db.add(otra)
        db.commit()

        assert inscribir(cliente, edicion.id, "Equipo A", "999").status_code == 201
        assert inscribir(cliente, otra.id, "Equipo A", "999").status_code == 201
