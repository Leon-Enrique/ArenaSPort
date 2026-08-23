"""sacar roster_lock, que nunca se aplico

`ediciones.roster_lock` existia desde el esquema inicial y ningun codigo lo
leyo jamas: no habia nada que bloqueara el plantel al llegar esa fecha. Un
organizador podia cargarla creyendo que congelaba los rosters, y no pasaba
nada — el peor tipo de campo, porque promete una regla que no existe.

Estaba en NULL en las 6 ediciones de la base, asi que no se pierde ningun
dato. Si mas adelante se implementa el bloqueo de plantel, la columna vuelve
junto con la logica que la respeta, no antes.

Revision ID: a5f5cd2454e2
Revises: 52de9bc8006a
Create Date: 2026-08-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import app.db.database  # para DateTimeUTC en el downgrade


# revision identifiers, used by Alembic.
revision: str = 'a5f5cd2454e2'
down_revision: Union[str, Sequence[str], None] = '52de9bc8006a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("ediciones", schema=None) as batch_op:
        batch_op.drop_column("roster_lock")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("ediciones", schema=None) as batch_op:
        # DateTimeUTC, no sa.DATETIME: el autogenerate propuso el tipo plano,
        # pero en este proyecto ninguna columna de fecha va sin zona horaria
        # (ver app/db/database.py). Volver con el tipo equivocado dejaria la
        # columna distinta de como estaba.
        batch_op.add_column(
            sa.Column("roster_lock", app.db.database.DateTimeUTC(timezone=True), nullable=True)
        )
