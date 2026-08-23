"""elegibilidad respeta el estado de la inscripcion, y discord_id mas largo

Dos arreglos que comparten migracion porque tocan las mismas dos tablas.

1) Elegibilidad
La regla "un jugador en un solo equipo por edicion" se hacia cumplir con un
UNIQUE(edicion_id, clave_identidad) que no sabe nada de estados. Al rechazar
un equipo, sus jugadores seguian ocupando cupo y no podian entrar en ningun
otro por el resto de la edicion, atados a una inscripcion muerta.

Se reemplaza por un indice unico PARCIAL sobre `ocupa_cupo`, un derivado del
estado de la inscripcion (la condicion no puede mirar otra tabla, de ahi la
desnormalizacion). Rechazada y retirada liberan a su gente; descalificada NO,
porque si no la sancion no significaria nada.

2) discord_id
Era String(40). Las cuentas locales guardan ahi un sintetico "local:<email>"
que con un email de 35 caracteres ya se pasa. SQLite ignora el largo de un
VARCHAR asi que en desarrollo entraba igual: el error solo iba a aparecer en
Postgres, o sea recien en produccion y con un usuario real sin poder
registrarse. 320 cubre el maximo de un email por RFC mas el prefijo.

Revision ID: b25513457704
Revises: a5f5cd2454e2
Create Date: 2026-08-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b25513457704'
down_revision: Union[str, Sequence[str], None] = 'a5f5cd2454e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Los enums se guardan por NOMBRE (native_enum=False), o sea en mayusculas.
ESTADOS_QUE_LIBERAN = ("RECHAZADA", "RETIRADA")


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("jugadores", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("ocupa_cupo", sa.Boolean(), server_default="1", nullable=False)
        )
        batch_op.alter_column(
            "discord_id",
            existing_type=sa.VARCHAR(length=40),
            type_=sa.String(length=320),
            existing_nullable=True,
        )
        batch_op.drop_constraint("uq_jugador_elegibilidad", type_="unique")
        batch_op.create_index(
            "uq_jugador_elegibilidad",
            ["edicion_id", "clave_identidad"],
            unique=True,
            sqlite_where=sa.text("ocupa_cupo = 1"),
            postgresql_where=sa.text("ocupa_cupo"),
        )

    # Backfill: esto NO lo genera autogenerate y sin esto el arreglo no sirve
    # para los datos que ya existen. Las columnas nuevas nacen todas en true,
    # asi que los jugadores de equipos ya rechazados seguirian bloqueados —
    # que es exactamente el bug que esta revision viene a cerrar.
    #
    # Va DESPUES de crear el indice a proposito: si hubiera duplicados entre
    # un equipo rechazado y uno vivo, el indice fallaria antes de liberarlos.
    # No puede pasar, porque el UNIQUE viejo ya impedia esos duplicados.
    op.execute(
        "UPDATE jugadores SET ocupa_cupo = false WHERE inscripcion_id IN "
        f"(SELECT id FROM inscripciones WHERE estado IN {ESTADOS_QUE_LIBERAN})"
    )

    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.alter_column(
            "discord_id",
            existing_type=sa.VARCHAR(length=40),
            type_=sa.String(length=320),
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema.

    Ojo: volver al UNIQUE comun puede fallar si mientras tanto se creo un
    jugador en un equipo nuevo cuyo cupo habia liberado un rechazo. Es la
    consecuencia esperable de volver a una regla mas estricta, no un error
    de esta migracion.
    """
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.alter_column(
            "discord_id",
            existing_type=sa.String(length=320),
            type_=sa.VARCHAR(length=40),
            existing_nullable=False,
        )

    with op.batch_alter_table("jugadores", schema=None) as batch_op:
        batch_op.drop_index(
            "uq_jugador_elegibilidad",
            sqlite_where=sa.text("ocupa_cupo = 1"),
            postgresql_where=sa.text("ocupa_cupo"),
        )
        batch_op.create_unique_constraint(
            "uq_jugador_elegibilidad", ["edicion_id", "clave_identidad"]
        )
        batch_op.alter_column(
            "discord_id",
            existing_type=sa.String(length=320),
            type_=sa.VARCHAR(length=40),
            existing_nullable=True,
        )
        batch_op.drop_column("ocupa_cupo")
