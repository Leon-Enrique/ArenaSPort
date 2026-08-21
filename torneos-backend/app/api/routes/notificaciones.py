"""Bandeja de notificaciones del usuario logueado.

Todo acá está siempre acotado al usuario del token — no existe un endpoint
para leer las notificaciones de otro, ni siquiera para el organizador.
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models import Notificacion
from app.schemas.notificaciones import BandejaNotificaciones, NotificacionRead

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])

LIMITE_BANDEJA = 30


@router.get("", response_model=BandejaNotificaciones)
def listar_notificaciones(
    db: DbSession, usuario: CurrentUser, solo_no_leidas: bool = False
) -> BandejaNotificaciones:
    q = db.query(Notificacion).filter(Notificacion.usuario_id == usuario.id)
    if solo_no_leidas:
        q = q.filter(Notificacion.leida_at.is_(None))

    items = q.order_by(Notificacion.created_at.desc()).limit(LIMITE_BANDEJA).all()

    no_leidas = (
        db.query(Notificacion)
        .filter(Notificacion.usuario_id == usuario.id, Notificacion.leida_at.is_(None))
        .count()
    )

    return BandejaNotificaciones(
        items=[NotificacionRead.model_validate(n) for n in items],
        no_leidas=no_leidas,
    )


@router.post("/{notificacion_id}/leer", response_model=NotificacionRead)
def marcar_leida(notificacion_id: int, db: DbSession, usuario: CurrentUser) -> Notificacion:
    notificacion = db.get(Notificacion, notificacion_id)
    # Ajena o inexistente dan el mismo 404 a propósito: responder "existe
    # pero no es tuya" confirmaría que ese id existe.
    if not notificacion or notificacion.usuario_id != usuario.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La notificación no existe.")

    if not notificacion.leida_at:
        notificacion.leida_at = datetime.now().astimezone()
        db.commit()
        db.refresh(notificacion)
    return notificacion


@router.post("/leer-todas", response_model=BandejaNotificaciones)
def marcar_todas_leidas(db: DbSession, usuario: CurrentUser) -> BandejaNotificaciones:
    ahora = datetime.now().astimezone()
    db.query(Notificacion).filter(
        Notificacion.usuario_id == usuario.id, Notificacion.leida_at.is_(None)
    ).update({Notificacion.leida_at: ahora}, synchronize_session=False)
    db.commit()

    items = (
        db.query(Notificacion)
        .filter(Notificacion.usuario_id == usuario.id)
        .order_by(Notificacion.created_at.desc())
        .limit(LIMITE_BANDEJA)
        .all()
    )
    return BandejaNotificaciones(
        items=[NotificacionRead.model_validate(n) for n in items], no_leidas=0
    )
