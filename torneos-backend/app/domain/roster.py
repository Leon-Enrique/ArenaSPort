"""Reglas de roster. Puro Python, sin dependencias de framework ni DB.

Implementa las reglas del organizador:
  - Si el equipo no marca suplentes, se asignan los últimos de la lista.
  - Si el capitán declarado no coincide con ningún nick, es el primero de la lista.
"""

from dataclasses import dataclass, field


class ErrorRoster(Exception):
    """Error de negocio en la composición de un roster."""


@dataclass
class JugadorEntrada:
    """Datos crudos de un jugador tal como llegan del formulario."""

    identidad: dict
    es_suplente: bool | None = None  # None = el equipo no lo especificó
    es_capitan: bool = False
    discord_id: str | None = None  # identidad global, no depende del juego


@dataclass
class ConfigJuego:
    titulares_requeridos: int
    suplentes_maximos: int
    campos_requeridos: list[str]
    campos_clave: list[str]


@dataclass
class JugadorNormalizado:
    identidad: dict
    clave_identidad: str
    orden: int
    es_suplente: bool
    es_capitan: bool
    discord_id: str | None = None


@dataclass
class ResultadoRoster:
    jugadores: list[JugadorNormalizado]
    avisos: list[str] = field(default_factory=list)


def construir_clave_identidad(identidad: dict, campos_clave: list[str]) -> str:
    """Clave estable para el índice único de elegibilidad.

    Se normaliza a minúsculas y sin espacios: los capitanes escriben el mismo ID
    de mil formas distintas.
    """
    partes = []
    for campo in campos_clave:
        valor = str(identidad.get(campo, "")).strip().lower()
        if not valor:
            raise ErrorRoster(f"Falta el campo de identidad obligatorio: {campo}")
        partes.append(valor)
    return "|".join(partes)


def validar_identidad(identidad: dict, config: ConfigJuego) -> str:
    """Valida la identidad de UN jugador y devuelve su clave.

    `normalizar_roster` valida el equipo entero de una vez, que es el flujo
    del capitán cargando el formulario. Esto es el otro camino: el jugador
    que acepta una invitación carga sus propios datos y llega solo, sin
    equipo alrededor contra el cual validar tamaños ni suplentes.

    La regla de qué campos son obligatorios es la misma en los dos lados a
    propósito — si se duplicara, un jugador podría entrar por invitación
    con datos que el formulario del capitán habría rechazado.
    """
    faltantes = [
        c for c in config.campos_requeridos if not str(identidad.get(c, "")).strip()
    ]
    if faltantes:
        raise ErrorRoster(f"Te faltan datos: {', '.join(faltantes)}.")
    return construir_clave_identidad(identidad, config.campos_clave)


def normalizar_roster(
    entradas: list[JugadorEntrada],
    config: ConfigJuego,
    capitan_declarado: str | None = None,
) -> ResultadoRoster:
    """Valida y completa un roster crudo.

    Args:
        entradas: jugadores en el orden en que los mandó el capitán.
        config: reglas del juego (tamaño de equipo, campos de identidad).
        capitan_declarado: nombre que puso el equipo como capitán. Puede ser el
            nombre real de la persona y no coincidir con ningún nick.

    Returns:
        ResultadoRoster con los jugadores normalizados y avisos de lo que se
        asumió automáticamente.

    Raises:
        ErrorRoster: si el roster no puede completarse.
    """
    avisos: list[str] = []

    minimo = config.titulares_requeridos
    maximo = config.titulares_requeridos + config.suplentes_maximos
    if len(entradas) < minimo:
        raise ErrorRoster(
            f"El equipo tiene {len(entradas)} jugadores y se requieren al menos {minimo}."
        )
    if len(entradas) > maximo:
        raise ErrorRoster(
            f"El equipo tiene {len(entradas)} jugadores y el máximo es {maximo}."
        )

    # Campos obligatorios presentes
    for i, e in enumerate(entradas, start=1):
        faltantes = [
            c
            for c in config.campos_requeridos
            if not str(e.identidad.get(c, "")).strip()
        ]
        if faltantes:
            raise ErrorRoster(
                f"Al jugador #{i} le faltan datos: {', '.join(faltantes)}."
            )

    # Sin duplicados dentro del mismo equipo
    claves = [construir_clave_identidad(e.identidad, config.campos_clave) for e in entradas]
    if len(set(claves)) != len(claves):
        raise ErrorRoster("Hay jugadores repetidos en el roster.")

    # --- Regla de suplentes ---
    nadie_marco_suplente = all(e.es_suplente is None for e in entradas)
    if nadie_marco_suplente:
        cantidad_suplentes = len(entradas) - config.titulares_requeridos
        indices_suplentes = (
            set(range(len(entradas) - cantidad_suplentes, len(entradas)))
            if cantidad_suplentes > 0
            else set()
        )
        if cantidad_suplentes > 0:
            avisos.append(
                f"El equipo no marcó suplentes: se asignaron los últimos "
                f"{cantidad_suplentes} de la lista."
            )
    else:
        indices_suplentes = {i for i, e in enumerate(entradas) if e.es_suplente}
        titulares = len(entradas) - len(indices_suplentes)
        if titulares != config.titulares_requeridos:
            raise ErrorRoster(
                f"Quedan {titulares} titulares y se requieren "
                f"{config.titulares_requeridos}."
            )

    # --- Regla de capitán ---
    indice_capitan: int | None = next(
        (i for i, e in enumerate(entradas) if e.es_capitan), None
    )

    if indice_capitan is None and capitan_declarado:
        buscado = capitan_declarado.strip().lower()
        indice_capitan = next(
            (
                i
                for i, e in enumerate(entradas)
                if str(e.identidad.get("nick", "")).strip().lower() == buscado
            ),
            None,
        )
        if indice_capitan is None:
            avisos.append(
                f"'{capitan_declarado}' no coincide con ningún nick del roster "
                f"(probablemente es el nombre real): se marcó como capitán al "
                f"primer jugador de la lista."
            )

    if indice_capitan is None:
        indice_capitan = 0
        if not capitan_declarado:
            avisos.append(
                "No se indicó capitán: se marcó al primer jugador de la lista."
            )

    if indice_capitan in indices_suplentes:
        avisos.append("El capitán quedó marcado como suplente. Revisar con el equipo.")

    jugadores = [
        JugadorNormalizado(
            identidad=e.identidad,
            clave_identidad=claves[i],
            orden=i,
            es_suplente=i in indices_suplentes,
            es_capitan=i == indice_capitan,
            discord_id=e.discord_id,
        )
        for i, e in enumerate(entradas)
    ]

    return ResultadoRoster(jugadores=jugadores, avisos=avisos)
