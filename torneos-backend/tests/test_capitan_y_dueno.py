"""Quien registra el equipo es su capitán y su dueño.

Antes eran dos permisos separados que nunca se conectaban: el dueño
(`Equipo.propietario_usuario_id`, por id de usuario) podía inscribir y
renombrar el equipo; el capitán (`Jugador.es_capitan` + `discord_id`) podía
reportar resultados. Coincidían por casualidad del flujo, y cuando se
separaban quedaban dos medias personas — una que administra el equipo pero no
puede reportar, otra que reporta pero no puede reinscribirlo.

Peor: la cuenta a vincular la elegía el CLIENTE. Podía mandar el `discord_id`
de cualquier jugador, o sea reclamar la cuenta de otro y quedar habilitado a
operar por un equipo ajeno.

Ahora la cuenta sale de la sesión, y quien inscribe queda de las dos cosas.
Referencia: Battlefy, donde el que crea el equipo es el capitán y el rol se
transfiere explícitamente.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.enums import EstadoEdicion, ModeloCompetencia
from app.main import app
from app.models import Edicion, Equipo, Inscripcion, Juego, Torneo, Usuario


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

    ana = Usuario(discord_id="cuenta-de-ana", discord_username="Ana")
    beto = Usuario(discord_id="cuenta-de-beto", discord_username="Beto")
    org = Usuario(discord_id="org", discord_username="Org", es_organizador=True)
    db.add_all([ana, beto, org])
    db.commit()
    return {"edicion": edicion, "ana": ana, "beto": beto, "organizador": org}


def auth(u: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(u.id, u.discord_id, u.es_organizador)}"}


def roster(*nicks, discord_para_todos=None):
    return [
        {
            "identidad": {"nick": n, "id_juego": f"id-{n}"},
            "es_capitan": i == 0,
            **({"discord_id": discord_para_todos} if discord_para_todos else {}),
        }
        for i, n in enumerate(nicks)
    ]


def inscribir(cliente, escenario, quien=None, nicks=("ana", "beto"), **kwargs):
    return cliente.post(
        f"/api/ediciones/{escenario['edicion'].id}/inscripciones",
        json={"nombre_equipo": "Dragons", "jugadores": roster(*nicks, **kwargs)},
        headers=auth(quien) if quien else {},
    )


class TestQuienRegistraQuedaDeLasDosCosas:
    def test_queda_de_dueno_del_equipo(self, cliente, db, escenario):
        r = inscribir(cliente, escenario, quien=escenario["ana"])
        assert r.status_code == 201, r.text

        equipo_id = r.json()["inscripcion"]["equipo"]["id"]
        assert db.get(Equipo, equipo_id).propietario_usuario_id == escenario["ana"].id

    def test_queda_de_capitan_de_la_inscripcion(self, cliente, db, escenario):
        r = inscribir(cliente, escenario, quien=escenario["ana"])
        insc = db.get(Inscripcion, r.json()["inscripcion"]["id"])

        capitan = next(j for j in insc.jugadores if j.es_capitan)
        assert capitan.discord_id == escenario["ana"].discord_id

    def test_puede_reportar_y_reinscribir(self, cliente, db, escenario):
        """El punto de unificarlo: antes podías tener una de las dos cosas."""
        r = inscribir(cliente, escenario, quien=escenario["ana"])
        insc_id = r.json()["inscripcion"]["id"]

        # Operar dentro del torneo (permiso de capitán)
        editado = cliente.patch(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc_id}",
            json={"nombre_equipo": "Dragons", "jugadores": roster("ana", "carlos")},
            headers=auth(escenario["ana"]),
        )
        assert editado.status_code == 200, editado.text

        # Administrar el equipo (permiso de dueño)
        mios = cliente.get("/api/equipos/mios", headers=auth(escenario["ana"]))
        assert [e["nombre"] for e in mios.json()] == ["Dragons"]


class TestNadieVinculaLaCuentaDeOtro:
    def test_no_se_puede_reclamar_la_cuenta_ajena(self, cliente, db, escenario):
        """El agujero que se cierra: mandar el discord de otro en el
        formulario y quedar habilitado a operar por su equipo."""
        r = inscribir(
            cliente, escenario, quien=escenario["ana"],
            discord_para_todos=escenario["beto"].discord_id,
        )
        insc = db.get(Inscripcion, r.json()["inscripcion"]["id"])

        vinculados = {j.discord_id for j in insc.jugadores if j.discord_id}
        assert escenario["beto"].discord_id not in vinculados
        assert vinculados == {escenario["ana"].discord_id}

    def test_solo_el_capitan_queda_vinculado(self, cliente, db, escenario):
        r = inscribir(cliente, escenario, quien=escenario["ana"])
        insc = db.get(Inscripcion, r.json()["inscripcion"]["id"])

        con_cuenta = [j for j in insc.jugadores if j.discord_id]
        assert len(con_cuenta) == 1
        assert con_cuenta[0].es_capitan

    def test_sin_sesion_no_se_vincula_nadie(self, cliente, db, escenario):
        """Inscribirse sin cuenta sigue permitido, pero entonces nadie queda
        habilitado a reportar — y el aviso de la respuesta ya lo dice."""
        r = inscribir(cliente, escenario, discord_para_todos="cuenta-de-beto")
        insc = db.get(Inscripcion, r.json()["inscripcion"]["id"])

        assert all(j.discord_id is None for j in insc.jugadores)


class TestTransferirCapitania:
    def _inscribir(self, cliente, escenario):
        r = inscribir(cliente, escenario, quien=escenario["ana"])
        return r.json()["inscripcion"]

    def test_el_capitan_puede_entregar_el_rol(self, cliente, db, escenario):
        insc = self._inscribir(cliente, escenario)
        otro = next(j for j in insc["jugadores"] if not j["es_capitan"])

        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc['id']}"
            f"/transferir-capitania?jugador_id={otro['id']}",
            headers=auth(escenario["ana"]),
        )
        assert r.status_code == 200, r.text

        actualizada = db.get(Inscripcion, insc["id"])
        capitan = next(j for j in actualizada.jugadores if j.es_capitan)
        assert capitan.id == otro["id"]

    def test_hay_siempre_exactamente_un_capitan(self, cliente, db, escenario):
        insc = self._inscribir(cliente, escenario)
        otro = next(j for j in insc["jugadores"] if not j["es_capitan"])
        cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc['id']}"
            f"/transferir-capitania?jugador_id={otro['id']}",
            headers=auth(escenario["ana"]),
        )
        actualizada = db.get(Inscripcion, insc["id"])
        assert sum(j.es_capitan for j in actualizada.jugadores) == 1

    def test_el_nuevo_capitan_no_hereda_la_cuenta(self, cliente, db, escenario):
        """El rol se muda, la identidad no: nadie puede afirmar de quién es
        la cuenta del nuevo capitán sin que él lo confirme."""
        insc = self._inscribir(cliente, escenario)
        otro = next(j for j in insc["jugadores"] if not j["es_capitan"])
        cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc['id']}"
            f"/transferir-capitania?jugador_id={otro['id']}",
            headers=auth(escenario["ana"]),
        )
        actualizada = db.get(Inscripcion, insc["id"])
        nuevo = next(j for j in actualizada.jugadores if j.es_capitan)
        assert nuevo.discord_id is None

    def test_un_ajeno_no_puede_autoproclamarse(self, cliente, db, escenario):
        insc = self._inscribir(cliente, escenario)
        otro = next(j for j in insc["jugadores"] if not j["es_capitan"])

        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc['id']}"
            f"/transferir-capitania?jugador_id={otro['id']}",
            headers=auth(escenario["beto"]),
        )
        assert r.status_code == 403

    def test_el_organizador_puede_destrabar(self, cliente, db, escenario):
        """El caso de "el capitán desapareció"."""
        insc = self._inscribir(cliente, escenario)
        otro = next(j for j in insc["jugadores"] if not j["es_capitan"])

        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc['id']}"
            f"/transferir-capitania?jugador_id={otro['id']}",
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 200, r.text

    def test_no_se_transfiere_a_alguien_de_otro_equipo(self, cliente, db, escenario):
        insc = self._inscribir(cliente, escenario)
        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc['id']}"
            "/transferir-capitania?jugador_id=99999",
            headers=auth(escenario["ana"]),
        )
        assert r.status_code == 404

    def test_transferirsela_al_actual_no_tiene_sentido(self, cliente, db, escenario):
        insc = self._inscribir(cliente, escenario)
        capitan = next(j for j in insc["jugadores"] if j["es_capitan"])
        r = cliente.post(
            f"/api/ediciones/{escenario['edicion'].id}/inscripciones/{insc['id']}"
            f"/transferir-capitania?jugador_id={capitan['id']}",
            headers=auth(escenario["ana"]),
        )
        assert r.status_code == 422
