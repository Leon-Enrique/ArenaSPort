"""Roster permanente e invitaciones.

El cambio que se prueba acá es de fondo: un miembro de equipo pasa a ser una
persona con cuenta, no un texto que tipeó el capitán. De eso salen las dos
cosas que más se vigilan en este archivo:

  - **La identidad la carga su dueño.** El capitán no puede meter a nadie;
    el jugador entra aceptando una invitación y escribe sus propios datos.
  - **Una invitación no es un oráculo.** Todo lo que no se puede usar
    responde 404 igual —vencida, revocada, dirigida a otro, inexistente—
    para que probando tokens no se pueda averiguar cuáles existen.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.enums import ModeloCompetencia
from app.main import app
from app.models import Equipo, InvitacionAEquipo, Juego, MiembroEquipo, Usuario


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
        titulares_requeridos=5,
        suplentes_maximos=2,
        campos_identidad={
            "campos": [
                {"nombre": "nick", "etiqueta": "Nick", "requerido": True},
                {"nombre": "id_juego", "etiqueta": "ID", "requerido": True},
                {"nombre": "server", "etiqueta": "Server", "requerido": False},
            ],
            "clave_unica": ["id_juego"],
        },
    )
    db.add(juego)
    db.flush()

    duenio = Usuario(discord_id="due-1", discord_username="Dueño")
    jugador = Usuario(discord_id="jug-1", discord_username="Jugador")
    otro = Usuario(discord_id="jug-2", discord_username="Otro")
    ajeno = Usuario(discord_id="aje-1", discord_username="Ajeno")
    db.add_all([duenio, jugador, otro, ajeno])
    db.flush()

    equipo = Equipo(nombre="Dragons", propietario_usuario_id=duenio.id)
    db.add(equipo)
    db.commit()

    return {
        "juego": juego,
        "equipo": equipo,
        "duenio": duenio,
        "jugador": jugador,
        "otro": otro,
        "ajeno": ajeno,
    }


def auth(u: Usuario) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {crear_access_token(u.id, u.discord_id, u.es_organizador)}"
    }


def identidad(nick="Lyon", id_juego="123456789"):
    return {"nick": nick, "id_juego": id_juego, "server": "2251"}


def invitar(cliente, escenario, destino=None, dias=7):
    cuerpo = {"dias_de_vida": dias}
    if destino is not None:
        cuerpo["usuario_destino_id"] = destino.id
    return cliente.post(
        f"/api/equipos/{escenario['equipo'].id}/invitaciones",
        json=cuerpo,
        headers=auth(escenario["duenio"]),
    )


def aceptar(cliente, token, quien, ident=None):
    return cliente.post(
        f"/api/invitaciones/{token}/aceptar",
        json={"identidad": ident or identidad()},
        headers=auth(quien),
    )


class TestQuienPuedeInvitar:
    def test_el_duenio_del_equipo_puede(self, cliente, escenario):
        r = invitar(cliente, escenario)
        assert r.status_code == 201
        assert r.json()["token"]

    def test_un_ajeno_no_puede(self, cliente, escenario):
        r = cliente.post(
            f"/api/equipos/{escenario['equipo'].id}/invitaciones",
            json={},
            headers=auth(escenario["ajeno"]),
        )
        assert r.status_code == 403

    def test_sin_sesion_no_se_puede(self, cliente, escenario):
        r = cliente.post(f"/api/equipos/{escenario['equipo'].id}/invitaciones", json={})
        assert r.status_code == 401

    def test_un_equipo_inexistente_da_404(self, cliente, escenario):
        r = cliente.post(
            "/api/equipos/999999/invitaciones",
            json={},
            headers=auth(escenario["duenio"]),
        )
        assert r.status_code == 404


class TestAceptarUnaInvitacion:
    def test_el_link_abierto_lo_acepta_cualquiera_con_cuenta(self, cliente, escenario, db):
        token = invitar(cliente, escenario).json()["token"]
        r = aceptar(cliente, token, escenario["jugador"])
        assert r.status_code == 201
        assert r.json()["usuario_id"] == escenario["jugador"].id

        miembro = db.query(MiembroEquipo).one()
        assert miembro.equipo_id == escenario["equipo"].id
        assert miembro.identidad["nick"] == "Lyon"

    def test_la_identidad_la_carga_el_jugador_y_queda_a_su_nombre(
        self, cliente, escenario, db
    ):
        """El punto del rediseño: la fila es del jugador, no del capitán."""
        token = invitar(cliente, escenario).json()["token"]
        aceptar(cliente, token, escenario["jugador"], identidad(nick="ElegidoPorMi"))

        miembro = db.query(MiembroEquipo).one()
        assert miembro.usuario_id == escenario["jugador"].id
        assert miembro.identidad["nick"] == "ElegidoPorMi"

    def test_la_invitacion_dirigida_solo_la_acepta_su_destinatario(
        self, cliente, escenario
    ):
        token = invitar(cliente, escenario, destino=escenario["jugador"]).json()["token"]
        assert aceptar(cliente, token, escenario["jugador"]).status_code == 201

    def test_una_invitacion_dirigida_a_otro_responde_404(self, cliente, escenario):
        """404 y no 403: decir 'existe pero no es tuya' convertiría la ruta
        en un oráculo para adivinar tokens."""
        token = invitar(cliente, escenario, destino=escenario["jugador"]).json()["token"]
        assert aceptar(cliente, token, escenario["otro"]).status_code == 404

    def test_sin_los_campos_obligatorios_del_juego_no_entra(self, cliente, escenario):
        token = invitar(cliente, escenario).json()["token"]
        r = aceptar(cliente, token, escenario["jugador"], {"nick": "SinId"})
        assert r.status_code == 422
        assert "id_juego" in r.json()["detail"]

    def test_una_invitacion_se_usa_una_sola_vez(self, cliente, escenario):
        token = invitar(cliente, escenario).json()["token"]
        assert aceptar(cliente, token, escenario["jugador"]).status_code == 201
        assert aceptar(cliente, token, escenario["otro"]).status_code == 404

    def test_no_se_puede_entrar_dos_veces_al_mismo_equipo(self, cliente, escenario):
        t1 = invitar(cliente, escenario).json()["token"]
        t2 = invitar(cliente, escenario).json()["token"]
        assert aceptar(cliente, t1, escenario["jugador"]).status_code == 201
        assert aceptar(cliente, t2, escenario["jugador"]).status_code == 409

    def test_dos_personas_no_pueden_declarar_la_misma_identidad_de_juego(
        self, cliente, escenario
    ):
        """El ID de juego identifica a una persona: dos cuentas de la
        plataforma con el mismo ID son la misma persona entrando dos veces."""
        t1 = invitar(cliente, escenario).json()["token"]
        t2 = invitar(cliente, escenario).json()["token"]
        assert aceptar(cliente, t1, escenario["jugador"]).status_code == 201
        r = aceptar(cliente, t2, escenario["otro"], identidad(nick="OtroNick"))
        assert r.status_code == 409


class TestInvitacionesQueNoSirven:
    """Todas responden 404, y esa uniformidad es el punto."""

    def test_un_token_inventado(self, cliente, escenario):
        assert aceptar(cliente, "no-existe", escenario["jugador"]).status_code == 404

    def test_una_vencida(self, cliente, escenario, db):
        token = invitar(cliente, escenario).json()["token"]
        inv = db.query(InvitacionAEquipo).one()
        inv.expira_at = datetime.now().astimezone() - timedelta(days=1)
        db.commit()
        assert aceptar(cliente, token, escenario["jugador"]).status_code == 404

    def test_una_revocada(self, cliente, escenario, db):
        creada = invitar(cliente, escenario).json()
        r = cliente.delete(
            f"/api/equipos/{escenario['equipo'].id}/invitaciones/{creada['id']}",
            headers=auth(escenario["duenio"]),
        )
        assert r.status_code == 200
        assert aceptar(cliente, creada["token"], escenario["jugador"]).status_code == 404

    def test_revocar_una_ya_aceptada_no_tiene_sentido(self, cliente, escenario):
        creada = invitar(cliente, escenario).json()
        aceptar(cliente, creada["token"], escenario["jugador"])
        r = cliente.delete(
            f"/api/equipos/{escenario['equipo'].id}/invitaciones/{creada['id']}",
            headers=auth(escenario["duenio"]),
        )
        assert r.status_code == 409


class TestElRosterPermanente:
    def test_el_duenio_ve_a_sus_miembros(self, cliente, escenario):
        token = invitar(cliente, escenario).json()["token"]
        aceptar(cliente, token, escenario["jugador"])

        r = cliente.get(
            f"/api/equipos/{escenario['equipo'].id}/miembros",
            headers=auth(escenario["duenio"]),
        )
        assert r.status_code == 200
        assert [m["usuario_nombre"] for m in r.json()] == ["Jugador"]

    def test_un_ajeno_no_ve_el_roster(self, cliente, escenario):
        """Acá van los datos de juego de cada persona; el perfil público del
        equipo es otra ruta."""
        r = cliente.get(
            f"/api/equipos/{escenario['equipo'].id}/miembros",
            headers=auth(escenario["ajeno"]),
        )
        assert r.status_code == 403

    def test_el_que_se_fue_no_aparece(self, cliente, escenario, db):
        token = invitar(cliente, escenario).json()["token"]
        aceptar(cliente, token, escenario["jugador"])

        db.query(MiembroEquipo).one().esta_activo = False
        db.commit()

        r = cliente.get(
            f"/api/equipos/{escenario['equipo'].id}/miembros",
            headers=auth(escenario["duenio"]),
        )
        assert r.json() == []

    def test_volver_al_equipo_reusa_la_fila_en_vez_de_duplicarla(
        self, cliente, escenario, db
    ):
        token = invitar(cliente, escenario).json()["token"]
        aceptar(cliente, token, escenario["jugador"])
        db.query(MiembroEquipo).one().esta_activo = False
        db.commit()

        token2 = invitar(cliente, escenario).json()["token"]
        assert aceptar(cliente, token2, escenario["jugador"]).status_code == 201
        assert db.query(MiembroEquipo).count() == 1


class TestElTokenNoCircula:
    def test_el_listado_de_invitaciones_no_lo_incluye(self, cliente, escenario):
        """Se devuelve una sola vez, al crearla."""
        invitar(cliente, escenario)
        r = cliente.get(
            f"/api/equipos/{escenario['equipo'].id}/invitaciones",
            headers=auth(escenario["duenio"]),
        )
        assert r.status_code == 200
        assert r.json()
        assert all("token" not in inv for inv in r.json())
