"""Fixtures compartidas.

La mayoría de los tests de este paquete no las necesitan: el dominio
(`app/domain/formatos`, `tabla`, `partidas`, `roster`) es puro Python y se
testea sin base ni servidor, que es justamente por qué está separado así.

Las fixtures de acá son para la capa que sí toca la base — `app/domain/sorteo.py`
y las rutas.
"""

import os

import pytest

# La base de tests es SIEMPRE en memoria. Se fija ANTES de importar cualquier
# cosa de `app`, porque app.db.database crea el engine en tiempo de import
# leyendo settings: si se importa primero, el engine ya quedó apuntando a la
# base de desarrollo real y los tests la escribirían.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["RUN_SEED"] = "false"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.database import Base  # noqa: E402
from app.domain.enums import FormatoFase, ModeloCompetencia  # noqa: E402
from app.models import Edicion, Equipo, Fase, Juego, Torneo  # noqa: E402


@pytest.fixture
def db() -> Session:
    """Sesión contra una base SQLite en memoria, nueva por test.

    StaticPool + una sola conexión: sin esto cada checkout del pool abre una
    base en memoria distinta y las tablas creadas acá no existirían para la
    sesión que usa el test.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    sesion = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    try:
        yield sesion
    finally:
        sesion.close()
        engine.dispose()


@pytest.fixture
def juego(db: Session) -> Juego:
    return _crear_juego(db)


def _crear_juego(db: Session) -> Juego:
    j = Juego(
        codigo="mlbb",
        nombre="Mobile Legends",
        modelo_competencia_default=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        titulares_requeridos=5,
        suplentes_maximos=2,
        campos_identidad={
            "campos": [
                {"nombre": "nick", "etiqueta": "Nick", "requerido": True},
                {"nombre": "id_juego", "etiqueta": "ID", "requerido": True},
                {"nombre": "server", "etiqueta": "Server", "requerido": True},
            ],
            "clave_unica": ["id_juego", "server"],
        },
    )
    db.add(j)
    db.flush()
    return j


@pytest.fixture
def fabrica_fase(db: Session, juego: Juego):
    """Devuelve una función que arma una fase lista para sortear, con la
    cantidad de equipos que pida el test. Evita repetir el andamiaje de
    torneo -> edicion -> fase -> equipos en cada caso."""

    def crear(cantidad_equipos: int, formato: FormatoFase, config: dict | None = None):
        torneo = Torneo(nombre="Copa Test", slug=f"copa-test-{formato}")
        db.add(torneo)
        db.flush()
        edicion = Edicion(
            torneo_id=torneo.id,
            juego_id=juego.id,
            numero=1,
            nombre="Temporada 1",
            slug=f"copa-test-{formato}-t1",
        )
        db.add(edicion)
        db.flush()
        fase = Fase(
            edicion_id=edicion.id,
            orden=1,
            nombre="Fase 1",
            modelo_competencia=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
            formato=formato,
            config=config or {},
        )
        db.add(fase)
        db.flush()

        equipos = []
        for i in range(1, cantidad_equipos + 1):
            e = Equipo(nombre=f"Equipo {i}")
            db.add(e)
            equipos.append(e)
        db.flush()

        return fase, [e.id for e in equipos]

    return crear
