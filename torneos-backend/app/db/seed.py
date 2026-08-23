"""Catálogo de juegos. Idempotente.

Agregar un juego nuevo es agregar una entrada acá — no requiere migración ni
cambios en el código del núcleo.

Hoy la plataforma se enfoca en Mobile Legends y nada más. Los otros juegos
están definidos pero EN PAUSA (ver `JUEGOS_EN_PAUSA`): no se siembran, y si
existen en la base se desactivan, así no aparecen como opción.

Los dos de battle royale están en pausa por una razón concreta y no por
prioridades: **el motor no sabe correrlos**. Ningún generador crea caídas
multi-equipo, `calcular_tabla` solo entiende enfrentamientos de a dos, y
aunque `ParticipacionEnPartida` tiene `posicion`, `bajas` y `puntos`, no hay
ningún endpoint que los escriba. Un organizador podía crear un torneo de Free
Fire, aprobar equipos y sortear, para descubrir recién ahí que no hay forma
de cargar un resultado. Ofrecerlo así era peor que no ofrecerlo.
"""

from sqlalchemy.orm import Session

from app.domain.enums import ModeloCompetencia
from app.models import Juego

MLBB = {
    "codigo": "mlbb",
    "nombre": "Mobile Legends: Bang Bang",
    "modelo_competencia_default": ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
    "titulares_requeridos": 5,
    "suplentes_maximos": 2,
    "campos_identidad": {
        "campos": [
            {"nombre": "nick", "etiqueta": "Nick en el juego", "requerido": True},
            {"nombre": "id_juego", "etiqueta": "ID de jugador", "requerido": True},
            {"nombre": "server", "etiqueta": "Server ID", "requerido": True},
        ],
        "clave_unica": ["id_juego", "server"],
    },
}

# Lo único que se siembra y se deja activo.
JUEGOS = [MLBB]

# Definiciones conservadas para cuando se retomen. Reactivar uno es moverlo a
# `JUEGOS` — pero los de MULTI_EQUIPO necesitan además que exista el motor de
# battle royale, no alcanza con moverlos.
JUEGOS_EN_PAUSA = [
    {
        "codigo": "free_fire",
        "nombre": "Free Fire",
        "modelo_competencia_default": ModeloCompetencia.MULTI_EQUIPO,
        "titulares_requeridos": 4,
        "suplentes_maximos": 1,
        "campos_identidad": {
            "campos": [
                {"nombre": "nick", "etiqueta": "Nick en el juego", "requerido": True},
                {"nombre": "uid", "etiqueta": "UID", "requerido": True},
            ],
            "clave_unica": ["uid"],
        },
    },
    {
        "codigo": "codm_mp",
        "nombre": "Call of Duty Mobile — Multijugador",
        "modelo_competencia_default": ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        "titulares_requeridos": 5,
        "suplentes_maximos": 2,
        "campos_identidad": {
            "campos": [
                {"nombre": "nick", "etiqueta": "Nick en el juego", "requerido": True},
                {"nombre": "uid", "etiqueta": "UID", "requerido": True},
            ],
            "clave_unica": ["uid"],
        },
    },
    {
        "codigo": "codm_br",
        "nombre": "Call of Duty Mobile — Battle Royale",
        "modelo_competencia_default": ModeloCompetencia.MULTI_EQUIPO,
        "titulares_requeridos": 4,
        "suplentes_maximos": 1,
        "campos_identidad": {
            "campos": [
                {"nombre": "nick", "etiqueta": "Nick en el juego", "requerido": True},
                {"nombre": "uid", "etiqueta": "UID", "requerido": True},
            ],
            "clave_unica": ["uid"],
        },
    },
    {
        "codigo": "wild_rift",
        "nombre": "League of Legends: Wild Rift",
        "modelo_competencia_default": ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        "titulares_requeridos": 5,
        "suplentes_maximos": 2,
        "campos_identidad": {
            "campos": [
                {"nombre": "nick", "etiqueta": "Riot ID", "requerido": True},
                {"nombre": "tag", "etiqueta": "Tag (#)", "requerido": True},
            ],
            "clave_unica": ["nick", "tag"],
        },
    },
]


def sembrar_juegos(db: Session) -> int:
    """Inserta los juegos activos que falten y pausa los que estén en pausa.

    No pisa la configuración de un juego existente (campos de identidad,
    tamaño de plantel): solo inserta los que faltan y toca `esta_activo` de
    los pausados.

    Desactivar en cada arranque es a propósito, no un efecto colateral: es lo
    que hace que `JUEGOS_EN_PAUSA` signifique algo en una base que ya tiene
    esos juegos cargados de antes. Para reactivar uno hay que moverlo a
    `JUEGOS`, no cambiarlo a mano en la base — si no, el próximo arranque lo
    vuelve a apagar.

    Los datos que ya existan de un juego pausado (ediciones, inscripciones,
    partidas) no se tocan: pausar lo saca del catálogo, no borra historia.
    """
    por_codigo = {j.codigo: j for j in db.query(Juego).all()}
    nuevos = 0
    cambios = False

    for datos in JUEGOS:
        juego = por_codigo.get(datos["codigo"])
        if juego is None:
            db.add(Juego(**datos))
            nuevos += 1
            cambios = True
        elif not juego.esta_activo:
            juego.esta_activo = True
            cambios = True

    for datos in JUEGOS_EN_PAUSA:
        juego = por_codigo.get(datos["codigo"])
        if juego is not None and juego.esta_activo:
            juego.esta_activo = False
            cambios = True

    if cambios:
        db.commit()
    return nuevos
