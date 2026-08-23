from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import ErrorAuth, decodificar_access_token
from app.db.database import get_db
from app.models import Usuario

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: DbSession,
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> Usuario:
    if credenciales is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Hace falta iniciar sesión. Mandá el token en el header "
            "'Authorization: Bearer <token>'.",
        )
    try:
        payload = decodificar_access_token(credenciales.credentials)
    except ErrorAuth as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e)) from e

    usuario = db.get(Usuario, int(payload["sub"]))
    if not usuario or not usuario.esta_activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado o inactivo.")
    return usuario


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def get_current_user_opcional(
    db: DbSession,
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
) -> Usuario | None:
    """Como get_current_user, pero nunca tira 401 — devuelve None si no hay
    token o es inválido. Sirve para endpoints públicos que igual quieren
    mostrar más si quien pregunta resulta ser el organizador (ver
    `listar_inscripciones`: el discord_id de cada jugador se redacta para
    cualquiera que no sea organizador, pero el endpoint en sí sigue siendo
    público)."""
    if credenciales is None:
        return None
    try:
        payload = decodificar_access_token(credenciales.credentials)
    except ErrorAuth:
        return None
    usuario = db.get(Usuario, int(payload["sub"]))
    if not usuario or not usuario.esta_activo:
        return None
    return usuario


UsuarioOpcional = Annotated[Usuario | None, Depends(get_current_user_opcional)]


def verificar_organizador(usuario: CurrentUser) -> Usuario:
    if not usuario.es_organizador:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Esta acción es solo para organizadores.",
        )
    return usuario


RequiereOrganizador = Annotated[Usuario, Depends(verificar_organizador)]


def verificar_gestor_de_organizadores(usuario: CurrentUser) -> Usuario:
    """Nivel separado de 'organizador' a secas — evita que cualquier
    organizador promovido pueda tocar quién más es organizador, incluida
    la persona que lo promovió a él."""
    if not usuario.es_organizador or not usuario.puede_gestionar_organizadores:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Esta acción es solo para quienes tienen permiso de gestionar organizadores.",
        )
    return usuario


RequiereGestionDeOrganizadores = Annotated[Usuario, Depends(verificar_gestor_de_organizadores)]


# ──────────────────────────────────────────────────────────────
# Staff de un torneo puntual
# ──────────────────────────────────────────────────────────────
#
# `es_organizador` es global: quien lo tiene administra TODOS los torneos.
# Eso hacía imposible pedir una mano puntual — para que alguien te ayudara en
# una copa había que darle acceso a toda la plataforma, o hacerlo vos.
#
# Estas dependencias resuelven el torneo desde el parámetro de la ruta
# (`edicion_id` o `fase_id`, que FastAPI inyecta solo porque el nombre
# coincide) y comprueban si el usuario puede operar ESE torneo.


def _torneo_de_edicion(db: Session, edicion_id: int) -> int | None:
    from app.models import Edicion

    edicion = db.get(Edicion, edicion_id)
    return edicion.torneo_id if edicion else None


def _torneo_de_fase(db: Session, fase_id: int) -> int | None:
    from app.models import Fase

    fase = db.get(Fase, fase_id)
    return _torneo_de_edicion(db, fase.edicion_id) if fase else None


def _puede_operar(db: Session, usuario: Usuario, torneo_id: int | None, solo_admin: bool) -> bool:
    from app.domain.enums import RolStaff
    from app.models import StaffDeTorneo

    # El organizador global entra siempre: delegar no le quita permisos a
    # quien delega.
    if usuario.es_organizador:
        return True
    if torneo_id is None:
        return False

    staff = (
        db.query(StaffDeTorneo)
        .filter(
            StaffDeTorneo.torneo_id == torneo_id,
            StaffDeTorneo.usuario_id == usuario.id,
        )
        .first()
    )
    if staff is None:
        return False
    if solo_admin:
        return staff.rol == RolStaff.ADMINISTRADOR
    return True


def _negar(solo_admin: bool) -> None:
    quienes = (
        "el organizador o un administrador de este torneo"
        if solo_admin
        else "el organizador, un administrador o un árbitro de este torneo"
    )
    raise HTTPException(status.HTTP_403_FORBIDDEN, f"Esta acción es para {quienes}.")


def staff_de_edicion(db: DbSession, usuario: CurrentUser, edicion_id: int) -> Usuario:
    """Árbitro o superior sobre el torneo de esta edición."""
    if not _puede_operar(db, usuario, _torneo_de_edicion(db, edicion_id), solo_admin=False):
        _negar(solo_admin=False)
    return usuario


def admin_de_edicion(db: DbSession, usuario: CurrentUser, edicion_id: int) -> Usuario:
    """Administrador o superior: armado del torneo (inscripciones, sorteo)."""
    if not _puede_operar(db, usuario, _torneo_de_edicion(db, edicion_id), solo_admin=True):
        _negar(solo_admin=True)
    return usuario


def staff_de_fase(db: DbSession, usuario: CurrentUser, fase_id: int) -> Usuario:
    """Árbitro o superior, resolviendo el torneo desde la fase."""
    if not _puede_operar(db, usuario, _torneo_de_fase(db, fase_id), solo_admin=False):
        _negar(solo_admin=False)
    return usuario


RequiereStaffDeEdicion = Annotated[Usuario, Depends(staff_de_edicion)]
RequiereAdminDeEdicion = Annotated[Usuario, Depends(admin_de_edicion)]
RequiereStaffDeFase = Annotated[Usuario, Depends(staff_de_fase)]
