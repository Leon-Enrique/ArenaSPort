"""Las rutas de configuración no pueden depender del directorio de trabajo.

Existe por dos bugs reales, los dos silenciosos:

  - `DATABASE_URL=sqlite:///./torneos.db` es relativo al CWD. Arrancar
    uvicorn desde la raíz del repo en vez de desde `torneos-backend/` creaba
    y usaba una base vacía distinta, sin ningún error: la app levantaba
    perfecto y no había ni un torneo.
  - `ALMACENAMIENTO_LOCAL_DIR=./evidencias`, lo mismo, y peor: las capturas
    ya subidas quedaban en la carpeta vieja y las URLs guardadas en las
    disputas empezaban a devolver 404.

Los dos se resuelven anclando a la raíz del backend. Testear esto necesita
subprocesos: el CWD es del proceso, no algo que se pueda simular desde acá.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ_BACKEND = Path(__file__).resolve().parents[1]

LEER_RUTAS = (
    "from app.core.config import settings;"
    "print(settings.DATABASE_URL);"
    "print(settings.ALMACENAMIENTO_LOCAL_DIR)"
)


def entorno_limpio(**extra: str) -> dict[str, str]:
    """Entorno para los subprocesos, SIN las variables que conftest.py fija
    para apuntar los tests a la base en memoria.

    Sin esta limpieza el subproceso hereda `DATABASE_URL=sqlite://` y estos
    tests dejarían de mirar lo que dicen mirar: la ruta que sale del `.env`
    del proyecto pasada por el anclaje.
    """
    entorno = {
        k: v
        for k, v in os.environ.items()
        if k not in ("DATABASE_URL", "ALMACENAMIENTO_LOCAL_DIR", "RUN_SEED")
    }
    entorno["PYTHONPATH"] = str(RAIZ_BACKEND)
    entorno.update(extra)
    return entorno


def rutas_desde(cwd: Path) -> tuple[str, str]:
    """Importa la configuración en un proceso nuevo lanzado desde `cwd` y
    devuelve (DATABASE_URL, ALMACENAMIENTO_LOCAL_DIR)."""
    resultado = subprocess.run(
        [sys.executable, "-c", LEER_RUTAS],
        cwd=cwd,
        env=entorno_limpio(),
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    db, evidencias = resultado.stdout.strip().splitlines()[:2]
    return db, evidencias


@pytest.fixture(scope="module")
def desde_el_backend() -> tuple[str, str]:
    return rutas_desde(RAIZ_BACKEND)


@pytest.fixture(scope="module")
def desde_otro_lado(tmp_path_factory) -> tuple[str, str]:
    return rutas_desde(tmp_path_factory.mktemp("cwd_ajeno"))


def test_la_base_es_la_misma_desde_cualquier_directorio(desde_el_backend, desde_otro_lado):
    assert desde_el_backend[0] == desde_otro_lado[0]


def test_las_evidencias_van_a_la_misma_carpeta(desde_el_backend, desde_otro_lado):
    assert desde_el_backend[1] == desde_otro_lado[1]


def test_la_base_sqlite_queda_bajo_la_raiz_del_backend(desde_otro_lado):
    url = desde_otro_lado[0]
    if not url.startswith("sqlite:///"):
        pytest.skip("configurado contra Postgres: no aplica")
    ruta = Path(url.removeprefix("sqlite:///"))
    assert ruta.is_absolute(), f"la ruta de la base quedó relativa: {ruta}"
    assert RAIZ_BACKEND in ruta.parents


def test_la_carpeta_de_evidencias_queda_bajo_la_raiz_del_backend(desde_otro_lado):
    ruta = Path(desde_otro_lado[1])
    assert ruta.is_absolute(), f"la carpeta de evidencias quedó relativa: {ruta}"
    assert RAIZ_BACKEND in ruta.parents


def test_una_ruta_absoluta_se_respeta_tal_cual(tmp_path):
    """Anclar no puede pisar una ruta que el operador puso a propósito —
    en producción el bucket o el volumen montado son absolutos."""
    absoluta = tmp_path / "evidencias_montadas"
    resultado = subprocess.run(
        [sys.executable, "-c", LEER_RUTAS],
        cwd=tmp_path,
        env=entorno_limpio(ALMACENAMIENTO_LOCAL_DIR=str(absoluta)),
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    devuelta = Path(resultado.stdout.strip().splitlines()[1])
    assert devuelta == absoluta


def test_una_url_de_postgres_no_se_toca(tmp_path):
    url_pg = "postgresql+psycopg://usuario:pass@host:5432/torneos"
    resultado = subprocess.run(
        [sys.executable, "-c", LEER_RUTAS],
        cwd=tmp_path,
        env=entorno_limpio(DATABASE_URL=url_pg),
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout.strip().splitlines()[0] == url_pg


def test_el_env_file_apunta_siempre_al_del_backend(tmp_path):
    """La causa raíz de los dos bugs: con `env_file=".env"` relativo, desde
    otro directorio el archivo no se encuentra y todo cae a los valores por
    defecto sin avisar.

    Se afirma que la ruta está anclada, no que el archivo exista: `.env` está
    en .gitignore y en CI no hay ninguno. Que exista o no depende del
    entorno; que apunte siempre al mismo lado es la propiedad que se arregló.
    """
    resultado = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path;"
            "from app.core.config import Settings;"
            "print(Path(Settings.model_config['env_file']).resolve())",
        ],
        cwd=tmp_path,
        env=entorno_limpio(),
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr
    ruta = Path(resultado.stdout.strip())
    assert ruta.is_absolute()
    assert ruta == (RAIZ_BACKEND / ".env").resolve()
