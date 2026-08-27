"""Inscribirse sin retipear el roster.

Es el pago de todo el rediseño. Antes, un equipo que jugaba cinco torneos
tipeaba a sus cinco jugadores cinco veces, y los tipeaba el capitán — de ahí
salían los IDs mal copiados y que nadie fuera dueño de sus propios datos.

Ahora el capitán manda la inscripción sin `jugadores` y el plantel se arma
solo, con la identidad que cargó cada uno en su cuenta.

La regla dura: **no se entra incompleto.** Si falta gente la inscripción se
rechaza, porque un equipo al que le faltan jugadores no puede jugar y
dejarlo anotarse "a completar después" convierte el problema en algo que
aparece el día del sorteo. Lo que sí se cuida es que el rechazo sea
accionable: a los que no cargaron su ID se les avisa en el momento, porque
son los únicos que pueden destrabarlo.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.enums import EstadoEdicion, EstadoInscripcion, ModeloCompetencia
from app.main import app
from app.models import (
    Edicion,
    Equipo,
    IdentidadDeJuego,
    Inscripcion,
    Jugador,
    MiembroEquipo,
    Notificacion,
    Torneo,
    Usuario,
)

TITULARES = 3


@pytest.fixture
def cliente(db):
    from app.db.database import get_db

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def escenario(db):
    from app.models import Juego

    juego = Juego(
        codigo="mlbb",
        nombre="Mobile Legends",
        modelo_competencia_default=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        titulares_requeridos=TITULARES,
        suplentes_maximos=2,
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

    capitan = Usuario(discord_id="cap", discord_username="Capitan")
    db.add(capitan)
    db.flush()
    equipo = Equipo(nombre="Dragons", propietario_usuario_id=capitan.id)
    db.add(equipo)
    db.flush()

    # El capitán es miembro de su propio equipo, como pasa al crearlo.
    jugadores = [capitan]
    for i in range(1, 5):
        u = Usuario(discord_id=f"jug-{i}", discord_username=f"Jugador{i}")
        db.add(u)
        jugadores.append(u)
    db.flush()

    for u in jugadores:
        db.add(
            MiembroEquipo(equipo_id=equipo.id, juego_id=juego.id, usuario_id=u.id)
        )
    db.commit()

    return {
        "juego": juego,
        "edicion": edicion,
        "equipo": equipo,
        "capitan": capitan,
        "jugadores": jugadores,
    }


def auth(u: Usuario) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {crear_access_token(u.id, u.discord_id, u.es_organizador)}"
    }


def dar_identidad(db, escenario, usuarios):
    for i, u in enumerate(usuarios):
        db.add(
            IdentidadDeJuego(
                usuario_id=u.id,
                juego_id=escenario["juego"].id,
                identidad={"nick": u.discord_username, "id_juego": f"{1000 + i}"},
                clave_identidad=f"{1000 + i}",
            )
        )
    db.commit()


def inscribir(cliente, escenario, quien=None):
    """Sin `jugadores`: el roster sale del equipo."""
    return cliente.post(
        f"/api/ediciones/{escenario['edicion'].id}/inscripciones",
        json={
            "nombre_equipo": escenario["equipo"].nombre,
            "equipo_id": escenario["equipo"].id,
        },
        headers=auth(quien or escenario["capitan"]),
    )


class TestElRosterSaleDelEquipo:
    def test_se_inscribe_sin_mandar_un_solo_jugador(self, cliente, escenario, db):
        dar_identidad(db, escenario, escenario["jugadores"][:TITULARES])
        r = inscribir(cliente, escenario)
        assert r.status_code == 201, r.text

        inscripcion = db.query(Inscripcion).one()
        assert db.query(Jugador).filter_by(inscripcion_id=inscripcion.id).count() == TITULARES

    def test_las_identidades_son_las_que_cargo_cada_uno(self, cliente, escenario, db):
        dar_identidad(db, escenario, escenario["jugadores"][:TITULARES])
        inscribir(cliente, escenario)

        nicks = {j.identidad["nick"] for j in db.query(Jugador).all()}
        assert nicks == {"Capitan", "Jugador1", "Jugador2"}

    def test_el_dueno_del_equipo_queda_de_capitan(self, cliente, escenario, db):
        dar_identidad(db, escenario, escenario["jugadores"][:TITULARES])
        inscribir(cliente, escenario)

        capitan = db.query(Jugador).filter_by(es_capitan=True).one()
        assert capitan.identidad["nick"] == "Capitan"

    def test_todo_el_plantel_queda_habilitado_a_reportar(self, cliente, escenario, db):
        """Antes solo el capitán quedaba vinculado a una cuenta, y de ahí
        salía que 50 de 52 inscripciones no pudieran reportar."""
        dar_identidad(db, escenario, escenario["jugadores"][:TITULARES])
        inscribir(cliente, escenario)

        assert all(j.discord_id for j in db.query(Jugador).all())


class TestNoSeEntraIncompleto:
    def test_con_menos_de_los_titulares_se_rechaza(self, cliente, escenario, db):
        dar_identidad(db, escenario, escenario["jugadores"][: TITULARES - 1])
        r = inscribir(cliente, escenario)
        assert r.status_code == 409
        assert db.query(Inscripcion).count() == 0

    def test_el_error_dice_a_quien_le_falta(self, cliente, escenario, db):
        dar_identidad(db, escenario, escenario["jugadores"][: TITULARES - 1])
        detalle = inscribir(cliente, escenario).json()["detail"]
        assert "Jugador2" in detalle

    def test_a_los_que_faltan_se_les_avisa(self, cliente, escenario, db):
        """Son los únicos que pueden destrabarlo: el capitán no puede
        cargar el ID por ellos."""
        dar_identidad(db, escenario, escenario["jugadores"][: TITULARES - 1])
        inscribir(cliente, escenario)

        avisados = {n.usuario_id for n in db.query(Notificacion).all()}
        sin_identidad = {u.id for u in escenario["jugadores"][TITULARES - 1 :]}
        assert avisados == sin_identidad

    def test_el_aviso_sobrevive_al_rechazo(self, cliente, escenario, db):
        """La inscripción se revierte, el aviso no — si se fuera con el
        rollback, nadie se enteraría de por qué no entraron."""
        dar_identidad(db, escenario, escenario["jugadores"][: TITULARES - 1])
        inscribir(cliente, escenario)
        assert db.query(Notificacion).count() > 0

    def test_rechazar_no_renombra_el_equipo(self, cliente, escenario, db):
        """El commit del aviso no puede llevarse puesto un renombre de un
        alta que no entró."""
        dar_identidad(db, escenario, escenario["jugadores"][: TITULARES - 1])
        cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones",
            json={"nombre_equipo": "Nombre Nuevo", "equipo_id": escenario["equipo"].id},
            headers=auth(escenario["capitan"]),
        )
        assert db.get(Equipo, escenario["equipo"].id).nombre == "Dragons"

    def test_un_equipo_sin_miembros_no_se_puede_inscribir(self, cliente, escenario, db):
        db.query(MiembroEquipo).delete()
        db.commit()
        r = inscribir(cliente, escenario)
        assert r.status_code == 409
        assert "no tiene jugadores" in r.json()["detail"]

    def test_el_que_se_fue_del_equipo_no_cuenta(self, cliente, escenario, db):
        dar_identidad(db, escenario, escenario["jugadores"][:TITULARES])
        miembro = (
            db.query(MiembroEquipo)
            .filter_by(usuario_id=escenario["jugadores"][2].id)
            .one()
        )
        miembro.esta_activo = False
        db.commit()

        assert inscribir(cliente, escenario).status_code == 409


class TestElFormularioViejoSigueAndando:
    """Mandar `jugadores` a mano sigue siendo válido: es el camino de los
    torneos que apagan `requiere_equipo_permanente`."""

    def test_con_jugadores_explicitos_no_mira_el_equipo(self, cliente, escenario, db):
        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones",
            json={
                "nombre_equipo": "Dragons",
                "equipo_id": escenario["equipo"].id,
                "jugadores": [
                    {"identidad": {"nick": f"Tipeado{i}", "id_juego": f"{i}"}}
                    for i in range(TITULARES)
                ],
            },
            headers=auth(escenario["capitan"]),
        )
        assert r.status_code == 201, r.text
        nicks = {j.identidad["nick"] for j in db.query(Jugador).all()}
        assert nicks == {"Tipeado0", "Tipeado1", "Tipeado2"}


class TestNoSeFiltraElRosterAjeno:
    def test_inscribir_el_equipo_de_otro_sigue_prohibido(self, cliente, escenario, db):
        """Resolver el equipo tiene que pasar ANTES de armar el roster: al
        revés, mandar el equipo_id de otro con la lista vacía devolvería su
        plantel completo en la respuesta."""
        dar_identidad(db, escenario, escenario["jugadores"][:TITULARES])
        ajeno = Usuario(discord_id="aje", discord_username="Ajeno")
        db.add(ajeno)
        db.commit()

        r = inscribir(cliente, escenario, quien=ajeno)
        assert r.status_code == 403
        assert "Dragons" not in str(r.json().get("detail", ""))
