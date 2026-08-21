"""Las migraciones tienen que construir exactamente el esquema que declaran
los modelos.

Existe por un bug real: `MensajePartida` se agregó al modelo pero nunca a una
migración. En SQLite no se notó nunca, porque el arranque llama a
`create_all` y la tabla aparecía sola; en Postgres, donde Alembic es la única
fuente de verdad y `create_all` no corre, la tabla no existía y el chat de
partidas fallaba con "relation does not exist".

El test no mira `mensajes_partida` en particular: compara el esquema COMPLETO,
así que cualquier modelo futuro que se agregue sin su migración cae acá antes
de llegar a producción — que es el único lugar donde el bug se manifiesta.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from app.db.database import Base
import app.models  # noqa: F401  registra todas las tablas en Base.metadata

RAIZ_BACKEND = Path(__file__).resolve().parents[1]

# Tablas internas de Alembic: no las declara ningún modelo, es correcto que
# estén en la base y no en la metadata.
TABLAS_DE_ALEMBIC = {"alembic_version"}


@pytest.fixture(scope="module")
def esquema_migrado(tmp_path_factory) -> dict[str, set[str]]:
    """Corre `alembic upgrade head` sobre una base vacía y devuelve
    {tabla: {columnas}} de lo que quedó.

    Subproceso a propósito: es el mismo comando que se corre en el deploy, y
    `alembic/env.py` lee la URL de settings en tiempo de import, así que
    necesita un proceso propio para tomar la base temporal.
    """
    destino = tmp_path_factory.mktemp("esquema") / "migrada.db"
    url = f"sqlite:///{destino.as_posix()}"

    entorno = {
        **os.environ,
        "DATABASE_URL": url,
        "RUN_SEED": "false",
        "PYTHONPATH": str(RAIZ_BACKEND),
    }
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=RAIZ_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, (
        f"'alembic upgrade head' falló sobre una base vacía:\n{resultado.stderr}"
    )

    motor = create_engine(url)
    inspector = inspect(motor)
    esquema = {
        tabla: {c["name"] for c in inspector.get_columns(tabla)}
        for tabla in inspector.get_table_names()
    }
    motor.dispose()
    return esquema


def test_las_migraciones_corren_de_cero(esquema_migrado):
    assert esquema_migrado, "la base migrada quedó sin ninguna tabla"


def test_no_falta_ninguna_tabla_declarada_en_los_modelos(esquema_migrado):
    """El caso de `mensajes_partida`: un modelo sin su migración."""
    declaradas = set(Base.metadata.tables)
    migradas = set(esquema_migrado) - TABLAS_DE_ALEMBIC
    faltan = declaradas - migradas
    assert not faltan, (
        f"Estos modelos no tienen migración: {sorted(faltan)}. "
        "En SQLite no se nota porque create_all las crea igual, pero en "
        "Postgres la tabla no va a existir. Generá la revisión que falta."
    )


def test_no_sobra_ninguna_tabla_en_las_migraciones(esquema_migrado):
    """El inverso: una tabla que las migraciones crean y ningún modelo usa
    ya — típicamente algo que se renombró o se dejó de usar sin limpiar."""
    declaradas = set(Base.metadata.tables)
    migradas = set(esquema_migrado) - TABLAS_DE_ALEMBIC
    sobran = migradas - declaradas
    assert not sobran, (
        f"Estas tablas existen en las migraciones pero ningún modelo las "
        f"declara: {sorted(sobran)}."
    )


def test_no_falta_ninguna_columna(esquema_migrado):
    """Una columna agregada al modelo sin migración rompe igual que una
    tabla entera, y es todavía más fácil que pase."""
    problemas = []
    for nombre, tabla in Base.metadata.tables.items():
        if nombre not in esquema_migrado:
            continue  # ya lo reporta el test de tablas
        declaradas = {c.name for c in tabla.columns}
        faltan = declaradas - esquema_migrado[nombre]
        if faltan:
            problemas.append(f"{nombre}: {sorted(faltan)}")
    assert not problemas, "Columnas sin migración -> " + "; ".join(problemas)


def test_la_tabla_del_chat_de_partidas_existe(esquema_migrado):
    """El caso concreto que originó todo esto, fijado aparte para que no
    vuelva a perderse entre el resto del esquema."""
    assert "mensajes_partida" in esquema_migrado
    columnas = esquema_migrado["mensajes_partida"]
    assert {"id", "partida_id", "equipo_id", "autor_nombre", "texto", "created_at"} <= columnas
