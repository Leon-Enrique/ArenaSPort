"""Bus de eventos y tickets de stream.

El hub tiene una trampa que estos tests vigilan: los handlers de FastAPI son
`def`, así que publican desde un hilo del threadpool, fuera del loop de
asyncio. Meter algo en un `asyncio.Queue` desde otro hilo no es seguro y
falla de forma intermitente y solo bajo carga — la peor manera de enterarse.
Por eso hay un test que publica explícitamente desde otro hilo.
"""

import asyncio
import threading
from datetime import UTC, datetime, timedelta

import pytest

from app.core.eventos import (
    MAX_EVENTOS_EN_COLA,
    Evento,
    HubDeEventos,
    _poner_descartando_viejos,
    topico_chat,
    topico_edicion,
)
from app.core.tickets import ErrorTicket, RegistroDeTickets


class TestFormatoSSE:
    def test_arma_las_lineas_del_protocolo(self):
        sse = Evento(tipo="mensaje_nuevo", datos={"id": 7}).como_sse()
        assert sse == 'event: mensaje_nuevo\ndata: {"id": 7}\n\n'

    def test_termina_en_linea_en_blanco(self):
        """Sin la línea en blanco el navegador no considera cerrado el
        evento y no dispara el handler."""
        assert Evento(tipo="x", datos={}).como_sse().endswith("\n\n")

    def test_no_escapa_los_acentos(self):
        sse = Evento(tipo="x", datos={"texto": "jugamos mañana"}).como_sse()
        assert "mañana" in sse

    def test_serializa_fechas(self):
        sse = Evento(tipo="x", datos={"cuando": datetime(2026, 8, 21, tzinfo=UTC)}).como_sse()
        assert "2026-08-21" in sse

    def test_un_salto_de_linea_en_el_texto_no_rompe_el_evento(self):
        """Un mensaje de chat con Enter adentro no puede partir el evento en
        dos: JSON escapa el salto, así que el `data:` sigue siendo una línea."""
        sse = Evento(tipo="x", datos={"texto": "hola\nchau"}).como_sse()
        cuerpo = sse.split("data: ")[1]
        assert cuerpo.count("\n") == 2  # solo el par final que cierra el evento


class TestNombresDeTopico:
    def test_son_distintos_por_entidad(self):
        assert topico_edicion(1) != topico_edicion(2)
        assert topico_chat(1) != topico_chat(2)

    def test_edicion_y_chat_no_se_pisan(self):
        """Si un chat de partida 1 y una edición 1 compartieran tópico, los
        mensajes privados irían al stream público."""
        assert topico_edicion(1) != topico_chat(1)


def correr(corutina):
    """Los casos async se corren a mano: el proyecto no usa pytest-asyncio y
    no vale la pena sumar la dependencia solo para estos tests."""
    return asyncio.run(corutina)


async def abrir_consumidor(hub: HubDeEventos, topico: str) -> tuple[asyncio.Task, list]:
    """Suscribe un cliente que consume de verdad, como hace el endpoint SSE.

    Devuelve (tarea, recibidos). Cancelar la tarea cierra el generador por el
    camino normal (GeneratorExit -> el `finally` que libera la suscripción),
    que es lo que pasa cuando un navegador corta la conexión.
    """
    recibidos: list = []
    registrado = asyncio.Event()

    async def consumir():
        suscripcion = hub.suscribir(topico)
        # Arrancar el generador es lo que registra la cola en el hub; recién
        # después tiene sentido publicar.
        tarea_primera = asyncio.ensure_future(suscripcion.__anext__())
        await asyncio.sleep(0)
        registrado.set()
        try:
            recibidos.append(await tarea_primera)
            async for evento in suscripcion:
                recibidos.append(evento)
        finally:
            await suscripcion.aclose()

    tarea = asyncio.ensure_future(consumir())
    await registrado.wait()
    return tarea, recibidos


async def cerrar(tarea: asyncio.Task) -> None:
    tarea.cancel()
    try:
        await tarea
    except asyncio.CancelledError:
        pass


def test_un_suscriptor_recibe_lo_que_se_publica():
    async def caso():
        hub = HubDeEventos()
        hub.vincular_loop(asyncio.get_running_loop())
        suscripcion = hub.suscribir("t")
        tarea = asyncio.ensure_future(suscripcion.__anext__())
        await asyncio.sleep(0)  # deja que la suscripción se registre

        hub.publicar("t", "saludo", {"n": 1})
        evento = await asyncio.wait_for(tarea, timeout=1)
        assert evento.tipo == "saludo"
        assert evento.datos == {"n": 1}
        await suscripcion.aclose()

    correr(caso())


def test_todos_los_suscriptores_del_topico_reciben():
    async def caso():
        hub = HubDeEventos()
        hub.vincular_loop(asyncio.get_running_loop())
        a, b = hub.suscribir("t"), hub.suscribir("t")
        ta, tb = asyncio.ensure_future(a.__anext__()), asyncio.ensure_future(b.__anext__())
        await asyncio.sleep(0)

        hub.publicar("t", "x", {"v": 9})
        ea, eb = await asyncio.wait_for(asyncio.gather(ta, tb), timeout=1)
        assert ea.datos == eb.datos == {"v": 9}
        await a.aclose()
        await b.aclose()

    correr(caso())


def test_no_llega_nada_de_otro_topico():
    """El aislamiento entre tópicos es lo que separa el chat privado de una
    partida del de otra."""
    async def caso():
        hub = HubDeEventos()
        hub.vincular_loop(asyncio.get_running_loop())
        tarea, recibidos = await abrir_consumidor(hub, "mio")

        hub.publicar("ajeno", "x", {})
        await asyncio.sleep(0.05)

        assert recibidos == []
        await cerrar(tarea)

    correr(caso())


def test_publicar_desde_otro_hilo_llega_igual():
    """El caso real: un handler `def` de FastAPI corre en el threadpool y
    publica desde ahí. Si el hub no delegara al loop, esto fallaría de forma
    intermitente."""
    async def caso():
        hub = HubDeEventos()
        hub.vincular_loop(asyncio.get_running_loop())
        suscripcion = hub.suscribir("t")
        tarea = asyncio.ensure_future(suscripcion.__anext__())
        await asyncio.sleep(0)

        hilo = threading.Thread(target=hub.publicar, args=("t", "desde_hilo", {"ok": True}))
        hilo.start()
        evento = await asyncio.wait_for(tarea, timeout=2)
        hilo.join()

        assert evento.tipo == "desde_hilo"
        await suscripcion.aclose()

    correr(caso())


def test_publicar_sin_suscriptores_no_rompe():
    hub = HubDeEventos()
    hub.publicar("nadie_escucha", "x", {})  # no debe levantar


def test_publicar_nunca_propaga_una_excepcion():
    """Publicar es un efecto secundario de una operación ya confirmada en la
    base: si el stream falla, el request tiene que responder igual."""
    hub = HubDeEventos()  # sin loop vinculado: encola directo

    class ColaRota:
        def put_nowait(self, _):
            raise RuntimeError("cola rota")

    hub._suscriptores["t"].add(ColaRota())  # type: ignore[arg-type]
    hub.publicar("t", "x", {})  # no debe levantar


def test_al_desconectarse_se_libera_la_suscripcion():
    """Sin esto el hub acumula colas muertas de cada pestaña que se cerró."""
    async def caso():
        hub = HubDeEventos()
        hub.vincular_loop(asyncio.get_running_loop())
        tarea, _ = await abrir_consumidor(hub, "t")
        assert hub.cantidad_de_suscriptores("t") == 1

        await cerrar(tarea)
        assert hub.cantidad_de_suscriptores("t") == 0

    correr(caso())


def test_un_cliente_lento_no_hace_crecer_la_memoria_sin_techo():
    """Una pestaña congelada no puede acumular eventos para siempre: al
    llenarse la cola se descartan los más viejos y se conservan los últimos,
    que para un bracket en vivo son los que importan.

    Va directo contra la cola en vez de contra el generador: lo que se está
    probando es la política de descarte, no el ciclo de suscripción.
    """
    cola: asyncio.Queue = asyncio.Queue(maxsize=MAX_EVENTOS_EN_COLA)
    for i in range(MAX_EVENTOS_EN_COLA * 3):
        _poner_descartando_viejos(cola, Evento(tipo="x", datos={"i": i}))

    assert cola.qsize() == MAX_EVENTOS_EN_COLA
    primero = cola.get_nowait()
    assert primero.datos["i"] == MAX_EVENTOS_EN_COLA * 2, "debería haber quedado la cola de eventos más nuevos"


class TestTickets:
    def test_un_ticket_sirve_una_sola_vez(self):
        """Si alguien lo levanta de un log de acceso, ya no vale."""
        registro = RegistroDeTickets()
        codigo = registro.emitir(usuario_id=7)
        assert registro.canjear(codigo) == 7
        with pytest.raises(ErrorTicket, match="ya fue usado"):
            registro.canjear(codigo)

    def test_un_ticket_vencido_no_sirve(self):
        registro = RegistroDeTickets(segundos_de_vida=30)
        emitido_en = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
        codigo = registro.emitir(usuario_id=7, ahora=emitido_en)
        with pytest.raises(ErrorTicket, match="venció"):
            registro.canjear(codigo, ahora=emitido_en + timedelta(seconds=31))

    def test_dentro_de_la_ventana_sirve(self):
        registro = RegistroDeTickets(segundos_de_vida=30)
        emitido_en = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
        codigo = registro.emitir(usuario_id=7, ahora=emitido_en)
        assert registro.canjear(codigo, ahora=emitido_en + timedelta(seconds=29)) == 7

    def test_un_codigo_inventado_no_sirve(self):
        registro = RegistroDeTickets()
        with pytest.raises(ErrorTicket):
            registro.canjear("no-existe")

    def test_cada_ticket_es_distinto(self):
        registro = RegistroDeTickets()
        codigos = {registro.emitir(usuario_id=1) for _ in range(50)}
        assert len(codigos) == 50

    def test_los_codigos_son_largos(self):
        """Cortos serían adivinables por fuerza bruta dentro de su minuto de
        vida."""
        assert len(RegistroDeTickets().emitir(usuario_id=1)) >= 32

    def test_los_vencidos_se_limpian_solos(self):
        registro = RegistroDeTickets(segundos_de_vida=10)
        base = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)
        for _ in range(5):
            registro.emitir(usuario_id=1, ahora=base)
        assert registro.cantidad_pendientes() == 5

        registro.emitir(usuario_id=1, ahora=base + timedelta(seconds=60))
        assert registro.cantidad_pendientes() == 1
