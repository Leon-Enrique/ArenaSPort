"""Tickets de un solo uso para autenticar streams SSE.

Por qué existe esto
-------------------
El navegador no deja poner headers en un `EventSource` (ni en un WebSocket),
así que el token de sesión no puede viajar como `Authorization`. La salida
fácil sería mandarlo como `?token=<JWT>`, y es justo lo que no hay que
hacer: la query string queda escrita en los logs de acceso del servidor, en
los del proxy y en el Referer, y ese JWT vive una semana.

Un ticket resuelve eso: se pide con el token real por header, sirve una sola
vez, vale un minuto y no autoriza nada más que abrir un stream. Si se filtra
en un log, ya está vencido y usado.

Vive en memoria, igual que el hub de eventos (`app/core/eventos.py`) — con
varios workers un ticket emitido por uno no lo puede canjear otro. Es la
misma limitación y se levanta junto con aquella.
"""

from __future__ import annotations

import secrets
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

SEGUNDOS_DE_VIDA = 60


@dataclass(frozen=True)
class _Ticket:
    usuario_id: int
    vence_at: datetime


class ErrorTicket(Exception):
    """El ticket no existe, ya se usó o venció."""


class RegistroDeTickets:
    def __init__(self, segundos_de_vida: int = SEGUNDOS_DE_VIDA) -> None:
        self._tickets: dict[str, _Ticket] = {}
        self._candado = threading.Lock()
        self._segundos_de_vida = segundos_de_vida

    def emitir(self, usuario_id: int, ahora: datetime | None = None) -> str:
        ahora = ahora or datetime.now(UTC)
        codigo = secrets.token_urlsafe(32)
        with self._candado:
            self._purgar_vencidos(ahora)
            self._tickets[codigo] = _Ticket(
                usuario_id=usuario_id,
                vence_at=ahora + timedelta(seconds=self._segundos_de_vida),
            )
        return codigo

    def canjear(self, codigo: str, ahora: datetime | None = None) -> int:
        """Devuelve el usuario_id y quema el ticket. Un segundo intento con
        el mismo código falla — si alguien lo copió de un log, ya no sirve.
        """
        ahora = ahora or datetime.now(UTC)
        with self._candado:
            ticket = self._tickets.pop(codigo, None)
        if ticket is None:
            raise ErrorTicket("El ticket no existe o ya fue usado.")
        if ahora > ticket.vence_at:
            raise ErrorTicket("El ticket venció. Pedí uno nuevo.")
        return ticket.usuario_id

    def _purgar_vencidos(self, ahora: datetime) -> None:
        """Se llama al emitir, que es la única operación que hace crecer el
        registro — no hace falta una tarea de limpieza aparte."""
        vencidos = [c for c, t in self._tickets.items() if ahora > t.vence_at]
        for c in vencidos:
            del self._tickets[c]

    def cantidad_pendientes(self) -> int:
        with self._candado:
            return len(self._tickets)


TICKETS = RegistroDeTickets()
