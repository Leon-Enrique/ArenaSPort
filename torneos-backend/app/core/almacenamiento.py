"""Almacenamiento de evidencia (capturas de resultados y disputas).

R2 es compatible con la API de S3, así que un solo cliente (boto3) sirve
para los dos. En desarrollo local, sin credenciales de R2, se guarda en
disco bajo ALMACENAMIENTO_LOCAL_DIR y se sirve por un endpoint propio — el
comportamiento observable es el mismo (subís un archivo, te devuelve una
URL), así que el resto del código nunca necesita saber cuál de los dos
está activo.
"""

import mimetypes
import secrets
import uuid
from pathlib import Path

import boto3
from botocore.config import Config as BotoConfig

from app.core.config import settings

EXTENSIONES_PERMITIDAS = {".png", ".jpg", ".jpeg", ".webp"}
TAMANO_MAXIMO_BYTES = 8 * 1024 * 1024  # 8 MB — es una captura de pantalla, no un video


class ErrorAlmacenamiento(Exception):
    """Error de negocio al subir evidencia."""


def _validar_archivo(nombre_original: str, contenido: bytes) -> str:
    ext = Path(nombre_original).suffix.lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise ErrorAlmacenamiento(
            f"Formato no permitido ({ext or 'sin extensión'}). "
            f"Usar: {', '.join(sorted(EXTENSIONES_PERMITIDAS))}."
        )
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise ErrorAlmacenamiento(
            f"El archivo pesa {len(contenido) / 1024 / 1024:.1f} MB, "
            f"el máximo es {TAMANO_MAXIMO_BYTES / 1024 / 1024:.0f} MB."
        )
    return ext


def _nombre_unico(prefijo: str, ext: str) -> str:
    # prefijo (ej "partida-42") + fecha implícita en la aleatoriedad, no hace
    # falta más que esto para no pisar archivos entre sí.
    return f"{prefijo}/{uuid.uuid4().hex}{ext}"


def _cliente_r2():
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def subir_evidencia(nombre_original: str, contenido: bytes, prefijo: str = "capturas") -> str:
    """Sube un archivo y devuelve la URL pública para guardar en
    `evidencia_url`. Lanza ErrorAlmacenamiento si el archivo no es válido.
    """
    ext = _validar_archivo(nombre_original, contenido)
    clave = _nombre_unico(prefijo, ext)

    if settings.ALMACENAMIENTO_LOCAL:
        destino = Path(settings.ALMACENAMIENTO_LOCAL_DIR) / clave
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
        return f"/api/evidencias/archivo/{clave}"

    if not settings.R2_BUCKET:
        raise ErrorAlmacenamiento(
            "R2 no está configurado (falta R2_BUCKET en .env) y "
            "ALMACENAMIENTO_LOCAL está en False."
        )

    content_type = mimetypes.guess_type(nombre_original)[0] or "application/octet-stream"
    cliente = _cliente_r2()
    cliente.put_object(
        Bucket=settings.R2_BUCKET,
        Key=clave,
        Body=contenido,
        ContentType=content_type,
    )

    base = settings.R2_PUBLIC_BASE_URL.rstrip("/")
    if not base:
        raise ErrorAlmacenamiento(
            "Falta R2_PUBLIC_BASE_URL en .env — sin eso no se puede armar la "
            "URL pública del archivo que se acaba de subir."
        )
    return f"{base}/{clave}"


def leer_evidencia_local(clave: str) -> tuple[bytes, str] | None:
    """Solo para el modo desarrollo (ALMACENAMIENTO_LOCAL=True). Devuelve
    (contenido, content_type) o None si no existe."""
    destino = Path(settings.ALMACENAMIENTO_LOCAL_DIR) / clave
    if not destino.is_file():
        return None
    content_type = mimetypes.guess_type(str(destino))[0] or "application/octet-stream"
    return destino.read_bytes(), content_type
