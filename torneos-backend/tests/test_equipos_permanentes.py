"""Equipos permanentes: la identidad que hace posible el historial.

Antes, cada inscripción creaba un `Equipo` nuevo, así que un equipo que jugó
cinco torneos eran cinco filas sin relación y su perfil no podía mostrar
nada. Acá se prueba que ahora pueda ser el mismo, y —más importante— que eso
no rompa la inscripción anónima, que es la que usa el 97% de la gente y que
se mantiene a propósito.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.security import crear_access_token
from app.domain.enums import EstadoEdicion, EstadoInscripcion, ModeloCompetencia
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
        codigo="mlbb",
        nombre="Mobile Legends",
        modelo_competencia_default=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        titulares_requeridos=1,
        suplentes_maximos=0,
        campos_identidad={
            "campos": [{"nombre": "nick", "etiqueta": "Nick", "requerido": True}],
            "clave_unica": ["nick"],
        },
    )
    db.add(juego)
    db.flush()

    torneo = Torneo(nombre="Copa Anual", slug="copa-anual")
    db.add(torneo)
    db.flush()

    ediciones = []
    for numero in (1, 2):
        e = Edicion(
            torneo_id=torneo.id, juego_id=juego.id, numero=numero,
            nombre=f"Temporada {numero}", slug=f"copa-anual-t{numero}",
            estado=EstadoEdicion.INSCRIPCIONES_ABIERTAS,
            # Casi todo este archivo prueba la MECÁNICA del equipo
            # permanente (reuso, dueño, historial), no la regla de si el
            # torneo exige cuenta. Esa tiene su propia clase más abajo, y
            # desde que el default se dio vuelta hay que apagarla acá para
            # poder seguir inscribiendo rosters sueltos.
            requiere_equipo_permanente=False,
        )
        db.add(e)
        ediciones.append(e)
    db.flush()

    capitan = Usuario(discord_id="cap-1", discord_username="Capitan")
    otro = Usuario(discord_id="cap-2", discord_username="Otro")
    organizador = Usuario(discord_id="org", discord_username="Org", es_organizador=True)
    db.add_all([capitan, otro, organizador])
    db.commit()

    return {
        "edicion_1": ediciones[0], "edicion_2": ediciones[1],
        "capitan": capitan, "otro": otro, "organizador": organizador,
    }


def auth(u: Usuario) -> dict[str, str]:
    return {"Authorization": f"Bearer {crear_access_token(u.id, u.discord_id, u.es_organizador)}"}


def roster(nick: str = "jugador1") -> list[dict]:
    return [{"identidad": {"nick": nick}, "es_capitan": True}]


def inscribir(cliente, edicion_id, nombre="Dragons", headers=None, equipo_id=None, nick="jugador1"):
    cuerpo = {"nombre_equipo": nombre, "jugadores": roster(nick)}
    if equipo_id is not None:
        cuerpo["equipo_id"] = equipo_id
    return cliente.post(
        f"/api/ediciones/{edicion_id}/inscripciones", json=cuerpo, headers=headers or {}
    )


class TestInscripcionSueltaCuandoElTorneoLaPermite:
    """Anotarse sin cuenta dejó de ser el default, pero NO se borró.

    Era una ventaja deliberada para torneos de base, y sigue estando: el
    organizador la habilita apagando `requiere_equipo_permanente` en su
    edición, igual que el "Permanent teams only" de Toornament. Lo que
    cambió es de qué lado arranca el interruptor, no que exista.

    Estos tests corren con el flag apagado (ver la fixture) y vigilan que
    ese camino siga entero.
    """

    def test_sin_sesion_se_puede_inscribir(self, cliente, escenario):
        r = inscribir(cliente, escenario["edicion_1"].id)
        assert r.status_code == 201, r.text

    def test_el_equipo_creado_asi_no_tiene_dueno(self, cliente, escenario, db):
        r = inscribir(cliente, escenario["edicion_1"].id)
        equipo_id = r.json()["inscripcion"]["equipo"]["id"]
        assert db.get(Equipo, equipo_id).propietario_usuario_id is None

    def test_avisa_que_no_va_a_acumular_historial(self, cliente, escenario):
        """El equipo tiene que enterarse de lo que pierde, no descubrirlo el
        año que viene."""
        r = inscribir(cliente, escenario["edicion_1"].id)
        avisos = " ".join(r.json()["avisos"])
        assert "sin iniciar sesión" in avisos
        assert "reutilizarlo" in avisos


class TestInscripcionConSesion:
    def test_el_equipo_queda_a_nombre_de_quien_inscribe(self, cliente, escenario, db):
        r = inscribir(cliente, escenario["edicion_1"].id, headers=auth(escenario["capitan"]))
        assert r.status_code == 201, r.text
        equipo_id = r.json()["inscripcion"]["equipo"]["id"]
        assert db.get(Equipo, equipo_id).propietario_usuario_id == escenario["capitan"].id

    def test_no_avisa_nada_sobre_historial(self, cliente, escenario):
        r = inscribir(cliente, escenario["edicion_1"].id, headers=auth(escenario["capitan"]))
        assert not any("sin iniciar sesión" in a for a in r.json()["avisos"])


class TestReutilizarElMismoEquipo:
    def test_el_mismo_equipo_juega_dos_torneos(self, cliente, escenario, db):
        """El objetivo de toda la funcionalidad: una sola fila de equipo con
        dos inscripciones, en vez de dos equipos sin relación."""
        headers = auth(escenario["capitan"])
        primera = inscribir(cliente, escenario["edicion_1"].id, headers=headers)
        equipo_id = primera.json()["inscripcion"]["equipo"]["id"]

        segunda = inscribir(
            cliente, escenario["edicion_2"].id, headers=headers,
            equipo_id=equipo_id, nick="jugador2",
        )
        assert segunda.status_code == 201, segunda.text
        assert segunda.json()["inscripcion"]["equipo"]["id"] == equipo_id

        inscripciones = db.query(Inscripcion).filter(Inscripcion.equipo_id == equipo_id).count()
        assert inscripciones == 2

    def test_el_perfil_refleja_los_dos_torneos(self, cliente, escenario, db):
        headers = auth(escenario["capitan"])
        equipo_id = inscribir(
            cliente, escenario["edicion_1"].id, headers=headers
        ).json()["inscripcion"]["equipo"]["id"]
        inscribir(
            cliente, escenario["edicion_2"].id, headers=headers,
            equipo_id=equipo_id, nick="jugador2",
        )
        for i in db.query(Inscripcion).filter(Inscripcion.equipo_id == equipo_id):
            i.estado = EstadoInscripcion.APROBADA
        db.commit()

        perfil = cliente.get(f"/api/equipos/{equipo_id}").json()
        assert perfil["torneos_jugados"] == 2

    def test_no_se_puede_inscribir_un_equipo_ajeno(self, cliente, escenario):
        """Heredar el historial y los títulos de otro sería suplantarlo."""
        equipo_id = inscribir(
            cliente, escenario["edicion_1"].id, headers=auth(escenario["capitan"])
        ).json()["inscripcion"]["equipo"]["id"]

        r = inscribir(
            cliente, escenario["edicion_2"].id, headers=auth(escenario["otro"]),
            equipo_id=equipo_id, nick="jugador2",
        )
        assert r.status_code == 403

    def test_sin_sesion_no_se_puede_reutilizar(self, cliente, escenario):
        equipo_id = inscribir(
            cliente, escenario["edicion_1"].id, headers=auth(escenario["capitan"])
        ).json()["inscripcion"]["equipo"]["id"]

        r = inscribir(cliente, escenario["edicion_2"].id, equipo_id=equipo_id, nick="jugador2")
        assert r.status_code == 401

    def test_el_organizador_si_puede_inscribir_cualquiera(self, cliente, escenario):
        equipo_id = inscribir(
            cliente, escenario["edicion_1"].id, headers=auth(escenario["capitan"])
        ).json()["inscripcion"]["equipo"]["id"]

        r = inscribir(
            cliente, escenario["edicion_2"].id, headers=auth(escenario["organizador"]),
            equipo_id=equipo_id, nick="jugador2",
        )
        assert r.status_code == 201, r.text

    def test_un_equipo_inexistente_da_404(self, cliente, escenario):
        r = inscribir(
            cliente, escenario["edicion_1"].id, headers=auth(escenario["capitan"]),
            equipo_id=99999,
        )
        assert r.status_code == 404

    def test_no_se_puede_inscribir_dos_veces_en_la_misma_edicion(self, cliente, escenario):
        headers = auth(escenario["capitan"])
        equipo_id = inscribir(
            cliente, escenario["edicion_1"].id, headers=headers
        ).json()["inscripcion"]["equipo"]["id"]

        r = inscribir(
            cliente, escenario["edicion_1"].id, nombre="Dragons Reloaded",
            headers=headers, equipo_id=equipo_id, nick="jugador2",
        )
        assert r.status_code == 409

    def test_renombrar_al_reinscribirse_conserva_el_historial(self, cliente, escenario, db):
        """El historial va con el equipo, no con el texto del nombre."""
        headers = auth(escenario["capitan"])
        equipo_id = inscribir(
            cliente, escenario["edicion_1"].id, nombre="Dragons", headers=headers
        ).json()["inscripcion"]["equipo"]["id"]

        r = inscribir(
            cliente, escenario["edicion_2"].id, nombre="Dragons Esports",
            headers=headers, equipo_id=equipo_id, nick="jugador2",
        )
        assert r.status_code == 201, r.text
        assert db.get(Equipo, equipo_id).nombre == "Dragons Esports"
        assert any("pasó a llamarse" in a for a in r.json()["avisos"])


class TestTorneoQueExigeEquipoPermanente:
    """El flag por edición, copiado de Toornament: el organizador decide si
    su torneo pide cuenta o no, en vez de imponerlo la plataforma."""

    def test_por_defecto_viene_prendido(self, db, escenario):
        """Se dio vuelta cuando la identidad de juego pasó a vivir en la
        cuenta: sin cuenta no hay dónde guardar el ID, a quién avisarle que
        lo sumaron, ni cómo dejar que se vaya solo del equipo.

        Se construye una edición nueva a mano porque la fixture de este
        archivo lo apaga a propósito.
        """
        nueva = Edicion(
            torneo_id=escenario["edicion_1"].torneo_id,
            juego_id=escenario["edicion_1"].juego_id,
            numero=9,
            nombre="Recién creada",
            slug="copa-anual-t9",
            estado=EstadoEdicion.INSCRIPCIONES_ABIERTAS,
        )
        db.add(nueva)
        db.commit()
        assert nueva.requiere_equipo_permanente is True

    def test_un_torneo_nuevo_rechaza_al_que_no_tiene_equipo(self, cliente, db, escenario):
        """La consecuencia de lo anterior, vista desde afuera."""
        nueva = Edicion(
            torneo_id=escenario["edicion_1"].torneo_id,
            juego_id=escenario["edicion_1"].juego_id,
            numero=10,
            nombre="Recién creada 2",
            slug="copa-anual-t10",
            estado=EstadoEdicion.INSCRIPCIONES_ABIERTAS,
        )
        db.add(nueva)
        db.commit()

        r = inscribir(cliente, nueva.id, headers=auth(escenario["capitan"]))
        assert r.status_code == 409
        assert "equipo permanente" in r.json()["detail"]

    def test_prendido_rechaza_la_inscripcion_suelta(self, cliente, escenario, db):
        escenario["edicion_1"].requiere_equipo_permanente = True
        db.commit()

        r = inscribir(cliente, escenario["edicion_1"].id, headers=auth(escenario["capitan"]))
        assert r.status_code == 409
        assert "equipo permanente" in r.json()["detail"]

    def test_prendido_acepta_un_equipo_existente(self, cliente, escenario, db):
        creado = cliente.post(
            "/api/equipos", json={"nombre": "Dragons"}, headers=auth(escenario["capitan"])
        ).json()
        escenario["edicion_1"].requiere_equipo_permanente = True
        db.commit()

        r = inscribir(
            cliente, escenario["edicion_1"].id, headers=auth(escenario["capitan"]),
            equipo_id=creado["id"],
        )
        assert r.status_code == 201, r.text

    def test_apagado_no_cambia_nada(self, cliente, escenario):
        assert inscribir(cliente, escenario["edicion_1"].id).status_code == 201


class TestAdministrarMisEquipos:
    def test_sin_sesion_no_se_listan(self, cliente):
        assert cliente.get("/api/equipos/mios").status_code == 401

    def test_arranca_vacio(self, cliente, escenario):
        r = cliente.get("/api/equipos/mios", headers=auth(escenario["capitan"]))
        assert r.status_code == 200 and r.json() == []

    def test_crear_y_listar(self, cliente, escenario):
        headers = auth(escenario["capitan"])
        creado = cliente.post("/api/equipos", json={"nombre": "Dragons", "tag": "DRG"}, headers=headers)
        assert creado.status_code == 201, creado.text

        mios = cliente.get("/api/equipos/mios", headers=headers).json()
        assert [e["nombre"] for e in mios] == ["Dragons"]
        assert mios[0]["torneos_jugados"] == 0

    def test_no_se_ven_los_equipos_de_otro(self, cliente, escenario):
        cliente.post("/api/equipos", json={"nombre": "Dragons"}, headers=auth(escenario["capitan"]))
        assert cliente.get("/api/equipos/mios", headers=auth(escenario["otro"])).json() == []

    def test_no_se_repite_el_nombre_dentro_de_la_misma_cuenta(self, cliente, escenario):
        headers = auth(escenario["capitan"])
        cliente.post("/api/equipos", json={"nombre": "Dragons"}, headers=headers)
        r = cliente.post("/api/equipos", json={"nombre": "dragons"}, headers=headers)
        assert r.status_code == 409

    def test_dos_personas_distintas_si_pueden_usar_el_mismo_nombre(self, cliente, escenario):
        """El nombre no es identificador global: dos equipos reales pueden
        llamarse igual y no son el mismo."""
        cliente.post("/api/equipos", json={"nombre": "Dragons"}, headers=auth(escenario["capitan"]))
        r = cliente.post("/api/equipos", json={"nombre": "Dragons"}, headers=auth(escenario["otro"]))
        assert r.status_code == 201

    def test_editar_el_propio(self, cliente, escenario):
        headers = auth(escenario["capitan"])
        creado = cliente.post("/api/equipos", json={"nombre": "Dragons"}, headers=headers).json()
        r = cliente.patch(f"/api/equipos/{creado['id']}", json={"tag": "DRG"}, headers=headers)
        assert r.status_code == 200 and r.json()["tag"] == "DRG"

    def test_un_patch_parcial_no_pisa_lo_demas(self, cliente, escenario):
        headers = auth(escenario["capitan"])
        creado = cliente.post(
            "/api/equipos", json={"nombre": "Dragons", "tag": "DRG"}, headers=headers
        ).json()
        r = cliente.patch(f"/api/equipos/{creado['id']}", json={"nombre": "Dragons X"}, headers=headers)
        assert r.json()["nombre"] == "Dragons X"
        assert r.json()["tag"] == "DRG"

    def test_no_se_edita_el_de_otro(self, cliente, escenario):
        creado = cliente.post(
            "/api/equipos", json={"nombre": "Dragons"}, headers=auth(escenario["capitan"])
        ).json()
        r = cliente.patch(
            f"/api/equipos/{creado['id']}", json={"tag": "HACK"}, headers=auth(escenario["otro"])
        )
        assert r.status_code == 403

    def test_editar_uno_inexistente_da_404(self, cliente, escenario):
        r = cliente.patch("/api/equipos/99999", json={"tag": "X"}, headers=auth(escenario["capitan"]))
        assert r.status_code == 404
