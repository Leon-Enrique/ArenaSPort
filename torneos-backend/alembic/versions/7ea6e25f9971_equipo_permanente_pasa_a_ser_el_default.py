"""equipo permanente pasa a ser el default

Da vuelta el server_default de ediciones.requiere_equipo_permanente, de 0 a 1.
El interruptor sigue existiendo y sigue siendo por edicion, copiando el
"Permanent teams only" de Toornament: lo que cambia es de que lado arranca.

Por que se dio vuelta: la identidad de juego paso a vivir en la cuenta (ver
identidades_de_juego). Sin cuenta no hay donde guardar el ID del jugador, no
hay a quien avisarle que lo sumaron a un equipo, y no hay forma de que se
vaya solo. El torneo de base sigue siendo posible apagando el flag, y ahi se
vuelve al roster tipeado por el capitan.

Las ediciones que YA existen no se tocan a proposito: se quedan en el valor
que tienen. Un torneo en curso que acepta inscripcion suelta la sigue
aceptando — cambiarle la regla a mitad de camino romperia inscripciones que
ya estan andando. El default nuevo aplica a las ediciones que se creen de
aca en adelante.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ea6e25f9971'
down_revision: Union[str, Sequence[str], None] = 'f5180082aebb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Postgres exige un booleano de verdad en un ALTER ... SET DEFAULT: con `1`
# corta con "la columna es de tipo boolean pero la expresion default es de
# tipo integer". SQLite lo acepta igual, asi que el error solo aparece en
# produccion — y como el Procfile encadena `alembic upgrade head && uvicorn`,
# se lleva puesto el deploy entero.
#
# Ojo: en las migraciones anteriores `server_default="1"` sobre booleanos SI
# funciona, porque van dentro de un CREATE TABLE, donde Postgres castea el
# literal. Es solo el ALTER el que no perdona.
VERDADERO = sa.text("true")
FALSO = sa.text("false")


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("ediciones", schema=None) as batch_op:
        batch_op.alter_column(
            "requiere_equipo_permanente",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=VERDADERO,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("ediciones", schema=None) as batch_op:
        batch_op.alter_column(
            "requiere_equipo_permanente",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=FALSO,
        )
