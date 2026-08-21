"""Subida y (solo en desarrollo) servido de evidencia. Cualquier usuario
logueado puede subir — un capitán tiene que poder adjuntar su propia
captura, no solo el organizador.
"""

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.deps import CurrentUser
from app.core.almacenamiento import ErrorAlmacenamiento, leer_evidencia_local, subir_evidencia

router = APIRouter(prefix="/evidencias", tags=["evidencias"])


class EvidenciaSubidaOut(BaseModel):
    url: str


@router.post("/subir", response_model=EvidenciaSubidaOut)
async def subir(archivo: UploadFile, _usuario: CurrentUser) -> EvidenciaSubidaOut:
    """Sube una captura y devuelve la URL para usar como `evidencia_url` en
    /reportar, /reportar-problema, etc. Máximo 8 MB, formatos de imagen
    comunes — es una captura de pantalla, no un archivo cualquiera.
    """
    contenido = await archivo.read()
    try:
        url = subir_evidencia(archivo.filename or "captura.png", contenido)
    except ErrorAlmacenamiento as e:
        raise HTTPException(422, str(e)) from e
    return EvidenciaSubidaOut(url=url)


@router.get("/archivo/{clave:path}")
def servir_archivo_local(clave: str) -> Response:
    """Solo existe para que el modo de desarrollo (ALMACENAMIENTO_LOCAL=True)
    tenga algo que responda a la URL que devolvió /subir. En producción con
    R2, `evidencia_url` apunta directo al bucket/CDN y este endpoint ni se
    usa — no es parte del diseño para servir archivos en serio.
    """
    resultado = leer_evidencia_local(clave)
    if resultado is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El archivo no existe.")
    contenido, content_type = resultado
    return Response(content=contenido, media_type=content_type)
