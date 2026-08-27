"""El puente entre los rosters viejos y el modelo de cuentas.

No hay migración automática posible. Los 263 jugadores históricos son texto
que tipeó un capitán, sin cuenta detrás, y una cuenta no se fabrica desde un
apodo. Lo único que sabe que "Lyon" del roster es esta persona es un humano.

`vincular-discord` es donde ese humano lo dice, así que ahí se migra: al
vincular, la persona se lleva su identidad de juego, entra al roster
permanente del equipo y —si era el capitán— queda de dueño. Eso último
desatasca lo que hoy bloquea todo: los equipos existentes no tienen dueño,
así que nadie puede reinscribirlos.

Este endpoint no tenía ningún test, y por eso sobrevivió el bug de que
aceptaba un `discord_id` que no existía: el jugador figuraba vinculado y
seguía sin poder reportar nada.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.enums import EstadoEdicion, ModeloCompetencia
from app.main import app
from app.models import (
    Edicion,
    Equipo,
    IdentidadDeJuego,
    Inscripcion,
    Juego,
    Jugador,
    MiembroEquipo,
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
    juego = Juego(
        codigo="mlbb",
        nombre="Mobile Legends",
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
    edicion = Edicion(
        torneo_id=torneo.id, juego_id=juego.id, numero=1, nombre="T1",
        slug="copa-t1", estado=EstadoEdicion.INSCRIPCIONES_ABIERTAS,
        # Reproduce los datos viejos: roster tipeado, sin cuentas.
        requiere_equipo_permanente=False,
    )
    db.add(edicion)
    db.flush()

    org = Usuario(discord_id="org", discord_username="Org", es_organizador=True)
    lyon = Usuario(discord_id="lyon-real", discord_username="Lyon")
    otro = Usuario(discord_id="otro-real", discord_username="Otro")
    db.add_all([org, lyon, otro])
    db.commit()

    return {"juego": juego, "edicion": edicion, "org": org, "lyon": lyon, "otro": otro}


def auth(u: Usuario) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {crear_access_token(u.id, u.discord_id, u.es_organizador)}"
    }


@pytest.fixture
def inscripcion_vieja(cliente, escenario, db):
    """Una inscripción como las que ya existen: sin dueño y sin cuentas."""
    r = cliente.post(
        f"/api/ediciones/{escenario['edicion'].id}/inscripciones",
        json={
            "nombre_equipo": "Dragons",
            "jugadores": [
                {"identidad": {"nick": "Lyon", "id_juego": "111"}, "es_capitan": True},
                {"identidad": {"nick": "Compa", "id_juego": "222"}},
            ],
        },
    )
    assert r.status_code == 201, r.text
    inscripcion = db.query(Inscripcion).one()
    assert db.get(Equipo, inscripcion.equipo_id).propietario_usuario_id is None
    return inscripcion


def vincular(cliente, escenario, inscripcion, jugador, discord_id, quien=None):
    return cliente.patch(
        f"/api/ediciones/{escenario['edicion'].id}/inscripciones/"
        f"{inscripcion.id}/jugadores/{jugador.id}/vincular-discord",
        params={"discord_id": discord_id},
        headers=auth(quien or escenario["org"]),
    )


def capitan_de(db, inscripcion):
    return (
        db.query(Jugador)
        .filter_by(inscripcion_id=inscripcion.id, es_capitan=True)
        .one()
    )


class TestElBugQueNoTeniaTest:
    def test_no_se_puede_vincular_a_una_cuenta_que_no_existe(
        self, cliente, escenario, inscripcion_vieja, db
    ):
        """Antes se aceptaba: el jugador figuraba vinculado y seguía sin
        poder reportar nada. Así quedaron datos apuntando a la nada."""
        r = vincular(
            cliente, escenario, inscripcion_vieja,
            capitan_de(db, inscripcion_vieja), "no-existe-esta-cuenta",
        )
        assert r.status_code == 404
        assert "registrarse" in r.json()["detail"]

    def test_solo_el_staff_de_la_edicion_puede(
        self, cliente, escenario, inscripcion_vieja, db
    ):
        r = vincular(
            cliente, escenario, inscripcion_vieja,
            capitan_de(db, inscripcion_vieja), "lyon-real",
            quien=escenario["otro"],
        )
        assert r.status_code == 403


class TestVincularMigraALaPersona:
    def test_se_lleva_su_identidad_de_juego(
        self, cliente, escenario, inscripcion_vieja, db
    ):
        """Los datos ya estaban en el roster; lo que faltaba era de quién
        son."""
        vincular(
            cliente, escenario, inscripcion_vieja,
            capitan_de(db, inscripcion_vieja), "lyon-real",
        )
        identidad = db.query(IdentidadDeJuego).one()
        assert identidad.usuario_id == escenario["lyon"].id
        assert identidad.identidad["id_juego"] == "111"

    def test_entra_al_roster_permanente(
        self, cliente, escenario, inscripcion_vieja, db
    ):
        vincular(
            cliente, escenario, inscripcion_vieja,
            capitan_de(db, inscripcion_vieja), "lyon-real",
        )
        miembro = db.query(MiembroEquipo).one()
        assert miembro.usuario_id == escenario["lyon"].id
        assert miembro.equipo_id == inscripcion_vieja.equipo_id

    def test_el_capitan_queda_de_dueno_del_equipo(
        self, cliente, escenario, inscripcion_vieja, db
    ):
        """Es lo que desatasca todo: sin dueño nadie puede reinscribir
        ninguno de los equipos que ya existen."""
        vincular(
            cliente, escenario, inscripcion_vieja,
            capitan_de(db, inscripcion_vieja), "lyon-real",
        )
        equipo = db.get(Equipo, inscripcion_vieja.equipo_id)
        assert equipo.propietario_usuario_id == escenario["lyon"].id

    def test_un_jugador_comun_no_se_queda_con_el_equipo(
        self, cliente, escenario, inscripcion_vieja, db
    ):
        comun = (
            db.query(Jugador)
            .filter_by(inscripcion_id=inscripcion_vieja.id, es_capitan=False)
            .one()
        )
        vincular(cliente, escenario, inscripcion_vieja, comun, "otro-real")

        equipo = db.get(Equipo, inscripcion_vieja.equipo_id)
        assert equipo.propietario_usuario_id is None
        assert db.query(MiembroEquipo).count() == 1

    def test_vincular_dos_veces_no_duplica_nada(
        self, cliente, escenario, inscripcion_vieja, db
    ):
        jugador = capitan_de(db, inscripcion_vieja)
        vincular(cliente, escenario, inscripcion_vieja, jugador, "lyon-real")
        vincular(cliente, escenario, inscripcion_vieja, jugador, "lyon-real")

        assert db.query(MiembroEquipo).count() == 1
        assert db.query(IdentidadDeJuego).count() == 1


class TestLoQueLaMigracionNoPisa:
    def test_si_la_persona_ya_cargo_su_identidad_gana_la_suya(
        self, cliente, escenario, inscripcion_vieja, db
    ):
        """El dato es de ella, no del roster que alguien tipeó por ella."""
        db.add(
            IdentidadDeJuego(
                usuario_id=escenario["lyon"].id,
                juego_id=escenario["juego"].id,
                identidad={"nick": "LyonReal", "id_juego": "999"},
                clave_identidad="999",
            )
        )
        db.commit()

        vincular(
            cliente, escenario, inscripcion_vieja,
            capitan_de(db, inscripcion_vieja), "lyon-real",
        )
        identidad = db.query(IdentidadDeJuego).one()
        assert identidad.identidad["id_juego"] == "999"

    def test_si_esa_identidad_ya_es_de_otro_se_vincula_igual_sin_robarla(
        self, cliente, escenario, inscripcion_vieja, db
    ):
        """Un roster viejo puede tener el ID de otra persona. Pisarlo sería
        creerle más a un dato tipeado hace meses que al que su dueño cargó
        con su cuenta."""
        db.add(
            IdentidadDeJuego(
                usuario_id=escenario["otro"].id,
                juego_id=escenario["juego"].id,
                identidad={"nick": "Otro", "id_juego": "111"},
                clave_identidad="111",
            )
        )
        db.commit()

        r = vincular(
            cliente, escenario, inscripcion_vieja,
            capitan_de(db, inscripcion_vieja), "lyon-real",
        )
        assert r.status_code == 200

        assert db.query(IdentidadDeJuego).count() == 1
        assert db.query(IdentidadDeJuego).one().usuario_id == escenario["otro"].id
        # Se vinculó igual: el equipo y la cuenta quedan conectados aunque
        # la identidad quede en disputa.
        assert db.query(MiembroEquipo).one().usuario_id == escenario["lyon"].id


class TestDespuesDeMigrarSePuedeReinscribir:
    def test_el_equipo_migrado_ya_sirve_para_el_modelo_nuevo(
        self, cliente, escenario, inscripcion_vieja, db
    ):
        """La prueba de que el puente sirve: migrás a los dos jugadores y el
        equipo se puede inscribir en el torneo siguiente sin tipear nada."""
        vincular(
            cliente, escenario, inscripcion_vieja,
            capitan_de(db, inscripcion_vieja), "lyon-real",
        )
        comun = (
            db.query(Jugador)
            .filter_by(inscripcion_id=inscripcion_vieja.id, es_capitan=False)
            .one()
        )
        vincular(cliente, escenario, inscripcion_vieja, comun, "otro-real")

        siguiente = Edicion(
            torneo_id=escenario["edicion"].torneo_id,
            juego_id=escenario["juego"].id,
            numero=2, nombre="T2", slug="copa-t2",
            estado=EstadoEdicion.INSCRIPCIONES_ABIERTAS,
        )
        db.add(siguiente)
        db.commit()

        r = cliente.post(
            f"/api/ediciones/{siguiente.id}/inscripciones",
            json={"nombre_equipo": "Dragons", "equipo_id": inscripcion_vieja.equipo_id},
            headers=auth(escenario["lyon"]),
        )
        assert r.status_code == 201, r.text
        nueva = db.query(Inscripcion).filter_by(edicion_id=siguiente.id).one()
        assert db.query(Jugador).filter_by(inscripcion_id=nueva.id).count() == 2
