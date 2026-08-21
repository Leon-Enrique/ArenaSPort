from enum import StrEnum


class ModeloCompetencia(StrEnum):
    """Cómo se enfrentan los equipos dentro de una partida."""

    ENFRENTAMIENTO_DIRECTO = "enfrentamiento_directo"  # 2 equipos: MLBB, CODM MP
    MULTI_EQUIPO = "multi_equipo"  # N escuadras: Free Fire, PUBG Mobile


class FormatoFase(StrEnum):
    ROUND_ROBIN = "round_robin"
    ELIMINACION_SIMPLE = "eliminacion_simple"
    ELIMINACION_DOBLE = "eliminacion_doble"
    SUIZO = "suizo"
    LIGA_ACUMULATIVA = "liga_acumulativa"


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
