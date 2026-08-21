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
