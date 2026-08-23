"""modo de reporte por edicion y puntos de siembra

`ediciones.solo_organizador_reporta`: en True, el resultado lo carga el
organizador y no los capitanes. Para torneos presenciales o con arbitro en
cada mesa, donde hacer que los equipos reporten solo agrega pasos. Battlefy
ofrece la misma opcion. Arranca en False: el flujo de siempre.

`inscripciones.puntos_siembra`: puntos para ordenar la siembra (ranking
previo, temporadas pasadas, lo que el organizador decida). Sin esto la
siembra era o aleatoria o numero por numero a mano; con 32 equipos de nivel
dispar, sembrar al azar hace que los dos mejores puedan cruzarse en primera
ronda. Nullable: sin puntos cargados, la siembra sigue siendo aleatoria.


Revision ID: a5f07601fd8a
Revises: ffdcba36d86d
Create Date: 2026-08-23 15:04:20.181268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5f07601fd8a'
down_revision: Union[str, Sequence[str], None] = 'ffdcba36d86d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('ediciones', schema=None) as batch_op:
        batch_op.add_column(sa.Column('solo_organizador_reporta', sa.Boolean(), server_default='0', nullable=False))

    with op.batch_alter_table('inscripciones', schema=None) as batch_op:
        batch_op.add_column(sa.Column('puntos_siembra', sa.Integer(), nullable=True))



def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('inscripciones', schema=None) as batch_op:
        batch_op.drop_column('puntos_siembra')

    with op.batch_alter_table('ediciones', schema=None) as batch_op:
        batch_op.drop_column('solo_organizador_reporta')

