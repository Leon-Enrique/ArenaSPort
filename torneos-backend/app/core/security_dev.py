"""SOLO DESARROLLO Y PRUEBAS. Emite tokens sin pasar por Discord de verdad.

Nunca se expone como endpoint HTTP — se usa importándolo directamente desde
scripts de prueba (`probar_*.py`), donde no hay navegador para completar un
login OAuth real. En producción, la única forma de conseguir un token es el
flujo real de `/auth/discord/callback`.
"""

from sqlalchemy.orm import Session

from app.core.security import crear_access_token
from app.models import Usuario


def usuario_de_prueba(
    db: Session,
    discord_id: str,
    es_organizador: bool = False,
    username: str | None = None,
    puede_gestionar_organizadores: bool = False,
) -> Usuario:
    """Crea (o reutiliza) un Usuario y devuelve un token válido para él,
    exactamente como si hubiera iniciado sesión por Discord."""
    usuario = db.query(Usuario).filter(Usuario.discord_id == discord_id).first()
    if not usuario:
        usuario = Usuario(
            discord_id=discord_id,
            discord_username=username or f"usuario_prueba_{discord_id}",
            es_organizador=es_organizador,
            puede_gestionar_organizadores=puede_gestionar_organizadores,
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)
    return usuario


def token_de_prueba(
    db: Session,
    discord_id: str,
    es_organizador: bool = False,
    username: str | None = None,
    puede_gestionar_organizadores: bool = False,
) -> str:
    usuario = usuario_de_prueba(
        db, discord_id, es_organizador, username, puede_gestionar_organizadores
    )
    return crear_access_token(usuario.id, usuario.discord_id, usuario.es_organizador)
