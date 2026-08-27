"""Las migraciones tienen que compilar para Postgres, no solo para SQLite.

Todo el desarrollo pasó contra SQLite y producción va a ser Postgres. Alembic
puede renderizar la cadena entera a SQL de un dialecto SIN conectarse a
ninguna base (`alembic upgrade head --sql`), así que se puede verificar acá
que cada operación compila para Postgres.

Lo que esto SÍ descarta: errores de dialecto —un tipo que Postgres no
entiende, una operación que SQLAlchemy no sabe traducir—, que es la clase de
fallo más común al migrar de motor y la que rompe el deploy en el primer
`alembic upgrade head`.

Lo que NO descarta: que el SQL se ejecute bien contra un servidor real
(constraints que chocan con datos, permisos, extensiones). Para eso hace
falta un Postgres de verdad, que esta máquina no tiene.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ_BACKEND = Path(__file__).resolve().parents[1]

# No se conecta: en modo offline la URL solo elige el dialecto.
URL_FALSA = "postgresql+psycopg://usuario:pass@localhost:5432/nada"


@pytest.fixture(scope="module")
def sql_para_postgres() -> str:
    """La cadena completa de migraciones, renderizada a SQL de Postgres."""
    entorno = {
        k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "RUN_SEED")
    }
    entorno["DATABASE_URL"] = URL_FALSA
    entorno["PYTHONPATH"] = str(RAIZ_BACKEND)

    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=RAIZ_BACKEND,
        env=entorno,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, (
        "Las migraciones no compilan para Postgres. El deploy iba a fallar en "
        f"el primer 'alembic upgrade head':\n{r.stderr[-2000:]}"
    )
    return r.stdout


def test_la_cadena_entera_compila(sql_para_postgres):
    assert "CREATE TABLE" in sql_para_postgres


def test_estan_todas_las_revisiones(sql_para_postgres):
    """Si una revisión se saltea en silencio, el esquema de producción queda
    incompleto sin que nadie se entere."""
    aplicadas = sql_para_postgres.count("-- Running upgrade")
    versiones = len(list((RAIZ_BACKEND / "alembic" / "versions").glob("*.py")))
    assert aplicadas == versiones, (
        f"{versiones} archivos de migración pero {aplicadas} aplicadas"
    )


def test_se_crean_las_tablas_que_declaran_los_modelos(sql_para_postgres):
    from app.db.database import Base
    import app.models  # noqa: F401

    creadas = set(re.findall(r"CREATE TABLE (\w+)", sql_para_postgres))
    faltan = set(Base.metadata.tables) - creadas
    assert not faltan, f"no se crean en Postgres: {sorted(faltan)}"


def test_las_fechas_llevan_zona_horaria(sql_para_postgres):
    """La regla del proyecto es que ninguna columna de fecha va sin zona
    (ver `DateTimeUTC` en app/db/database.py). Un `TIMESTAMP` pelado en
    Postgres guardaría el instante equivocado y el bug aparecería recién
    cuando un check-in vence antes de tiempo."""
    sin_zona = re.findall(r"(\w+) TIMESTAMP(?! WITH TIME ZONE)", sql_para_postgres)
    assert not sin_zona, f"columnas de fecha sin zona horaria: {sorted(set(sin_zona))}"


def test_los_enums_se_guardan_como_texto(sql_para_postgres):
    """Con `native_enum=False` los enums son VARCHAR en los dos motores. Si
    alguno se declarara nativo, Postgres crearía un tipo ENUM propio y
    agregar un valor pasaría a necesitar una migración."""
    assert "CREATE TYPE" not in sql_para_postgres.upper()


def test_la_migracion_del_chat_funciona_offline(sql_para_postgres):
    """Esa revisión inspecciona la base para no recrear una tabla que
    `create_all` ya había hecho en desarrollo. En modo offline no hay base
    que inspeccionar, así que tiene que saber saltear ese chequeo — si no,
    la generación del SQL se corta a la mitad de la cadena."""
    assert "CREATE TABLE mensajes_partida" in sql_para_postgres


def test_alter_default_booleano_usa_true_false(sql_para_postgres):
    """Postgres rechaza `SET DEFAULT 1` en un ALTER de columna boolean.

    En CREATE TABLE el literal entero se casteá; en ALTER no. Usar `1`/`0`
    acá tira el deploy entero porque el Procfile encadena
    `alembic upgrade head && uvicorn`.
    """
    alters_con_entero = re.findall(
        r"ALTER COLUMN \w+ SET DEFAULT [01]\b",
        sql_para_postgres,
        flags=re.IGNORECASE,
    )
    assert not alters_con_entero, (
        "ALTER ... SET DEFAULT con entero sobre boolean rompe Postgres: "
        f"{alters_con_entero}"
    )
    assert "requiere_equipo_permanente SET DEFAULT true" in sql_para_postgres
