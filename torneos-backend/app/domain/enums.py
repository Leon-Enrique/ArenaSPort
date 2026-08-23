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
