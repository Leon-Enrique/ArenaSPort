"""Catálogo inicial de juegos. Idempotente.

Agregar un juego nuevo es agregar una entrada acá — no requiere migración ni
cambios en el código del núcleo.
"""

from sqlalchemy.orm import Session

from app.domain.enums import ModeloCompetencia
from app.models import Juego

JUEGOS = [
    {
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
    },
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
    """Inserta los juegos que falten. No pisa los existentes."""
    existentes = {j.codigo for j in db.query(Juego).all()}
    nuevos = 0
    for datos in JUEGOS:
        if datos["codigo"] in existentes:
            continue
        db.add(Juego(**datos))
        nuevos += 1
    if nuevos:
        db.commit()
    return nuevos
