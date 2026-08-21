"""Emisión y verificación de tokens propios (JWT), y el cliente de Discord
OAuth2. No hay contraseñas: la identidad la garantiza Discord.
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


class ErrorAuth(Exception):
    """Error de negocio en el flujo de autenticación."""


def crear_access_token(usuario_id: int, discord_id: str, es_organizador: bool) -> str:
    """Emite un JWT propio. Se llama tanto desde el callback real de Discord
    como (para pruebas locales, sin credenciales de Discord) desde
    `app.core.security_dev`.
    """
    expira = datetime.now(UTC) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(usuario_id),
        "discord_id": discord_id,
        "es_organizador": es_organizador,
        "exp": expira,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decodificar_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise ErrorAuth("Token inválido o vencido.") from e


def url_autorizacion_discord(state: str) -> str:
    """La URL a la que se manda al capitán para que inicie sesión con Discord."""
    params = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "redirect_uri": settings.DISCORD_REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
        "state": state,
    }
    return f"{DISCORD_AUTHORIZE_URL}?{urlencode(params)}"


async def intercambiar_codigo_por_perfil(code: str) -> dict[str, Any]:
    """Cambia el `code` que devuelve Discord por el perfil del usuario
    (id, username, avatar). Una sola llamada de red hacia Discord — si algo
    falla acá, es un problema de red o de credenciales, no de lógica.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        token_resp = await client.post(
            DISCORD_TOKEN_URL,
            data={
                "client_id": settings.DISCORD_CLIENT_ID,
                "client_secret": settings.DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code != 200:
            raise ErrorAuth(f"Discord rechazó el código de autorización: {token_resp.text}")

        access_token = token_resp.json()["access_token"]

        perfil_resp = await client.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if perfil_resp.status_code != 200:
            raise ErrorAuth("No se pudo obtener el perfil de Discord.")

        return perfil_resp.json()
