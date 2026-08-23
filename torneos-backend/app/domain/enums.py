from enum import StrEnum


class ModeloCompetencia(StrEnum):
    """Cómo se enfrentan los equipos dentro de una partida."""

    ENFRENTAMIENTO_DIRECTO = "enfrentamiento_directo"  # 2 equipos: MLBB, CODM MP
    MULTI_EQUIPO = "multi_equipo"  # N escuadras: Free Fire, PUBG Mobile


class FormatoFase(StrEnum):
    """Formatos que el motor sabe generar de punta a punta.

    Estuvo un tiempo `LIGA_ACUMULATIVA` acá: se podía elegir al crear una
    fase y `sortear_fase` respondía "Formato no soportado todavía". Era el
    formato de battle royale (varias escuadras en el mismo lobby), y salió
    junto con Free Fire y CODM BR del catálogo — el motor no genera caídas
    multi-equipo ni calcula su tabla. Se agrega de nuevo cuando exista eso,
    no antes: un formato elegible que falla al sortear es peor que uno que
    no aparece.
    """

    ROUND_ROBIN = "round_robin"
    ELIMINACION_SIMPLE = "eliminacion_simple"
    ELIMINACION_DOBLE = "eliminacion_doble"
    SUIZO = "suizo"


class EstadoEdicion(StrEnum):
    BORRADOR = "borrador"
    INSCRIPCIONES_ABIERTAS = "inscripciones_abiertas"
    INSCRIPCIONES_CERRADAS = "inscripciones_cerradas"
    EN_CURSO = "en_curso"
    FINALIZADA = "finalizada"
    CANCELADA = "cancelada"


class EstadoInscripcion(StrEnum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    RETIRADA = "retirada"
    DESCALIFICADA = "descalificada"


# Estados en los que los jugadores de una inscripción siguen "ocupando" su
# cupo de elegibilidad, o sea que no pueden aparecer en otro equipo de la
# misma edición.
#
# RECHAZADA y RETIRADA quedan afuera: ese equipo no está compitiendo, así que
# retener a su gente solo los deja sin poder jugar con nadie. Antes no se
# distinguía y un rechazo dejaba a cinco jugadores bloqueados para toda la
# edición.
#
# DESCALIFICADA sí bloquea, y es a propósito: si los jugadores de un equipo
# descalificado pudieran reinscribirse con otro nombre, la sanción no
# significaría nada.
ESTADOS_QUE_OCUPAN_CUPO = frozenset({
    EstadoInscripcion.PENDIENTE,
    EstadoInscripcion.APROBADA,
    EstadoInscripcion.DESCALIFICADA,
})


class EstadoFase(StrEnum):
    PENDIENTE = "pendiente"
    SORTEADA = "sorteada"
    EN_CURSO = "en_curso"
    CERRADA = "cerrada"


class EstadoPartida(StrEnum):
    PROGRAMADA = "programada"
    CHECK_IN = "check_in"
    EN_CURSO = "en_curso"
    REPORTADA = "reportada"
    CONFIRMADA = "confirmada"
    EN_DISPUTA = "en_disputa"
    WALKOVER = "walkover"
    BYE = "bye"


class LadoLlave(StrEnum):
    """En eliminación doble: de qué lado del cuadro está la partida."""

    UNICA = "unica"  # eliminación simple
    ALTA = "alta"  # winners bracket
    BAJA = "baja"  # losers bracket
    GRAN_FINAL = "gran_final"


class RolStaff(StrEnum):
    """Rol de alguien que ayuda a correr UN torneo puntual.

    Distinto de `Usuario.es_organizador`, que es global y da acceso a todo.
    Acá el alcance es un torneo: se le puede dar una mano a alguien en la
    Copa de marzo sin que quede administrando el resto de la plataforma.

    ADMINISTRADOR opera el torneo completo: aprueba inscripciones, siembra,
    sortea, programa, resuelve disputas. Lo que NO puede es borrar el torneo
    ni tocar quién más es staff — eso queda para el organizador global, así
    delegar nunca implica perder el control de lo delegado.

    ARBITRO es el día de partido: programar, abrir check-in, resolver
    disputas, corregir resultados. No toca inscripciones ni sorteo, que son
    las decisiones de armado del torneo.
    """

    ADMINISTRADOR = "administrador"
    ARBITRO = "arbitro"
