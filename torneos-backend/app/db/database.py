from collections.abc import Generator
from datetime import UTC

from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.core.config import settings

es_sqlite = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if es_sqlite else {},
    pool_pre_ping=not es_sqlite,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class DateTimeUTC(TypeDecorator):
    """DateTime con zona, robusto entre SQLite y Postgres.

    SQLite no tiene tipo nativo con zona horaria: al guardar un datetime con
    offset y volver a leerlo, SQLAlchemy lo devuelve 'naive'. Esto reintroduce
    exactamente el bug que la regla 'nunca DateTime sin timezone' busca evitar,
    pero solo en desarrollo local — en Postgres el valor ya vuelve con tzinfo
    y este tipo no cambia nada.

    Se usa en TODAS las columnas de fecha/hora del proyecto en vez de
    DateTime(timezone=True) directo.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError(
                    "No se permite guardar un datetime sin zona horaria. "
                    "Usar datetime.now().astimezone() o datetime.now(UTC)."
                )
            # SQLite guarda el datetime tal cual y al leerlo lo devuelve
            # 'naive' (ver process_result_value, que lo reetiqueta como UTC).
            # Si el valor original no estaba ya en UTC (ej. datetime.now().astimezone()
            # en una zona con offset != 0), guardarlo sin convertir deja los
            # dígitos de reloj local en la fila, y al releerlos como si fueran
            # UTC el instante queda corrido por el offset local entero —
            # partidas con checkin_cierra_at recién puesto "a 15 minutos"
            # aparecen ya vencidas. Convertir a UTC antes de guardar lo evita.
            value = value.astimezone(UTC)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
