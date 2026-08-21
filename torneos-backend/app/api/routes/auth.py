"""Login vía Discord OAuth2. Sin contraseñas — la identidad la garantiza
Discord, nosotros solo emitimos nuestro propio token después.
"""

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import (
    ErrorAuth,
    crear_access_token,
    hash_password,
    intercambiar_codigo_por_perfil,
    url_autorizacion_discord,
    verificar_password,
)
from app.models import Usuario

router = APIRouter(prefix="/auth/discord", tags=["auth"])
router_local = APIRouter(prefix="/auth/local", tags=["auth"])

# Guarda states pendientes en memoria — alcanza para un solo proceso; si el
# backend corre en más de una instancia hace falta moverlo a Redis o similar.
_states_pendientes: set[str] = set()


class LoginUrlOut(BaseModel):
    url: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: "UsuarioOut"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    discord_id: str
    discord_username: str
    discord_avatar_url: str | None
    es_organizador: bool


@router.get("/login", response_model=LoginUrlOut)
def iniciar_login() -> LoginUrlOut:
    """Devuelve la URL de Discord a la que el frontend tiene que redirigir
    al capitán para que inicie sesión."""
    if not settings.DISCORD_CLIENT_ID:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Discord OAuth no está configurado (falta DISCORD_CLIENT_ID en .env).",
        )
    state = secrets.token_urlsafe(24)
    _states_pendientes.add(state)
    return LoginUrlOut(url=url_autorizacion_discord(state))


@router.get("/callback", response_model=TokenOut)
async def callback(code: str, state: str, db: DbSession) -> TokenOut:
    """Discord redirige acá después de que el capitán aprueba el login."""
    if state not in _states_pendientes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "State inválido o vencido.")
    _states_pendientes.discard(state)

    try:
        perfil = await intercambiar_codigo_por_perfil(code)
    except ErrorAuth as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    discord_id = perfil["id"]
    usuario = db.query(Usuario).filter(Usuario.discord_id == discord_id).first()

    avatar_url = None
    if perfil.get("avatar"):
        avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{perfil['avatar']}.png"

    if usuario:
        usuario.discord_username = perfil["username"]
        usuario.discord_avatar_url = avatar_url
        usuario.ultimo_login_at = datetime.now(UTC)
    else:
        es_organizador_inicial = discord_id in settings.discord_ids_organizadores_iniciales
        usuario = Usuario(
            discord_id=discord_id,
            discord_username=perfil["username"],
            discord_avatar_url=avatar_url,
            es_organizador=es_organizador_inicial,
            # Quien arranca la plataforma tiene el permiso completo desde el
            # primer login — cualquiera que se promueva DESPUÉS empieza sin
            # este permiso (ver PATCH /usuarios/{id}/rol).
            puede_gestionar_organizadores=es_organizador_inicial,
        )
        db.add(usuario)

    db.commit()
    db.refresh(usuario)

    token = crear_access_token(usuario.id, usuario.discord_id, usuario.es_organizador)
    return TokenOut(access_token=token, usuario=UsuarioOut.model_validate(usuario))


@router.get("/callback/redirigir")
async def callback_redirigir(code: str, state: str, db: DbSession) -> RedirectResponse:
    """Variante que redirige al frontend con el token en el hash de la URL,
    en vez de devolver JSON — para cuando exista el frontend y el navegador
    del capitán sea quien reciba esto directamente."""
    resultado = await callback(code, state, db)
    frontend_url = settings.origenes_cors[0] if settings.origenes_cors else "http://localhost:3000"
    return RedirectResponse(f"{frontend_url}/auth/callback#token={resultado.access_token}")


@router.get("/yo", response_model=UsuarioOut)
def quien_soy(usuario: CurrentUser) -> UsuarioOut:
    """Para que el frontend sepa quién está logueado sin decodificar el
    token él mismo."""
    return UsuarioOut.model_validate(usuario)


# ──────────────────────────────────────────────────────────────
# Login por email/contraseña — alternativa a Discord mientras no haya
# credenciales de una app de Discord configuradas. Reusa crear_access_token
# y UsuarioOut tal cual: get_current_user (deps.py) resuelve al usuario por
# id numérico, nunca por discord_id, así que no hace falta tocar nada del
# flujo de Discord para que esto conviva con él.
# ──────────────────────────────────────────────────────────────
class RegistroIn(BaseModel):
    email: str
    password: str
    nombre: str


class LoginIn(BaseModel):
    email: str
    password: str


def _normalizar_email(email: str) -> str:
    email = email.strip().lower()
    if "@" not in email or len(email) < 5:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Email inválido.")
    return email


@router_local.post("/registro", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def registro(datos: RegistroIn, db: DbSession) -> TokenOut:
    """Alta pública. Siempre crea un usuario normal (es_organizador=False)
    — promover a organizador es una acción aparte, nunca algo que uno mismo
    elija al registrarse."""
    email = _normalizar_email(datos.email)
    if len(datos.password) < 8:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "La contraseña debe tener al menos 8 caracteres.")
    if not datos.nombre.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Falta el nombre.")

    if db.query(Usuario).filter(Usuario.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe una cuenta con ese email.")

    usuario = Usuario(
        discord_id=f"local:{email}",
        discord_username=datos.nombre.strip(),
        email=email,
        password_hash=hash_password(datos.password),
        es_organizador=False,
        puede_gestionar_organizadores=False,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    token = crear_access_token(usuario.id, usuario.discord_id, usuario.es_organizador)
    return TokenOut(access_token=token, usuario=UsuarioOut.model_validate(usuario))


@router_local.post("/login", response_model=TokenOut)
def login(datos: LoginIn, db: DbSession) -> TokenOut:
    email = _normalizar_email(datos.email)
    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if not usuario or not usuario.password_hash or not verificar_password(datos.password, usuario.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email o contraseña incorrectos.")
    if not usuario.esta_activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Esta cuenta está inactiva.")

    usuario.ultimo_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(usuario)

    token = crear_access_token(usuario.id, usuario.discord_id, usuario.es_organizador)
    return TokenOut(access_token=token, usuario=UsuarioOut.model_validate(usuario))
