"""Endpoints SSE de punta a punta: quién puede escuchar qué.

Lo que más importa acá es la autorización. El stream de edición es público a
propósito (el bracket ya lo es), pero el de chat NO: si se pudiera abrir sin
credenciales, cualquiera leería la coordinación privada de dos equipos —
y peor, en tiempo real y sin dejar rastro en ningún endpoint auditado.
"""

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from app.api.routes.stream import _emitir
from app.core.eventos import PUBLICADOR, topico_chat, topico_edicion
from app.core.security import crear_access_token
from app.domain.enums import FormatoFase, ModeloCompetencia
from app.main import app
from app.models import (
    Edicion,
    Equipo,
    Fase,
    Inscripcion,
    Jugador,
    Juego,
    Partida,
    ParticipacionEnPartida,
    Torneo,
    Usuario,
)


@pytest.fixture
def cliente(db):
    """TestClient con la sesión de base del test inyectada en la app."""
    from app.db.database import get_db

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def escenario(db):
    """Una partida entre dos equipos, con el capitán de cada uno vinculado a
    una cuenta, más un organizador y un usuario ajeno."""
    juego = Juego(
        codigo="mlbb-stream",
        nombre="MLBB",
        modelo_competencia_default=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        titulares_requeridos=1,
        suplentes_maximos=0,
        campos_identidad={"campos": [{"nombre": "nick", "etiqueta": "Nick", "requerido": True}],
                          "clave_unica": ["nick"]},
    )
    db.add(juego)
    db.flush()

    torneo = Torneo(nombre="Copa Stream", slug="copa-stream")
    db.add(torneo)
    db.flush()
    edicion = Edicion(torneo_id=torneo.id, juego_id=juego.id, numero=1,
                      nombre="T1", slug="copa-stream-t1")
    db.add(edicion)
    db.flush()
    fase = Fase(edicion_id=edicion.id, orden=1, nombre="F1",
                modelo_competencia=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
                formato=FormatoFase.ELIMINACION_SIMPLE, config={"bo": 3})
    db.add(fase)
    db.flush()

    dragons, wolves = Equipo(nombre="Dragons"), Equipo(nombre="Wolves")
    db.add_all([dragons, wolves])
    db.flush()

    partida = Partida(fase_id=fase.id)
    db.add(partida)
    db.flush()
    db.add_all([
        ParticipacionEnPartida(partida_id=partida.id, equipo_id=dragons.id, slot=0),
        ParticipacionEnPartida(partida_id=partida.id, equipo_id=wolves.id, slot=1),
    ])

    capitan = Usuario(discord_id="cap-dragons", discord_username="CapDragons")
    ajeno = Usuario(discord_id="ajeno", discord_username="Curioso")
    organizador = Usuario(discord_id="org", discord_username="Org", es_organizador=True)
    db.add_all([capitan, ajeno, organizador])
    db.flush()

    for equipo, discord in ((dragons, "cap-dragons"), (wolves, None)):
        inscripcion = Inscripcion(edicion_id=edicion.id, equipo_id=equipo.id)
        db.add(inscripcion)
        db.flush()
        db.add(Jugador(
            inscripcion_id=inscripcion.id, edicion_id=edicion.id,
            identidad={"nick": equipo.nombre}, clave_identidad=equipo.nombre.lower(),
            es_capitan=True, discord_id=discord,
        ))
    db.commit()

    return {
        "edicion_id": edicion.id,
        "fase_id": fase.id,
        "partida_id": partida.id,
        "capitan": capitan,
        "ajeno": ajeno,
        "organizador": organizador,
    }


def auth(usuario: Usuario) -> dict[str, str]:
    token = crear_access_token(usuario.id, usuario.discord_id, usuario.es_organizador)
    return {"Authorization": f"Bearer {token}"}


def esperar_evento(cola, timeout: float = 2.0):
    """Espera un evento en una cola registrada directo en el hub.

    Por qué no se lee del stream HTTP: ni el TestClient de Starlette ni el
    ASGITransport de httpx saben manejar una respuesta que no termina — los
    dos esperan a tener el cuerpo completo, así que abrir un SSE infinito
    contra ellos cuelga el test (comprobado con una app mínima de cinco
    líneas, no es algo de este proyecto).

    Registrar la cola a mano prueba exactamente lo mismo que importa acá: que
    la acción HTTP publique el evento correcto en el tópico correcto. El
    formateo a texto SSE y el latido se prueban aparte, sobre `_emitir`.

    El sondeo corto existe porque publicar desde un handler `def` pasa por
    `call_soon_threadsafe`: el evento se encola en el loop de la app, no en
    el hilo del test, y puede tardar un instante en aparecer.
    """
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        try:
            return cola.get_nowait()
        except asyncio.QueueEmpty:
            time.sleep(0.01)
    raise AssertionError("no llegó ningún evento al tópico")


class TestTicket:
    def test_sin_sesion_no_da_ticket(self, cliente):
        assert cliente.post("/api/stream/ticket").status_code == 401

    def test_con_sesion_da_un_ticket(self, cliente, escenario):
        r = cliente.post("/api/stream/ticket", headers=auth(escenario["capitan"]))
        assert r.status_code == 200
        assert len(r.json()["ticket"]) >= 32
        assert r.json()["vence_en_segundos"] > 0




class TestStreamDeEdicion:
    def test_una_edicion_inexistente_da_404(self, cliente):
        assert cliente.get("/api/stream/ediciones/9999").status_code == 404

    def test_avisa_cuando_cambia_una_partida(self, cliente, escenario, db):
        """El camino completo: un capitán reporta por HTTP y el evento sale
        publicado al tópico de la edición sin que nadie vuelva a preguntar."""
        partida = db.get(Partida, escenario["partida_id"])
        partida.estado = "en_curso"
        db.commit()
        equipo_id = partida.participaciones[0].equipo_id

        topico = topico_edicion(escenario["edicion_id"])
        cola = PUBLICADOR.registrar(topico)
        try:
            r = cliente.post(
                f"/api/fases/{escenario['fase_id']}/partidas/{escenario['partida_id']}/reportar",
                json={"equipo_id": equipo_id, "marcador_propio": 2, "marcador_rival": 0},
                headers=auth(escenario["capitan"]),
            )
            assert r.status_code == 200, r.text

            evento = esperar_evento(cola)
            assert evento.tipo == "resultado_reportado"
            assert evento.datos["partida_id"] == escenario["partida_id"]
            assert evento.datos["estado"] == "reportada"
        finally:
            PUBLICADOR.desregistrar(topico, cola)

    def test_el_evento_no_incluye_la_partida_entera(self, cliente, escenario, db):
        """A propósito: el stream manda identificadores y el cliente vuelve a
        pedir con su propio permiso. Si mandara el objeto completo, el stream
        tendría que repetir las reglas de redacción de cada endpoint — y ahí
        es donde se escapa un campo que no debía salir."""
        partida = db.get(Partida, escenario["partida_id"])
        partida.estado = "en_curso"
        db.commit()

        topico = topico_edicion(escenario["edicion_id"])
        cola = PUBLICADOR.registrar(topico)
        try:
            cliente.post(
                f"/api/fases/{escenario['fase_id']}/partidas/{escenario['partida_id']}/reportar",
                json={
                    "equipo_id": partida.participaciones[0].equipo_id,
                    "marcador_propio": 2,
                    "marcador_rival": 0,
                },
                headers=auth(escenario["capitan"]),
            )
            evento = esperar_evento(cola)
            assert set(evento.datos) == {"partida_id", "fase_id", "estado"}
        finally:
            PUBLICADOR.desregistrar(topico, cola)

    def test_el_check_in_tambien_avisa(self, cliente, escenario):
        topico = topico_edicion(escenario["edicion_id"])
        cola = PUBLICADOR.registrar(topico)
        try:
            r = cliente.post(
                f"/api/fases/{escenario['fase_id']}/partidas/{escenario['partida_id']}/abrir-checkin",
                json={"minutos": 15},
                headers=auth(escenario["organizador"]),
            )
            assert r.status_code == 200, r.text
            assert esperar_evento(cola).tipo == "checkin_abierto"
        finally:
            PUBLICADOR.desregistrar(topico, cola)

    def test_una_edicion_no_recibe_los_eventos_de_otra(self, cliente, escenario, db):
        """Dos torneos en curso al mismo tiempo no pueden mezclarse."""
        partida = db.get(Partida, escenario["partida_id"])
        partida.estado = "en_curso"
        db.commit()

        otro_topico = topico_edicion(escenario["edicion_id"] + 999)
        cola_ajena = PUBLICADOR.registrar(otro_topico)
        try:
            cliente.post(
                f"/api/fases/{escenario['fase_id']}/partidas/{escenario['partida_id']}/reportar",
                json={
                    "equipo_id": partida.participaciones[0].equipo_id,
                    "marcador_propio": 2,
                    "marcador_rival": 0,
                },
                headers=auth(escenario["capitan"]),
            )
            time.sleep(0.1)
            assert cola_ajena.qsize() == 0
        finally:
            PUBLICADOR.desregistrar(otro_topico, cola_ajena)


class TestStreamDeChat:
    def test_sin_ticket_no_entra(self, cliente, escenario):
        r = cliente.get(f"/api/stream/partidas/{escenario['partida_id']}/chat")
        assert r.status_code == 401

    def test_con_un_ticket_inventado_no_entra(self, cliente, escenario):
        r = cliente.get(
            f"/api/stream/partidas/{escenario['partida_id']}/chat",
            params={"ticket": "cualquiera"},
        )
        assert r.status_code == 401

    def test_un_ajeno_no_puede_escuchar(self, cliente, escenario):
        """El test que más importa del archivo: alguien logueado pero que no
        juega esta partida no puede leer la coordinación de otros — y por un
        stream, además, que no deja rastro en ningún endpoint auditado."""
        ticket = cliente.post(
            "/api/stream/ticket", headers=auth(escenario["ajeno"])
        ).json()["ticket"]
        r = cliente.get(
            f"/api/stream/partidas/{escenario['partida_id']}/chat",
            params={"ticket": ticket},
        )
        assert r.status_code == 403

    def test_una_partida_inexistente_da_404(self, cliente, escenario):
        ticket = cliente.post(
            "/api/stream/ticket", headers=auth(escenario["capitan"])
        ).json()["ticket"]
        r = cliente.get("/api/stream/partidas/9999/chat", params={"ticket": ticket})
        assert r.status_code == 404

    def test_un_mensaje_nuevo_se_publica(self, cliente, escenario, db):
        """Lo que reemplaza al polling cada 4 segundos."""
        partida = db.get(Partida, escenario["partida_id"])
        equipo_id = partida.participaciones[0].equipo_id

        topico = topico_chat(escenario["partida_id"])
        cola = PUBLICADOR.registrar(topico)
        try:
            r = cliente.post(
                f"/api/fases/{escenario['fase_id']}/partidas/{escenario['partida_id']}/mensajes",
                json={"equipo_id": equipo_id, "texto": "jugamos 20:00?"},
                headers=auth(escenario["capitan"]),
            )
            assert r.status_code == 201, r.text

            evento = esperar_evento(cola)
            assert evento.tipo == "mensaje_nuevo"
            assert evento.datos["texto"] == "jugamos 20:00?"
            assert evento.datos["equipo_id"] == equipo_id
        finally:
            PUBLICADOR.desregistrar(topico, cola)

    def test_el_chat_de_otra_partida_no_se_filtra(self, cliente, escenario, db):
        """Aislamiento por tópico sobre los endpoints reales: un mensaje de la
        partida A no puede aparecer en el stream de la B."""
        otra = Partida(fase_id=escenario["fase_id"])
        db.add(otra)
        db.commit()

        partida = db.get(Partida, escenario["partida_id"])
        topico_otra = topico_chat(otra.id)
        cola_otra = PUBLICADOR.registrar(topico_otra)
        try:
            cliente.post(
                f"/api/fases/{escenario['fase_id']}/partidas/{escenario['partida_id']}/mensajes",
                json={
                    "equipo_id": partida.participaciones[0].equipo_id,
                    "texto": "privado",
                },
                headers=auth(escenario["capitan"]),
            )
            time.sleep(0.1)
            assert cola_otra.qsize() == 0, "un mensaje de otra partida se filtró"
        finally:
            PUBLICADOR.desregistrar(topico_otra, cola_otra)

    def test_el_chat_no_va_al_stream_publico_de_la_edicion(self, cliente, escenario, db):
        """La separación que evita el peor error posible acá: que la
        coordinación privada de dos capitanes salga por el stream que
        cualquiera puede abrir sin loguearse."""
        partida = db.get(Partida, escenario["partida_id"])
        topico_publico = topico_edicion(escenario["edicion_id"])
        cola_publica = PUBLICADOR.registrar(topico_publico)
        try:
            cliente.post(
                f"/api/fases/{escenario['fase_id']}/partidas/{escenario['partida_id']}/mensajes",
                json={
                    "equipo_id": partida.participaciones[0].equipo_id,
                    "texto": "secreto",
                },
                headers=auth(escenario["capitan"]),
            )
            time.sleep(0.1)
            assert cola_publica.qsize() == 0, "el chat privado se filtró al stream público"
        finally:
            PUBLICADOR.desregistrar(topico_publico, cola_publica)


class RequestFalso:
    """Lo mínimo que `_emitir` le pide a un Request."""

    async def is_disconnected(self) -> bool:
        return False


class TestEmision:
    """`_emitir` probado directo, sin HTTP.

    Es la pieza que traduce eventos del hub al texto del protocolo SSE, y la
    única que no se puede ejercitar por HTTP en los tests: una respuesta que
    nunca termina cuelga tanto al TestClient de Starlette como al
    ASGITransport de httpx, porque los dos esperan el cuerpo completo.
    """

    def test_arranca_diciendole_al_navegador_cuando_reconectar(self):
        async def caso():
            topico = "t-preambulo"
            cola = PUBLICADOR.registrar(topico)
            gen = _emitir(topico, cola, RequestFalso())
            try:
                assert await anext(gen) == "retry: 3000\n\n"
            finally:
                await gen.aclose()

        asyncio.run(caso())

    def test_un_evento_publicado_sale_como_sse(self):
        async def caso():
            topico = "t-emision"
            cola = PUBLICADOR.registrar(topico)
            gen = _emitir(topico, cola, RequestFalso())
            try:
                await anext(gen)  # preámbulo
                PUBLICADOR.publicar(topico, "mensaje_nuevo", {"texto": "hola"})
                salida = await asyncio.wait_for(anext(gen), timeout=2)
                assert salida.startswith("event: mensaje_nuevo\n")
                assert "hola" in salida
                assert salida.endswith("\n\n")
            finally:
                await gen.aclose()

        asyncio.run(caso())

    def test_manda_un_latido_si_no_pasa_nada(self, monkeypatch):
        """Sin latidos, un proxy corta la conexión ociosa y el cliente entra
        en un ciclo de reconexión que parece un problema del servidor."""
        monkeypatch.setattr("app.api.routes.stream.SEGUNDOS_ENTRE_LATIDOS", 0.05)

        async def caso():
            topico = "t-latido"
            cola = PUBLICADOR.registrar(topico)
            gen = _emitir(topico, cola, RequestFalso())
            try:
                await anext(gen)
                assert await asyncio.wait_for(anext(gen), timeout=2) == ": latido\n\n"
            finally:
                await gen.aclose()

        asyncio.run(caso())

    def test_al_cerrarse_libera_la_suscripcion(self):
        """Si no se liberara, cada pestaña cerrada dejaría una cola muerta
        acumulándose en la memoria del proceso."""

        async def caso():
            topico = "t-limpieza"
            cola = PUBLICADOR.registrar(topico)
            assert PUBLICADOR.cantidad_de_suscriptores(topico) == 1

            gen = _emitir(topico, cola, RequestFalso())
            await anext(gen)
            await gen.aclose()
            assert PUBLICADOR.cantidad_de_suscriptores(topico) == 0

        asyncio.run(caso())
