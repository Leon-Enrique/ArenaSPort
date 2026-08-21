"""Streams SSE: bracket en vivo y chat en vivo.

Dos endpoints con reglas de acceso distintas a propósito:

  - `/stream/ediciones/{id}` es PÚBLICO. Manda cambios de estado de partidas
    —lo mismo que ya muestra la página del torneo, que cualquiera puede
    abrir sin loguearse—. Pedir autenticación acá no protegería nada y
    dejaría el bracket en vivo solo para usuarios registrados.

  - `/stream/partidas/{id}/chat` es PRIVADO: solo los jugadores de los dos
    equipos y el organizador. Como el navegador no puede mandar headers en
    un EventSource, se entra con un ticket de un solo uso
    (ver app/core/tickets.py).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import CurrentUser, DbSession
from app.core.eventos import (
    PUBLICADOR,
    SEGUNDOS_ENTRE_LATIDOS,
    topico_chat,
    topico_edicion,
)
from app.core.tickets import TICKETS, ErrorTicket
from app.models import Edicion, Inscripcion, Jugador, Partida, Usuario

router = APIRouter(prefix="/stream", tags=["stream"])

# Cabeceras que necesita un SSE para funcionar detrás de un proxy.
# `X-Accel-Buffering: no` es específicamente para nginx: sin eso, nginx
# acumula la respuesta en un buffer y el "tiempo real" llega en tandas.
CABECERAS_SSE = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class TicketOut(BaseModel):
    ticket: str
    vence_en_segundos: int


@router.post("/ticket", response_model=TicketOut)
def emitir_ticket(usuario: CurrentUser) -> TicketOut:
    """Canjea la sesión normal (header Authorization) por un ticket corto
    para abrir un stream privado."""
    from app.core.tickets import SEGUNDOS_DE_VIDA

    return TicketOut(
        ticket=TICKETS.emitir(usuario.id),
        vence_en_segundos=SEGUNDOS_DE_VIDA,
    )


async def _emitir(topico: str, cola, request: Request) -> AsyncIterator[str]:
    """Convierte los eventos del hub en el formato de texto de SSE.

    Recibe la cola YA registrada (ver `HubDeEventos.registrar`): registrarse
    acá adentro llegaría tarde, porque el cuerpo de un generador async no
    corre hasta que alguien lo consume.

    Manda un latido cada tanto si no pasa nada: una conexión SSE ociosa la
    cortan los intermediarios, y el cliente entra en un ciclo de reconexión
    que parece un problema del servidor.
    """
    try:
        # `retry` le dice al navegador cuánto esperar antes de reconectar solo.
        yield "retry: 3000\n\n"
        while True:
            if await request.is_disconnected():
                break
            try:
                evento = await asyncio.wait_for(
                    cola.get(), timeout=SEGUNDOS_ENTRE_LATIDOS
                )
            except asyncio.TimeoutError:
                yield ": latido\n\n"
                continue
            yield evento.como_sse()
    finally:
        PUBLICADOR.desregistrar(topico, cola)


@router.get("/ediciones/{edicion_id}")
async def stream_de_edicion(edicion_id: int, request: Request, db: DbSession):
    """Bracket en vivo: cambios de estado de las partidas de esta edición.

    El evento trae el identificador de lo que cambió, no la partida entera —
    el cliente vuelve a pedir los datos que ya sabe pedir. Así el stream no
    tiene que replicar la forma de cada respuesta ni preocuparse por quién
    puede ver qué campo.
    """
    if not db.get(Edicion, edicion_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La edición no existe.")

    # Registrar ANTES de devolver la respuesta cierra la ventana en la que
    # el cliente ya está conectado pero el hub todavía no lo conoce.
    topico = topico_edicion(edicion_id)
    cola = PUBLICADOR.registrar(topico)
    return StreamingResponse(
        _emitir(topico, cola, request),
        media_type="text/event-stream",
        headers=CABECERAS_SSE,
    )


def _usuario_del_ticket(db: DbSession, ticket: str | None) -> Usuario:
    if not ticket:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Este stream necesita un ticket. Pedilo en POST /stream/ticket.",
        )
    try:
        usuario_id = TICKETS.canjear(ticket)
    except ErrorTicket as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e

    usuario = db.get(Usuario, usuario_id)
    if not usuario or not usuario.esta_activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado o inactivo.")
    return usuario


def _verificar_acceso_al_chat(db: DbSession, usuario: Usuario, partida: Partida) -> None:
    """Mismo criterio que el endpoint de mensajes en partidas.py: cualquier
    jugador de cualquiera de los dos equipos, o el organizador."""
    if usuario.es_organizador:
        return

    equipos_partida = [p.equipo_id for p in partida.participaciones]
    pertenece = (
        db.query(Jugador)
        .join(Jugador.inscripcion)
        .filter(
            Jugador.discord_id == usuario.discord_id,
            Jugador.inscripcion.has(Inscripcion.equipo_id.in_(equipos_partida)),
        )
        .first()
    )
    if not pertenece:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Esta partida no es tuya — no podés escuchar este chat.",
        )


@router.get("/partidas/{partida_id}/chat")
async def stream_de_chat(
    partida_id: int, request: Request, db: DbSession, ticket: str | None = None
):
    """Chat de partida en vivo. Reemplaza el polling cada 4 segundos.

    El ticket se canjea acá y se quema: si alguien lo levanta después de un
    log, ya no sirve.
    """
    partida = db.get(Partida, partida_id)
    if not partida:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La partida no existe.")

    usuario = _usuario_del_ticket(db, ticket)
    _verificar_acceso_al_chat(db, usuario, partida)

    topico = topico_chat(partida_id)
    cola = PUBLICADOR.registrar(topico)
    return StreamingResponse(
        _emitir(topico, cola, request),
        media_type="text/event-stream",
        headers=CABECERAS_SSE,
    )
