"""Staff de un torneo: ayudar a correr uno sin ser organizador global.

`es_organizador` es una bandera global: quien la tiene administra TODOS los
torneos de la plataforma. Eso hacía imposible pedir una mano puntual — para
que alguien te ayudara en una copa había que darle acceso a todo, o hacerlo
vos.

Lo que se vigila acá es que el alcance quede acotado de verdad: que el staff
de un torneo no pueda tocar otro, y que delegar la operación no incluya
delegar quién más entra.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.enums import (
    EstadoEdicion,
    EstadoPartida,
    FormatoFase,
    ModeloCompetencia,
    RolStaff,
)
from app.main import app
from app.models import Disputa, Edicion, Equipo, Fase, Juego, Partida, StaffDeTorneo, Torneo, Usuario


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
    """Dos torneos distintos, para poder comprobar que el alcance no se
    desborda de uno al otro."""
    juego = Juego(
        codigo="mlbb", nombre="MLBB",
        modelo_competencia_default=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        titulares_requeridos=1, suplentes_maximos=0,
        campos_identidad={"campos": [{"nombre": "nick", "etiqueta": "N", "requerido": True}],
                          "clave_unica": ["nick"]},
    )
    db.add(juego)
    db.flush()

    datos = {}
    for clave, nombre in (("a", "Copa A"), ("b", "Copa B")):
        torneo = Torneo(nombre=nombre, slug=nombre.lower().replace(" ", "-"))
        db.add(torneo)
        db.flush()
        edicion = Edicion(
            torneo_id=torneo.id, juego_id=juego.id, numero=1, nombre="T1",
            slug=f"{torneo.slug}-t1", estado=EstadoEdicion.INSCRIPCIONES_ABIERTAS,
        )
        db.add(edicion)
        db.flush()
        fase = Fase(
            edicion_id=edicion.id, orden=1, nombre="F",
            modelo_competencia=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
            formato=FormatoFase.ELIMINACION_SIMPLE, config={"bo": 3},
        )
        db.add(fase)
        db.flush()
        partida = Partida(fase_id=fase.id, ronda=1, estado=EstadoPartida.PROGRAMADA)
        db.add(partida)
        db.flush()
        datos[clave] = {"torneo": torneo, "edicion": edicion, "fase": fase, "partida": partida}

    org = Usuario(discord_id="org", discord_username="Org", es_organizador=True)
    admin = Usuario(discord_id="admin", discord_username="Admin")
    arbitro = Usuario(discord_id="arb", discord_username="Arbitro")
    ajeno = Usuario(discord_id="ajeno", discord_username="Ajeno")
    db.add_all([org, admin, arbitro, ajeno])
    db.commit()

    # Staff SOLO de la Copa A
    db.add(StaffDeTorneo(torneo_id=datos["a"]["torneo"].id, usuario_id=admin.id,
                         rol=RolStaff.ADMINISTRADOR))
    db.add(StaffDeTorneo(torneo_id=datos["a"]["torneo"].id, usuario_id=arbitro.id,
                         rol=RolStaff.ARBITRO))
    db.commit()

    return {**datos, "organizador": org, "admin": admin, "arbitro": arbitro, "ajeno": ajeno}


def programar(cliente, escenario, copa, quien):
    """Operación de día de partido."""
    d = escenario[copa]
    return cliente.patch(
        f"/api/fases/{d['fase'].id}/partidas/{d['partida'].id}/programar",
        json={"programada_para": "2026-12-01T20:00:00+00:00"},
        headers=auth(quien),
    )


def crear_fase(cliente, escenario, copa, quien):
    """Operación de armado del torneo."""
    return cliente.post(
        f"/api/ediciones/{escenario[copa]['edicion'].id}/fases",
        json={"orden": 9, "nombre": "Nueva", "modelo_competencia": "enfrentamiento_directo",
              "formato": "eliminacion_simple", "config": {}},
        headers=auth(quien),
    )


class TestElArbitro:
    def test_puede_operar_el_dia_de_partido(self, cliente, escenario):
        assert programar(cliente, escenario, "a", escenario["arbitro"]).status_code == 200

    def test_no_arma_el_torneo(self, cliente, escenario):
        """Crear fases es una decisión de armado, no del día de partido."""
        r = crear_fase(cliente, escenario, "a", escenario["arbitro"])
        assert r.status_code == 403
        assert "administrador" in r.json()["detail"]


class TestElAdministrador:
    def test_arma_el_torneo(self, cliente, escenario):
        assert crear_fase(cliente, escenario, "a", escenario["admin"]).status_code == 201

    def test_tambien_opera_el_dia_de_partido(self, cliente, escenario):
        assert programar(cliente, escenario, "a", escenario["admin"]).status_code == 200

    def test_no_puede_repartir_roles(self, cliente, escenario):
        """Delegar la operación de un torneo no puede incluir delegar quién
        más entra: alcanzaría con delegar una vez para perder el control."""
        r = cliente.post(
            f"/api/torneos/{escenario['a']['torneo'].id}/staff",
            json={"usuario_id": escenario["ajeno"].id, "rol": "administrador"},
            headers=auth(escenario["admin"]),
        )
        assert r.status_code == 403


class TestElAlcanceNoSeDesborda:
    def test_el_staff_de_un_torneo_no_toca_el_otro(self, cliente, escenario):
        """El punto de todo esto: dar una mano en la Copa A no puede dar
        acceso a la Copa B."""
        assert programar(cliente, escenario, "a", escenario["admin"]).status_code == 200
        assert programar(cliente, escenario, "b", escenario["admin"]).status_code == 403

    def test_el_arbitro_tampoco(self, cliente, escenario):
        assert programar(cliente, escenario, "b", escenario["arbitro"]).status_code == 403

    def test_alguien_sin_rol_no_entra_a_ninguno(self, cliente, escenario):
        assert programar(cliente, escenario, "a", escenario["ajeno"]).status_code == 403
        assert programar(cliente, escenario, "b", escenario["ajeno"]).status_code == 403


class TestElOrganizadorGlobal:
    def test_entra_a_todos(self, cliente, escenario):
        """Delegar no le quita permisos a quien delega."""
        assert programar(cliente, escenario, "a", escenario["organizador"]).status_code == 200
        assert programar(cliente, escenario, "b", escenario["organizador"]).status_code == 200


class TestGestionDelStaff:
    def test_agregar_y_listar(self, cliente, db, escenario):
        torneo_id = escenario["b"]["torneo"].id
        r = cliente.post(
            f"/api/torneos/{torneo_id}/staff",
            json={"usuario_id": escenario["ajeno"].id, "rol": "arbitro"},
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 201, r.text

        listado = cliente.get(
            f"/api/torneos/{torneo_id}/staff", headers=auth(escenario["organizador"])
        ).json()
        assert [s["usuario_id"] for s in listado] == [escenario["ajeno"].id]
        assert listado[0]["usuario_nombre"] == "Ajeno"

    def test_agregar_dos_veces_cambia_el_rol(self, cliente, escenario):
        torneo_id = escenario["a"]["torneo"].id
        r = cliente.post(
            f"/api/torneos/{torneo_id}/staff",
            json={"usuario_id": escenario["arbitro"].id, "rol": "administrador"},
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 201
        assert r.json()["rol"] == "administrador"

    def test_quitar_el_acceso(self, cliente, escenario):
        torneo_id = escenario["a"]["torneo"].id
        r = cliente.delete(
            f"/api/torneos/{torneo_id}/staff/{escenario['admin'].id}",
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 204
        assert programar(cliente, escenario, "a", escenario["admin"]).status_code == 403

    def test_quitar_a_alguien_que_no_es_staff_da_404(self, cliente, escenario):
        r = cliente.delete(
            f"/api/torneos/{escenario['a']['torneo'].id}/staff/{escenario['ajeno'].id}",
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 404

    def test_un_usuario_inexistente_da_404(self, cliente, escenario):
        r = cliente.post(
            f"/api/torneos/{escenario['a']['torneo'].id}/staff",
            json={"usuario_id": 99999, "rol": "arbitro"},
            headers=auth(escenario["organizador"]),
        )
        assert r.status_code == 404


class TestElBuscadorDeUsuarios:
    """El buscador existe para poder armar el staff de un torneo eligiendo
    de una lista, en vez de tener que averiguar el id de alguien a mano.

    Lo que se vigila acá es que no se convierta en una puerta de atrás a
    `listar_usuarios`: el permiso es más bajo a propósito, así que lo que
    devuelve tiene que ser más chico.
    """

    def _buscar(self, cliente, quien, **params):
        return cliente.get("/api/usuarios/buscar", params=params, headers=auth(quien))

    def test_el_organizador_busca_por_nombre(self, cliente, escenario):
        r = self._buscar(cliente, escenario["organizador"], q="arb")
        assert r.status_code == 200
        assert [u["discord_username"] for u in r.json()] == ["Arbitro"]

    def test_no_hace_falta_acertar_las_mayusculas(self, cliente, escenario):
        r = self._buscar(cliente, escenario["organizador"], q="ARBIT")
        assert [u["discord_username"] for u in r.json()] == ["Arbitro"]

    def test_tambien_encuentra_por_discord_id_exacto(self, cliente, escenario):
        """Pegar el ID de Discord es la forma sin ambigüedad de encontrar a
        alguien cuando hay varios nombres parecidos."""
        r = self._buscar(cliente, escenario["organizador"], q="ajeno")
        assert [u["id"] for u in r.json()] == [escenario["ajeno"].id]

    def test_sin_termino_devuelve_a_todos(self, cliente, escenario):
        """Abrir el buscador sin escribir nada tiene que mostrar caras, no
        una lista vacía."""
        r = self._buscar(cliente, escenario["organizador"])
        assert len(r.json()) == 4

    def test_el_guion_bajo_no_es_un_comodin(self, cliente, escenario, db):
        """`_` significa 'cualquier carácter' en LIKE y es común en los
        nombres de Discord: sin escaparlo, buscar `leo_` traería `leon`."""
        db.add(Usuario(discord_id="leo_", discord_username="leo_pro"))
        db.add(Usuario(discord_id="leon", discord_username="leonardo"))
        db.commit()

        r = self._buscar(cliente, escenario["organizador"], q="leo_")
        assert [u["discord_username"] for u in r.json()] == ["leo_pro"]

    def test_no_ofrece_cuentas_desactivadas(self, cliente, escenario, db):
        """Darle acceso a una cuenta apagada sería darle acceso a nadie."""
        escenario["ajeno"].esta_activo = False
        db.commit()

        r = self._buscar(cliente, escenario["organizador"], q="ajeno")
        assert r.json() == []

    def test_no_expone_el_estado_de_permisos(self, cliente, escenario):
        """El permiso para llamar acá es más bajo que el de `GET /usuarios`,
        así que lo que devuelve tiene que ser más chico: nada de
        `puede_gestionar_organizadores` ni `esta_activo`."""
        fila = self._buscar(cliente, escenario["organizador"], q="arb").json()[0]
        assert set(fila) == {
            "id", "discord_id", "discord_username", "discord_avatar_url", "es_organizador",
        }

    def test_marca_a_quien_ya_es_organizador_global(self, cliente, escenario):
        """Para poder avisar que sumarlo no cambiaría nada: ya entra a todos
        los torneos."""
        fila = self._buscar(cliente, escenario["organizador"], q="Org").json()[0]
        assert fila["es_organizador"] is True

    def test_no_es_para_cualquiera(self, cliente, escenario):
        assert self._buscar(cliente, escenario["ajeno"], q="a").status_code == 403

    def test_el_staff_de_un_torneo_tampoco_lo_usa(self, cliente, escenario):
        """Sumar staff es del organizador global, así que el buscador que
        alimenta esa pantalla también."""
        assert self._buscar(cliente, escenario["admin"], q="a").status_code == 403

    def test_el_limite_no_se_puede_estirar(self, cliente, escenario):
        r = self._buscar(cliente, escenario["organizador"], limite=9999)
        assert r.status_code == 200
        assert len(r.json()) <= 50


class TestResolverDisputa:
    """`/disputas/{id}/resolver` era la última ruta que se había quedado en
    organizador global cuando se armó el staff por torneo: no tiene
    `fase_id` en la URL, así que el torneo no se podía resolver con un
    `get()` directo como en las demás rutas. `RequiereStaffDeDisputa`
    hace esa consulta extra (Disputa -> Partida -> Fase -> Edición ->
    Torneo).

    Alcanza con ser árbitro: resolver una disputa es trabajo de día de
    partido, igual que programar o corregir un resultado.
    """

    def _abrir_disputa(self, db, escenario, copa) -> Disputa:
        """Salta el flujo real de impugnación (que exige ser capitán de un
        equipo inscripto) y crea la disputa directo — acá lo que se prueba
        es quién puede RESOLVERLA, no cómo se abre."""
        equipo = Equipo(nombre="Equipo que reclama")
        db.add(equipo)
        db.flush()
        disputa = Disputa(
            partida_id=escenario[copa]["partida"].id,
            abierta_por_equipo_id=equipo.id,
            motivo="Reclamo de prueba",
        )
        db.add(disputa)
        db.commit()
        db.refresh(disputa)
        return disputa

    def _resolver(self, cliente, disputa, quien):
        return cliente.post(
            f"/api/disputas/{disputa.id}/resolver",
            json={"resolucion": "Resuelto en la prueba.", "accion": "reprogramar"},
            headers=auth(quien),
        )

    def test_el_arbitro_de_ese_torneo_puede_resolver(self, cliente, escenario, db):
        disputa = self._abrir_disputa(db, escenario, "a")
        assert self._resolver(cliente, disputa, escenario["arbitro"]).status_code == 200

    def test_el_administrador_de_ese_torneo_tambien_puede(self, cliente, escenario, db):
        disputa = self._abrir_disputa(db, escenario, "a")
        assert self._resolver(cliente, disputa, escenario["admin"]).status_code == 200

    def test_el_organizador_global_sigue_pudiendo(self, cliente, escenario, db):
        disputa = self._abrir_disputa(db, escenario, "a")
        assert self._resolver(cliente, disputa, escenario["organizador"]).status_code == 200

    def test_el_staff_de_otro_torneo_no_puede(self, cliente, escenario, db):
        """El alcance no se desborda: staff de la Copa A no toca una
        disputa de la Copa B."""
        disputa = self._abrir_disputa(db, escenario, "b")
        assert self._resolver(cliente, disputa, escenario["arbitro"]).status_code == 403

    def test_un_ajeno_no_puede(self, cliente, escenario, db):
        disputa = self._abrir_disputa(db, escenario, "a")
        assert self._resolver(cliente, disputa, escenario["ajeno"]).status_code == 403

    def test_una_disputa_inexistente_no_filtra_si_existe(self, cliente, escenario):
        """Sin ser staff de ningún torneo, la respuesta es la misma
        (403) exista o no la disputa — no hay forma de usar esta ruta
        para confirmar IDs ajenos."""
        r = cliente.post(
            "/api/disputas/999999/resolver",
            json={"resolucion": "x", "accion": "reprogramar"},
            headers=auth(escenario["ajeno"]),
        )
        assert r.status_code == 403
