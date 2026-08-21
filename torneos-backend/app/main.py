import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth,
    evidencias,
    fases,
    inscripciones,
    notificaciones,
    partidas,
    torneos,
    usuarios,
)
from app.core.config import settings
from app.db.database import Base, SessionLocal, engine, es_sqlite
from app.db.seed import sembrar_juegos

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("torneos")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # SQLite (desarrollo local): create_all es cómodo, no hace falta correr
    # migraciones a mano para iterar rápido.
    # Postgres (producción): Alembic es la ÚNICA fuente de verdad del
    # esquema. Si create_all corriera acá también, crearía las tablas por
    # fuera del control de versiones de Alembic — correr
    # `alembic upgrade head` ANTES de levantar la app, nunca create_all.
    if es_sqlite:
        Base.metadata.create_all(bind=engine)
    else:
        log.info("Postgres detectado: el esquema lo gobierna Alembic, no create_all.")

    if settings.RUN_SEED:
        db = SessionLocal()
        try:
            nuevos = sembrar_juegos(db)
            if nuevos:
                log.info("Catálogo: %s juegos agregados", nuevos)
        finally:
            db.close()

    yield


app = FastAPI(
    title="Plataforma de Torneos",
    version="0.1.0",
    debug=settings.DEBUG,
    docs_url="/docs" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(auth.router_local, prefix="/api")
app.include_router(usuarios.router, prefix="/api")
app.include_router(notificaciones.router, prefix="/api")
app.include_router(evidencias.router, prefix="/api")
app.include_router(torneos.router_juegos, prefix="/api")
app.include_router(torneos.router_torneos, prefix="/api")
app.include_router(torneos.router_ediciones, prefix="/api")
app.include_router(inscripciones.router, prefix="/api")
app.include_router(fases.router, prefix="/api")
app.include_router(partidas.router, prefix="/api")
app.include_router(partidas.router_disputas, prefix="/api")


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
