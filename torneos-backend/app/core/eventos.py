"""Bus de eventos en memoria para los streams SSE.

Quién publica y quién escucha
-----------------------------
Publican las rutas normales (`app/api/routes/partidas.py`) cuando algo
cambia: se abre un check-in, se reporta un resultado, alguien escribe en el
chat. Escuchan los streams de `app/api/routes/stream.py`, uno por cliente
conectado.

El detalle que hace falta cuidar
--------------------------------
Los handlers de este proyecto son `def`, no `async def`, así que FastAPI los
corre en un hilo del threadpool — fuera del loop de asyncio. Meter algo en
un `asyncio.Queue` desde otro hilo no es seguro: hay que pedirle al loop que
lo haga él, con `call_soon_threadsafe`. Sin eso el evento se pierde o rompe
de forma intermitente y solo bajo carga, que es la peor manera de
enterarse. Por eso el hub guarda una referencia al loop al arrancar la app.

Límite conocido: esto vive en la memoria del proceso
-----------------------------------------------------
Con más de un worker de uvicorn, un evento publicado en el worker A no llega
a un cliente conectado al worker B, y el usuario ve datos viejos sin ningún
error. Hoy el proyecto corre en un solo proceso, así que alcanza — pero es
un techo real, no un detalle. `PUBLICADOR` está aislado justamente para que
cambiarlo por Postgres LISTEN/NOTIFY (ya hay Postgres, no haría falta Redis)
sea reemplazar esta clase y nada más.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger("torneos.eventos")

# Cuántos eventos puede acumular un cliente lento antes de que se le empiecen
# a descartar los más viejos. Un cliente sano vacía su cola al instante; esto
# existe para que una pestaña congelada no haga crecer la memoria del proceso
# sin techo.
MAX_EVENTOS_EN_COLA = 100

# Cada cuánto mandar un comentario de keepalive si no pasó nada. Sin esto,
# proxies y balanceadores cortan una conexión SSE ociosa y el cliente
# reconecta en loop.
SEGUNDOS_ENTRE_LATIDOS = 25


@dataclass
class Evento:
    tipo: str
    datos: dict[str, Any]
    creado_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def como_sse(self) -> str:
        """Formato del protocolo SSE: una línea `event:` y una `data:`,
        separadas del próximo evento por una línea en blanco."""
        cuerpo = json.dumps(self.datos, default=str, ensure_ascii=False)
        return f"event: {self.tipo}\ndata: {cuerpo}\n\n"


class HubDeEventos:
    """Pub/sub por tópico, seguro para publicar desde otros hilos."""

    def __init__(self) -> None:
        self._suscriptores: dict[str, set[asyncio.Queue[Evento]]] = defaultdict(set)
        self._candado = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def vincular_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Lo llama el lifespan de la app. Sin esto, publicar desde un
        handler síncrono no tiene a qué loop pedirle el trabajo."""
        self._loop = loop

    def cantidad_de_suscriptores(self, topico: str) -> int:
        with self._candado:
            return len(self._suscriptores.get(topico, ()))

    def publicar(self, topico: str, tipo: str, datos: dict[str, Any]) -> None:
        """Manda un evento a todos los suscriptores del tópico.

        Nunca levanta excepción: publicar es un efecto secundario de una
        operación que ya se completó (el resultado ya se guardó en la base),
        así que un problema en el stream no puede tumbar el request.
        """
        try:
            evento = Evento(tipo=tipo, datos=datos)
            with self._candado:
                colas = list(self._suscriptores.get(topico, ()))
            if not colas:
                return

            for cola in colas:
                self._encolar(cola, evento)
        except Exception:  # noqa: BLE001
            log.exception("No se pudo publicar el evento %s en %s", tipo, topico)

    def _encolar(self, cola: asyncio.Queue[Evento], evento: Evento) -> None:
        """Elige cómo poner el evento en la cola según desde dónde se publica.

        Dos caminos:
          - Hay un loop corriendo en ESTE hilo (handler async, o un test):
            encolar directo es seguro y es lo más rápido.
          - No lo hay (handler `def` en el threadpool): hay que pedirle al
            loop de la app que lo haga él, porque `asyncio.Queue` no es
            seguro entre hilos.

        El chequeo de `is_closed()` no es defensivo por las dudas: la
        referencia al loop se guarda una vez al arrancar, y si ese loop se
        cerró (apagado en curso, o un test que ya terminó) `call_soon_threadsafe`
        levanta y el evento se pierde sin que nadie se entere. Ante un loop
        muerto es mejor encolar directo: los que estuvieran esperando en ese
        loop ya no existen, así que no hay nada que despertar.
        """
        try:
            hay_loop_local = asyncio.get_running_loop() is not None
        except RuntimeError:
            hay_loop_local = False

        loop = self._loop
        if hay_loop_local or loop is None or loop.is_closed():
            _poner_descartando_viejos(cola, evento)
        else:
            loop.call_soon_threadsafe(_poner_descartando_viejos, cola, evento)

    def registrar(self, topico: str) -> asyncio.Queue[Evento]:
        """Da de alta un suscriptor y devuelve su cola. SÍNCRONO a propósito.

        La ruta SSE llama a esto ANTES de devolver la respuesta, no dentro del
        generador que la produce. La diferencia importa: el cuerpo de un
        generador async no corre hasta que alguien lo consume, así que
        registrarse ahí adentro deja una ventana entre "el cliente ya está
        conectado" y "el hub sabe que existe" — y todo lo que se publique en
        ese intervalo se pierde sin dejar rastro. Con la partida en vivo y
        alguien reportando un resultado justo en ese momento, es un evento
        perdido que nadie puede explicar después.
        """
        cola: asyncio.Queue[Evento] = asyncio.Queue(maxsize=MAX_EVENTOS_EN_COLA)
        with self._candado:
            self._suscriptores[topico].add(cola)
        return cola

    def desregistrar(self, topico: str, cola: asyncio.Queue[Evento]) -> None:
        """Impide que el hub se llene de colas muertas de clientes que ya
        cerraron la pestaña."""
        with self._candado:
            self._suscriptores[topico].discard(cola)
            if topico in self._suscriptores and not self._suscriptores[topico]:
                del self._suscriptores[topico]

    async def suscribir(self, topico: str) -> AsyncIterator[Evento]:
        """Azúcar sobre registrar/desregistrar para quien solo quiere iterar.

        La ruta SSE NO usa esto (necesita registrarse antes de que empiece la
        respuesta, ver `registrar`); queda para los tests y para cualquier
        consumidor interno.
        """
        cola = self.registrar(topico)
        try:
            while True:
                yield await cola.get()
        finally:
            self.desregistrar(topico, cola)


def _poner_descartando_viejos(cola: asyncio.Queue[Evento], evento: Evento) -> None:
    """Encola sin bloquear. Si el cliente viene tan atrasado que llenó su
    cola, se tira el evento más viejo: para un bracket en vivo el estado más
    nuevo es el que importa, y quedarse esperando bloquearía a los demás.
    """
    try:
        cola.put_nowait(evento)
    except asyncio.QueueFull:
        try:
            cola.get_nowait()
        except asyncio.QueueEmpty:
            pass
        try:
            cola.put_nowait(evento)
        except asyncio.QueueFull:
            pass


PUBLICADOR = HubDeEventos()


# --- Nombres de tópico -------------------------------------------------
# Centralizados para que publicador y suscriptor no puedan escribir el
# mismo nombre de dos formas distintas (un typo acá no da error: solo hace
# que el evento no le llegue a nadie, que es imposible de depurar).

def topico_edicion(edicion_id: int) -> str:
    """Cambios de partidas de una edición. Público: la página del torneo lo
    es, no hay nada acá que no se vea en el bracket."""
    return f"edicion:{edicion_id}"


def topico_chat(partida_id: int) -> str:
    """Chat de una partida. Privado: solo los equipos que juegan y el
    organizador."""
    return f"chat:{partida_id}"
