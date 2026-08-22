"""equipo permanente con dueno, y equipo permanente opcional por edicion

Hasta acá cada inscripción creaba un `Equipo` nuevo, así que un equipo que
jugó cinco torneos eran cinco filas sin nada que las relacionara: el
historial acumulado era imposible de armar.

Se agrega:
  - `equipos.propietario_usuario_id`: quién administra el equipo. Nulo para
    los equipos que ya existen y para los que se sigan creando por
    inscripción anónima.
  - `ediciones.requiere_equipo_permanente`: si el organizador exige elegir
    un equipo ya existente (y por lo tanto tener cuenta) o deja anotarse
    suelto. Arranca apagado para no cambiar el comportamiento de ninguna
    edición actual.

Revision ID: 52de9bc8006a
Revises: c3a8e5b17d24
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52de9bc8006a'
down_revision: Union[str, Sequence[str], None] = 'c3a8e5b17d24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# La FK se nombra explícitamente: sin nombre, el downgrade no tiene qué
# borrar (`drop_constraint(None)` falla) y la revisión queda sin vuelta atrás.
FK_PROPIETARIO = "fk_equipos_propietario_usuario_id"


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("ediciones", schema=None) as batch_op:
        # server_default además del default de Python: sin eso, las filas que
        # ya existen quedarían con NULL en una columna NOT NULL.
        batch_op.add_column(
            sa.Column(
                "requiere_equipo_permanente",
                sa.Boolean(),
                server_default="0",
                nullable=False,
            )
        )

    with op.batch_alter_table("equipos", schema=None) as batch_op:
        batch_op.add_column(sa.Column("propietario_usuario_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_equipos_propietario_usuario_id"),
            ["propietario_usuario_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            FK_PROPIETARIO, "usuarios", ["propietario_usuario_id"], ["id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("equipos", schema=None) as batch_op:
        batch_op.drop_constraint(FK_PROPIETARIO, type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_equipos_propietario_usuario_id"))
        batch_op.drop_column("propietario_usuario_id")

    with op.batch_alter_table("ediciones", schema=None) as batch_op:
        batch_op.drop_column("requiere_equipo_permanente")
