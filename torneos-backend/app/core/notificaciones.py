"""Entrega de notificaciones: fila en la base + aviso al canal de Discord.

Misma idea que app/core/almacenamiento.py — una costura en `core` para que
las rutas nunca sepan cómo se entrega nada, solo que algo pasó y a quién le
importa.

Dos caminos independientes a propósito:

- **In-app**: filas `Notificacion`, se escriben en la misma transacción que
  el cambio que las produjo. Es el registro durable.
- **Discord**: POST al webhook de la edición, encolado como tarea de fondo.
  Puede fallar (Discord caído, webhook borrado) sin que eso rompa la
  aprobación de una inscripción o la apertura de un check-in.
"""

import logging

import httpx
from sqlalchemy.orm import Session

from app.models import Edicion, Inscripcion, Jugador, Notificacion, Usuario

log = logging.getLogger("torneos.notificaciones")

# El organizador escribe esta URL a mano y el servidor le hace POST. Sin
# restringir el destino, un organizador podría apuntarla a un servicio de la
# red interna y usar el backend como proxy para alcanzarlo (SSRF). Solo se
# aceptan webhooks de Discord, y se comprueba tanto al guardar como antes de
# cada envío — guardar y enviar son momentos distintos y el valor pudo haber
# entrado por otro camino.
PREFIJOS_WEBHOOK_VALIDOS = (
    "https://discord.com/api/webhooks/",
    "https://discordapp.com/api/webhooks/",
)

TIMEOUT_DISCORD = httpx.Timeout(5.0)


class ErrorWebhook(Exception):
    """La URL de webhook no sirve. Error de negocio, se traduce a 422."""


def validar_url_webhook(url: str) -> str:
    limpia = url.strip()
    if not limpia.startswith(PREFIJOS_WEBHOOK_VALIDOS):
        raise ErrorWebhook(
            "Tiene que ser una URL de webhook de Discord "
            "(https://discord.com/api/webhooks/...). En Discord: "
            "Configuración del canal > Integraciones > Webhooks > Copiar URL."
        )
    return limpia


def _armar_payload(titulo: str, cuerpo: str, discord_ids: list[str]) -> dict:
    menciones = " ".join(f"<@{d}>" for d in discord_ids)
    contenido = f"**{titulo}**\n{cuerpo}"
    if menciones:
        contenido = f"{contenido}\n{menciones}"

    return {
        "content": contenido[:1900],  # Discord corta en 2000; dejamos aire
        # Sin esto, un nombre de equipo con "@everyone" adentro haría que el
        # webhook pinguee al servidor entero. La lista blanca explícita
        # limita los pings exactamente a los destinatarios previstos.
        "allowed_mentions": {"parse": [], "users": discord_ids[:100]},
    }


def enviar_a_discord(webhook_url: str, titulo: str, cuerpo: str, discord_ids: list[str]) -> None:
    """Publica en el canal. Nunca propaga: esto corre como tarea de fondo y
    un fallo acá no puede tumbar la operación que lo disparó."""
    try:
        url = validar_url_webhook(webhook_url)
        respuesta = httpx.post(url, json=_armar_payload(titulo, cuerpo, discord_ids), timeout=TIMEOUT_DISCORD)
        respuesta.raise_for_status()
    except Exception as e:
        log.warning("No se pudo publicar en Discord (%s): %s", titulo, e)


def enviar_a_discord_estricto(webhook_url: str, titulo: str, cuerpo: str) -> None:
    """Como `enviar_a_discord` pero SÍ propaga el error — es la versión para
    el botón "probar webhook", donde el organizador está esperando saber si
    funcionó y tragarse el error sería exactamente lo contrario de lo útil."""
    url = validar_url_webhook(webhook_url)
    try:
        respuesta = httpx.post(url, json=_armar_payload(titulo, cuerpo, []), timeout=TIMEOUT_DISCORD)
        respuesta.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ErrorWebhook(
            f"Discord rechazó el mensaje (HTTP {e.response.status_code}). "
            "Revisá que el webhook siga existiendo en el canal."
        ) from e
    except httpx.HTTPError as e:
        raise ErrorWebhook(f"No se pudo contactar a Discord: {e}") from e


def usuarios_de_equipos(db: Session, equipo_ids: list[int], edicion_id: int) -> list[Usuario]:
    """Las cuentas reales detrás de los jugadores de esos equipos.

    El vínculo es `Jugador.discord_id` -> `Usuario.discord_id` (ver el
    comentario en app/models/participantes.py). Un jugador sin vincular
    simplemente no aparece: no hay a quién notificar todavía. Las cuentas
    locales tienen un discord_id sintético ("local:<email>") que nunca va a
    matchear un jugador, y eso es correcto.
    """
    if not equipo_ids:
        return []

    return (
        db.query(Usuario)
        .join(Jugador, Jugador.discord_id == Usuario.discord_id)
        .join(Inscripcion, Inscripcion.id == Jugador.inscripcion_id)
        .filter(
            Jugador.edicion_id == edicion_id,
            Inscripcion.equipo_id.in_(equipo_ids),
            Usuario.esta_activo.is_(True),
        )
        .distinct()
        .all()
    )


def notificar(
    db: Session,
    background_tasks,
    *,
    tipo: str,
    usuarios: list[Usuario],
    titulo: str,
    cuerpo: str,
    url: str | None = None,
    edicion: Edicion | None = None,
) -> None:
    """Registra la notificación para cada destinatario y encola el aviso a
    Discord. NO hace commit — se hace junto al cambio que la disparó, para
    que no exista una notificación de algo que terminó no pasando.
    """
    for usuario in usuarios:
        db.add(
            Notificacion(
                usuario_id=usuario.id,
                tipo=tipo,
                titulo=titulo,
                cuerpo=cuerpo,
                url=url,
                edicion_id=edicion.id if edicion else None,
            )
        )

    if edicion and edicion.discord_webhook_url:
        discord_ids = [u.discord_id for u in usuarios if not u.discord_id.startswith("local:")]
        background_tasks.add_task(
            enviar_a_discord, edicion.discord_webhook_url, titulo, cuerpo, discord_ids
        )
