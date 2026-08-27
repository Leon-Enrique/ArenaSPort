"""Roster permanente, identidad de juego y salida voluntaria.

La regla que ordena todo el archivo, y que es el rediseño entero en una
línea:

    **Entrar no requiere aceptar; salir no requiere permiso.**

El capitán suma directo porque armar el equipo no puede depender de que
cinco personas contesten. Lo que hace legítimo eso es lo otro: al sumado le
llega aviso y se va solo, sin convencer a nadie. Los dos lados de esa
asimetría se prueban acá.

Y una tercera cosa que es la que hace posible el alta directa: **la
identidad de juego vive en la cuenta, no en el equipo**. El capitán nunca
escribe el ID de nadie.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.enums import ModeloCompetencia
from app.main import app
from app.models import (
    Equipo,
    IdentidadDeJuego,
    InvitacionAEquipo,
    Juego,
    MiembroEquipo,
    Notificacion,
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

    capitan = Usuario(discord_id="cap-1", discord_username="Capitan")
    jugador = Usuario(discord_id="jug-1", discord_username="Jugador")
    otro = Usuario(discord_id="jug-2", discord_username="Otro")
    ajeno = Usuario(discord_id="aje-1", discord_username="Ajeno")
    db.add_all([capitan, jugador, otro, ajeno])
    db.flush()

    equipo = Equipo(nombre="Dragons", propietario_usuario_id=capitan.id)
    db.add(equipo)
    db.commit()

    return {
        "juego": juego,
        "equipo": equipo,
        "capitan": capitan,
        "jugador": jugador,
        "otro": otro,
        "ajeno": ajeno,
    }


def auth(u: Usuario) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {crear_access_token(u.id, u.discord_id, u.es_organizador)}"
    }


def ident(nick="Lyon", id_juego="123456789"):
    return {"nick": nick, "id_juego": id_juego, "server": "2251"}


def cargar_identidad(cliente, quien, identidad=None):
    return cliente.put(
        "/api/usuarios/me/identidades",
        json={"identidad": identidad or ident()},
        headers=auth(quien),
    )


def agregar(cliente, escenario, a_quien, por=None):
    return cliente.post(
        f"/api/equipos/{escenario['equipo'].id}/miembros",
        json={"usuario_id": a_quien.id},
        headers=auth(por or escenario["capitan"]),
    )


def ver_roster(cliente, escenario, quien=None):
    return cliente.get(
        f"/api/equipos/{escenario['equipo'].id}/miembros",
        headers=auth(quien or escenario["capitan"]),
    )


class TestLaIdentidadEsDeLaCuenta:
    def test_cada_uno_carga_la_suya(self, cliente, escenario):
        r = cargar_identidad(cliente, escenario["jugador"])
        assert r.status_code == 200
        assert r.json()["identidad"]["id_juego"] == "123456789"

    def test_se_puede_corregir_y_no_duplica(self, cliente, escenario, db):
        cargar_identidad(cliente, escenario["jugador"])
        r = cargar_identidad(cliente, escenario["jugador"], ident(nick="NickNuevo"))
        assert r.status_code == 200
        assert db.query(IdentidadDeJuego).count() == 1
        assert db.query(IdentidadDeJuego).one().identidad["nick"] == "NickNuevo"

    def test_faltando_un_campo_obligatorio_no_se_guarda(self, cliente, escenario):
        r = cliente.put(
            "/api/usuarios/me/identidades",
            json={"identidad": {"nick": "SinId"}},
            headers=auth(escenario["jugador"]),
        )
        assert r.status_code == 422
        assert "id_juego" in r.json()["detail"]

    def test_dos_cuentas_no_pueden_declarar_el_mismo_id_de_juego(
        self, cliente, escenario
    ):
        """El hueco que antes era invisible: con la identidad viviendo
        dentro de cada inscripción, estas dos filas nunca se cruzaban."""
        cargar_identidad(cliente, escenario["jugador"])
        r = cargar_identidad(cliente, escenario["otro"])
        assert r.status_code == 409

    def test_corregirla_se_propaga_a_los_equipos(self, cliente, escenario):
        """El roster guarda el vínculo, no una copia del ID."""
        cargar_identidad(cliente, escenario["jugador"])
        agregar(cliente, escenario, escenario["jugador"])
        cargar_identidad(cliente, escenario["jugador"], ident(nick="Corregido"))

        roster = ver_roster(cliente, escenario).json()
        assert roster[0]["identidad"]["nick"] == "Corregido"


class TestEntrarNoRequiereAceptar:
    def test_el_capitan_suma_directo(self, cliente, escenario, db):
        r = agregar(cliente, escenario, escenario["jugador"])
        assert r.status_code == 201
        assert db.query(MiembroEquipo).one().usuario_id == escenario["jugador"].id

    def test_el_capitan_no_escribe_el_id_de_nadie(self, cliente, escenario):
        """Lo toma de la cuenta: es lo que permite sumar sin fricción."""
        cargar_identidad(cliente, escenario["jugador"], ident(nick="SuyoPropio"))
        r = agregar(cliente, escenario, escenario["jugador"])
        assert r.json()["identidad"]["nick"] == "SuyoPropio"

    def test_al_sumado_le_llega_una_notificacion_con_quien_lo_agrego(
        self, cliente, escenario, db
    ):
        """Es lo que hace legítima el alta sin permiso: nadie queda en un
        equipo sin enterarse."""
        agregar(cliente, escenario, escenario["jugador"])

        aviso = db.query(Notificacion).one()
        assert aviso.usuario_id == escenario["jugador"].id
        assert aviso.tipo == "agregado_a_equipo"
        assert "Capitan" in aviso.cuerpo
        assert "Dragons" in aviso.titulo

    def test_sin_identidad_cargada_entra_igual(self, cliente, escenario):
        """Bloquear el alta haría que armar el equipo dependa de la
        velocidad de los demás, que es lo que se quiere evitar."""
        r = agregar(cliente, escenario, escenario["jugador"])
        assert r.status_code == 201
        assert r.json()["identidad"] is None

    def test_un_ajeno_no_puede_sumar_gente(self, cliente, escenario):
        r = agregar(cliente, escenario, escenario["jugador"], por=escenario["ajeno"])
        assert r.status_code == 403

    def test_no_se_puede_sumar_a_alguien_que_ya_esta(self, cliente, escenario):
        agregar(cliente, escenario, escenario["jugador"])
        assert agregar(cliente, escenario, escenario["jugador"]).status_code == 409

    def test_un_usuario_inexistente_da_404(self, cliente, escenario):
        r = cliente.post(
            f"/api/equipos/{escenario['equipo'].id}/miembros",
            json={"usuario_id": 999999},
            headers=auth(escenario["capitan"]),
        )
        assert r.status_code == 404


class TestSalirNoRequierePermiso:
    def _miembro_id(self, cliente, escenario, quien):
        return agregar(cliente, escenario, quien).json()["id"]

    def test_el_jugador_se_va_solo(self, cliente, escenario, db):
        """El problema que este rediseño vino a resolver: antes había que
        convencer al capitán."""
        mid = self._miembro_id(cliente, escenario, escenario["jugador"])
        r = cliente.delete(
            f"/api/equipos/{escenario['equipo'].id}/miembros/{mid}",
            headers=auth(escenario["jugador"]),
        )
        assert r.status_code == 200
        assert db.query(MiembroEquipo).one().esta_activo is False

    def test_irse_solo_no_genera_aviso(self, cliente, escenario, db):
        """Ya sabe que se fue."""
        mid = self._miembro_id(cliente, escenario, escenario["jugador"])
        db.query(Notificacion).delete()
        db.commit()

        cliente.delete(
            f"/api/equipos/{escenario['equipo'].id}/miembros/{mid}",
            headers=auth(escenario["jugador"]),
        )
        assert db.query(Notificacion).count() == 0

    def test_el_capitan_puede_sacar_a_otro_y_le_avisa(self, cliente, escenario, db):
        mid = self._miembro_id(cliente, escenario, escenario["jugador"])
        db.query(Notificacion).delete()
        db.commit()

        r = cliente.delete(
            f"/api/equipos/{escenario['equipo'].id}/miembros/{mid}",
            headers=auth(escenario["capitan"]),
        )
        assert r.status_code == 200
        aviso = db.query(Notificacion).one()
        assert aviso.usuario_id == escenario["jugador"].id
        assert aviso.tipo == "sacado_de_equipo"

    def test_un_tercero_no_puede_sacar_a_nadie(self, cliente, escenario):
        mid = self._miembro_id(cliente, escenario, escenario["jugador"])
        r = cliente.delete(
            f"/api/equipos/{escenario['equipo'].id}/miembros/{mid}",
            headers=auth(escenario["ajeno"]),
        )
        assert r.status_code == 403

    def test_salir_dos_veces_no_se_puede(self, cliente, escenario):
        mid = self._miembro_id(cliente, escenario, escenario["jugador"])
        url = f"/api/equipos/{escenario['equipo'].id}/miembros/{mid}"
        assert cliente.delete(url, headers=auth(escenario["jugador"])).status_code == 200
        assert cliente.delete(url, headers=auth(escenario["jugador"])).status_code == 409

    def test_el_que_se_fue_no_aparece_en_el_roster(self, cliente, escenario):
        mid = self._miembro_id(cliente, escenario, escenario["jugador"])
        cliente.delete(
            f"/api/equipos/{escenario['equipo'].id}/miembros/{mid}",
            headers=auth(escenario["jugador"]),
        )
        assert ver_roster(cliente, escenario).json() == []

    def test_volver_reusa_la_fila_en_vez_de_duplicarla(self, cliente, escenario, db):
        mid = self._miembro_id(cliente, escenario, escenario["jugador"])
        cliente.delete(
            f"/api/equipos/{escenario['equipo'].id}/miembros/{mid}",
            headers=auth(escenario["jugador"]),
        )
        assert agregar(cliente, escenario, escenario["jugador"]).status_code == 201
        assert db.query(MiembroEquipo).count() == 1


class TestElRosterEsPrivado:
    def test_un_ajeno_no_lo_ve(self, cliente, escenario):
        """Acá van los datos de juego de cada persona; el perfil público
        del equipo es otra ruta."""
        assert ver_roster(cliente, escenario, escenario["ajeno"]).status_code == 403


class TestInvitacionPorLink:
    """No es el camino normal —al que ya tiene cuenta se lo agrega directo—
    sino el que cubre a quien todavía no se registró."""

    def _invitar(self, cliente, escenario, destino=None):
        cuerpo = {}
        if destino is not None:
            cuerpo["usuario_destino_id"] = destino.id
        return cliente.post(
            f"/api/equipos/{escenario['equipo'].id}/invitaciones",
            json=cuerpo,
            headers=auth(escenario["capitan"]),
        )

    def _aceptar(self, cliente, token, quien):
        return cliente.post(
            f"/api/invitaciones/{token}/aceptar", headers=auth(quien)
        )

    def test_entrar_por_link_no_pide_la_identidad(self, cliente, escenario):
        """Mismo criterio que el alta directa: la pertenencia no espera al
        dato."""
        token = self._invitar(cliente, escenario).json()["token"]
        r = self._aceptar(cliente, token, escenario["jugador"])
        assert r.status_code == 201
        assert r.json()["identidad"] is None

    def test_deja_el_mismo_estado_que_el_alta_directa(self, cliente, escenario, db):
        token = self._invitar(cliente, escenario).json()["token"]
        self._aceptar(cliente, token, escenario["jugador"])

        miembro = db.query(MiembroEquipo).one()
        assert miembro.esta_activo is True
        assert miembro.agregado_por_usuario_id == escenario["capitan"].id
        assert db.query(Notificacion).count() == 1

    def test_se_usa_una_sola_vez(self, cliente, escenario):
        token = self._invitar(cliente, escenario).json()["token"]
        assert self._aceptar(cliente, token, escenario["jugador"]).status_code == 201
        assert self._aceptar(cliente, token, escenario["otro"]).status_code == 404

    def test_la_dirigida_solo_la_usa_su_destinatario(self, cliente, escenario):
        token = self._invitar(cliente, escenario, escenario["jugador"]).json()["token"]
        assert self._aceptar(cliente, token, escenario["jugador"]).status_code == 201

    def test_una_dirigida_a_otro_responde_404(self, cliente, escenario):
        """404 y no 403: decir 'existe pero no es tuya' convertiría la ruta
        en un oráculo para adivinar tokens."""
        token = self._invitar(cliente, escenario, escenario["jugador"]).json()["token"]
        assert self._aceptar(cliente, token, escenario["otro"]).status_code == 404

    def test_un_token_inventado_responde_igual(self, cliente, escenario):
        assert self._aceptar(cliente, "no-existe", escenario["jugador"]).status_code == 404

    def test_una_vencida_responde_igual(self, cliente, escenario, db):
        token = self._invitar(cliente, escenario).json()["token"]
        db.query(InvitacionAEquipo).one().expira_at = (
            datetime.now().astimezone() - timedelta(days=1)
        )
        db.commit()
        assert self._aceptar(cliente, token, escenario["jugador"]).status_code == 404

    def test_una_revocada_responde_igual(self, cliente, escenario):
        creada = self._invitar(cliente, escenario).json()
        r = cliente.delete(
            f"/api/equipos/{escenario['equipo'].id}/invitaciones/{creada['id']}",
            headers=auth(escenario["capitan"]),
        )
        assert r.status_code == 200
        assert self._aceptar(cliente, creada["token"], escenario["jugador"]).status_code == 404

    def test_el_token_no_vuelve_a_aparecer_en_los_listados(self, cliente, escenario):
        self._invitar(cliente, escenario)
        r = cliente.get(
            f"/api/equipos/{escenario['equipo'].id}/invitaciones",
            headers=auth(escenario["capitan"]),
        )
        assert r.json()
        assert all("token" not in inv for inv in r.json())

    def test_el_preview_avisa_si_falta_cargar_el_id(self, cliente, escenario):
        token = self._invitar(cliente, escenario).json()["token"]
        r = cliente.get(
            f"/api/invitaciones/{token}", headers=auth(escenario["jugador"])
        )
        assert r.status_code == 200
        assert r.json()["ya_cargaste_tu_identidad"] is False
        assert "id_juego" in r.json()["campos_requeridos"]
