import os
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, RequiereOrganizador, UsuarioOpcional
from app.core import notificaciones
from app.domain.enums import ESTADOS_QUE_OCUPAN_CUPO, EstadoInscripcion
from app.domain.roster import (
    ConfigJuego,
    ErrorRoster,
    JugadorEntrada,
    normalizar_roster,
)
from app.models import (
    CambioDeRoster,
    Edicion,
    Equipo,
    Inscripcion,
    Jugador,
    ParticipacionEnPartida,
)
from app.schemas.inscripciones import (
    CambioDeRosterRead,
    InscripcionCreada,
    InscripcionCreate,
    InscripcionRead,
    PermisoCambioRosterOut,
    PermitirCambioRoster,
    RevisionInscripcion,
)

router = APIRouter(prefix="/ediciones/{edicion_id}/inscripciones", tags=["inscripciones"])


def _ahora() -> datetime:
    return datetime.now().astimezone()


def sincronizar_cupo_de_elegibilidad(inscripcion: Inscripcion) -> None:
    """Pone al día el flag `ocupa_cupo` de los jugadores según el estado de
    su inscripción.

    `Jugador.ocupa_cupo` es un derivado de `Inscripcion.estado` (ver
    ESTADOS_QUE_OCUPAN_CUPO), desnormalizado porque el índice único parcial
    que hace cumplir la elegibilidad no puede consultar otra tabla.

    Hay que llamarla desde CUALQUIER lugar que cambie el estado de una
    inscripción. Si se agrega uno nuevo y se olvida, el síntoma es silencioso
    y feo: un jugador queda bloqueado —o liberado— sin motivo visible.
    """
    ocupa = inscripcion.estado in ESTADOS_QUE_OCUPAN_CUPO
    for jugador in inscripcion.jugadores:
        jugador.ocupa_cupo = ocupa


def vincular_al_capitan(resultado, usuario) -> None:
    """Deja la cuenta de quien inscribe pegada a la fila del capitán, y a
    ninguna otra.

    La regla es "el que registra el equipo es su capitán y su dueño", igual
    que en Battlefy: quien crea el equipo queda de capitán y desde ahí puede
    pasarle el rol a otro miembro si hace falta.

    Antes esto lo decidía el cliente, que podía mandar un `discord_id` para
    CUALQUIER jugador del roster. Dos problemas:

      - El frontend le pegaba la cuenta de quien estaba logueado a la fila
        que estuviera marcada como capitán, fuera quien fuera esa persona.
        Si marcabas capitán a otro jugador, su fila quedaba con TU identidad:
        vos reportabas en su nombre y él no podía hacer nada.
      - Peor en general: cualquiera podía reclamar la cuenta de otro
        escribiéndola en el formulario, y quedar habilitado a reportar
        resultados por un equipo ajeno.

    Ahora la cuenta no la elige el cliente: sale de la sesión. Sin sesión no
    se vincula a nadie, y vincular a los demás jugadores sigue siendo tarea
    del organizador (`vincular-discord`), que es el camino auditado.
    """
    for jugador in resultado.jugadores:
        jugador.discord_id = (
            usuario.discord_id if (usuario is not None and jugador.es_capitan) else None
        )


def _obtener_edicion(db: DbSession, edicion_id: int) -> Edicion:
    edicion = db.get(Edicion, edicion_id)
    if not edicion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La edición no existe.")
    return edicion


def _normalizar_y_validar_roster(
    db: DbSession,
    edicion_id: int,
    juego,
    datos_jugadores: list,
    capitan_declarado: str | None,
    excluir_inscripcion_id: int | None = None,
):
    """Compartido entre crear y editar una inscripción. `excluir_inscripcion_id`
    es lo que hace que editar el propio roster no choque con la regla de
    elegibilidad contra uno mismo — sin esto, guardar sin cambios te diría
    que tus propios jugadores 'ya están inscritos en otro equipo'.
    """
    config = ConfigJuego(
        titulares_requeridos=juego.titulares_requeridos,
        suplentes_maximos=juego.suplentes_maximos,
        campos_requeridos=juego.campos_requeridos(),
        campos_clave=juego.campos_clave(),
    )

    entradas = [
        JugadorEntrada(
            identidad=j.identidad,
            es_suplente=j.es_suplente,
            es_capitan=j.es_capitan,
            discord_id=j.discord_id,
        )
        for j in datos_jugadores
    ]

    try:
        resultado = normalizar_roster(entradas, config, capitan_declarado)
    except ErrorRoster as e:
        raise HTTPException(422, str(e)) from e

    claves = [j.clave_identidad for j in resultado.jugadores]
    query = select(Jugador).where(
        Jugador.edicion_id == edicion_id,
        Jugador.clave_identidad.in_(claves),
        # Solo cuentan los que siguen ocupando cupo. Sin este filtro, rechazar
        # un equipo dejaba a sus cinco jugadores sin poder entrar en ningún
        # otro para el resto de la edición — atados a una inscripción muerta.
        Jugador.ocupa_cupo.is_(True),
    )
    if excluir_inscripcion_id is not None:
        query = query.where(Jugador.inscripcion_id != excluir_inscripcion_id)
    ya_inscritos = db.scalars(query).all()
    if ya_inscritos:
        # Nombrar el equipo, no solo el nick: con "Lyon ya está inscrito" el
        # capitán no sabe si es homónimo o si alguien de su plantel se anotó
        # por su cuenta en otro lado. Con el equipo lo resuelve solo.
        detalles = "; ".join(
            f"{j.nick} ya está inscrito en el equipo '{j.inscripcion.equipo.nombre}'"
            for j in ya_inscritos
        )
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{detalles}. Un jugador no puede estar en dos equipos de la misma edición.",
        )

    return resultado


def _verificar_capitan_de_inscripcion(db: DbSession, usuario, inscripcion: Inscripcion) -> None:
    """Como en partidas.py: el organizador puede actuar en nombre de
    cualquiera; si no, tiene que ser específicamente el capitán declarado
    de ESTA inscripción."""
    if usuario.es_organizador:
        return
    es_capitan = any(
        j.discord_id == usuario.discord_id and j.es_capitan for j in inscripcion.jugadores
    )
    if not es_capitan:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Solo el capitán de este equipo (o el organizador) puede editar la inscripción.",
        )


def _resolver_equipo(
    db: DbSession, edicion, datos: InscripcionCreate, usuario, nombre_normalizado: str
) -> tuple[Equipo, list[str]]:
    """Decide con qué `Equipo` se inscribe: uno permanente ya existente, o
    uno nuevo.

    Es el punto donde se gana (o se pierde) el historial acumulado. Antes esto
    creaba siempre una fila nueva, así que un equipo que jugó cinco torneos
    eran cinco equipos distintos y su perfil no podía mostrar nada.

    Tres caminos:
      - `equipo_id` explícito: reutiliza ese equipo. Exige ser el dueño —
        heredar el historial y los títulos de otro sería suplantarlo.
      - La edición exige equipo permanente: sin `equipo_id` no se pasa.
      - Ninguno de los dos: se crea uno nuevo, como siempre. Si quien
        inscribe está logueado queda como dueño, así el mismo equipo se puede
        reutilizar el año que viene.
    """
    avisos: list[str] = []

    if datos.equipo_id is not None:
        equipo = db.get(Equipo, datos.equipo_id)
        if not equipo:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese equipo no existe.")
        if usuario is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Para inscribir un equipo existente hay que iniciar sesión.",
            )
        es_duenio = equipo.propietario_usuario_id == usuario.id
        if not es_duenio and not usuario.es_organizador:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Este equipo no es tuyo. Solo su dueño puede inscribirlo.",
            )

        ya_inscrito = (
            db.query(Inscripcion)
            .filter(
                Inscripcion.edicion_id == edicion.id,
                Inscripcion.equipo_id == equipo.id,
                Inscripcion.estado != EstadoInscripcion.RECHAZADA,
            )
            .first()
        )
        if ya_inscrito:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Este equipo ya está inscrito en esta edición.",
            )

        # El nombre puede cambiar de temporada a temporada; el historial va
        # con el equipo, no con el texto.
        if nombre_normalizado and nombre_normalizado.lower() != equipo.nombre.lower():
            avisos.append(
                f"El equipo pasó a llamarse '{nombre_normalizado}' "
                f"(antes '{equipo.nombre}'). Su historial se mantiene."
            )
            equipo.nombre = nombre_normalizado
        return equipo, avisos

    if edicion.requiere_equipo_permanente:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este torneo pide inscribirse con un equipo permanente: creá tu "
            "equipo (o elegí uno que ya tengas) y volvé a intentar.",
        )

    equipo = Equipo(
        nombre=nombre_normalizado,
        tag=datos.tag,
        logo_url=datos.logo_url,
        contacto_nombre=datos.contacto_nombre,
        contacto_whatsapp=datos.contacto_whatsapp,
        contacto_discord=datos.contacto_discord,
        propietario_usuario_id=usuario.id if usuario else None,
    )
    db.add(equipo)
    db.flush()
    if usuario is None:
        avisos.append(
            "Te inscribiste sin iniciar sesión, así que este equipo no queda "
            "asociado a ninguna cuenta y no vas a poder reutilizarlo en otro "
            "torneo. Si querés que acumule historial, pedile al organizador "
            "que lo vincule."
        )
    return equipo, avisos


@router.post("", response_model=InscripcionCreada, status_code=status.HTTP_201_CREATED)
def inscribir_equipo(
    edicion_id: int, datos: InscripcionCreate, db: DbSession, usuario: UsuarioOpcional
) -> InscripcionCreada:
    """Registro de un equipo en un torneo.

    Sigue sin exigir login por defecto: anotarse sin cuenta es una ventaja
    real para torneos de base y no se toca. Lo que cambia es que, si quien
    inscribe SÍ tiene sesión, puede reutilizar un equipo suyo y arrastrar su
    historial — y el organizador puede exigirlo por torneo con
    `requiere_equipo_permanente`.

    Aplica las reglas de roster del organizador y devuelve los avisos de lo que
    el sistema asumió (suplentes, capitán) para que el equipo pueda corregir.
    """
    edicion = _obtener_edicion(db, edicion_id)

    if not edicion.acepta_inscripciones:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Las inscripciones no están abiertas (estado: {edicion.estado}).",
        )

    if edicion.inscripcion_cierra:
        ahora = datetime.now().astimezone()
        if ahora > edicion.inscripcion_cierra:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "El plazo de inscripción ya cerró."
            )

    if edicion.max_equipos:
        inscritos = (
            db.query(Inscripcion)
            .filter(
                Inscripcion.edicion_id == edicion_id,
                Inscripcion.estado.in_(
                    [EstadoInscripcion.PENDIENTE, EstadoInscripcion.APROBADA]
                ),
            )
            .count()
        )
        if inscritos >= edicion.max_equipos:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Ya se llenaron los {edicion.max_equipos} cupos.",
            )

    resultado = _normalizar_y_validar_roster(
        db, edicion_id, edicion.juego, datos.jugadores, datos.capitan_declarado
    )
    vincular_al_capitan(resultado, usuario)

    nombre_normalizado = datos.nombre_equipo.strip()
    duplicado = (
        db.query(Inscripcion)
        .join(Equipo)
        .filter(
            Inscripcion.edicion_id == edicion_id,
            Equipo.nombre.ilike(nombre_normalizado),
            Inscripcion.estado != EstadoInscripcion.RECHAZADA,
        )
        .first()
    )
    if duplicado:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya hay un equipo inscrito con el nombre '{nombre_normalizado}'.",
        )

    equipo, avisos_equipo = _resolver_equipo(db, edicion, datos, usuario, nombre_normalizado)

    # Torneo abierto: el equipo queda adentro sin revisión manual. Ojo con el
    # orden — todo lo que valida esta función (cupos, plazo, roster,
    # elegibilidad, nombre duplicado) ya corrió arriba. "Abierto" es sin
    # revisión, no sin reglas.
    aprobacion_automatica = not edicion.requiere_aprobacion
    inscripcion = Inscripcion(
        edicion_id=edicion_id,
        equipo_id=equipo.id,
        estado=EstadoInscripcion.APROBADA if aprobacion_automatica else EstadoInscripcion.PENDIENTE,
        revisada_at=datetime.now().astimezone() if aprobacion_automatica else None,
    )
    db.add(inscripcion)
    db.flush()

    for j in resultado.jugadores:
        db.add(
            Jugador(
                inscripcion_id=inscripcion.id,
                edicion_id=edicion_id,
                identidad=j.identidad,
                clave_identidad=j.clave_identidad,
                orden=j.orden,
                es_suplente=j.es_suplente,
                es_capitan=j.es_capitan,
                discord_id=j.discord_id,
            )
        )

    db.commit()
    db.refresh(inscripcion)

    avisos = list(resultado.avisos) + avisos_equipo
    if aprobacion_automatica:
        avisos.append(
            "Este torneo tiene inscripción abierta: tu equipo ya quedó aprobado, "
            "no hace falta esperar la revisión del organizador."
        )

    return InscripcionCreada(
        inscripcion=InscripcionRead.model_validate(inscripcion),
        avisos=avisos,
    )


@router.patch("/{inscripcion_id}", response_model=InscripcionCreada)
def editar_inscripcion(
    edicion_id: int, inscripcion_id: int, datos: InscripcionCreate, db: DbSession, usuario: CurrentUser
) -> InscripcionCreada:
    """El capitán (o el organizador) edita nombre, contacto o roster
    completo de un equipo ya inscrito.

    Mismo patrón que usa Toornament: mientras la inscripción está
    'pendiente' se edita libremente; si ya estaba 'aprobada', editar la
    devuelve a 'pendiente' — el organizador tiene que revisarla de nuevo,
    a propósito, para que un cambio no pase colado sin que nadie lo note.
    Una vez que el equipo ya fue colocado en una fase (tiene partidas
    generadas), no se puede editar más — ahí el cambio lo hace el
    organizador directo si hace falta.
    """
    inscripcion = db.get(Inscripcion, inscripcion_id)
    if not inscripcion or inscripcion.edicion_id != edicion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La inscripción no existe.")

    _verificar_capitan_de_inscripcion(db, usuario, inscripcion)

    if inscripcion.estado not in (EstadoInscripcion.PENDIENTE, EstadoInscripcion.APROBADA):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"No se puede editar una inscripción en estado '{inscripcion.estado}' — "
            "contactá al organizador si necesitás un cambio.",
        )

    ya_en_fase = (
        db.query(ParticipacionEnPartida)
        .filter(ParticipacionEnPartida.equipo_id == inscripcion.equipo_id)
        .first()
    )
    # Con el torneo ya sorteado el roster queda congelado, salvo que el
    # organizador haya abierto una ventana para este equipo. Es el caso real
    # de "se le rompió el celular al titular en cuartos": antes no había forma
    # de resolverlo ni siquiera siendo organizador.
    permiso_abierto = (
        inscripcion.cambio_roster_hasta is not None
        and _ahora() <= inscripcion.cambio_roster_hasta
    )
    if ya_en_fase and not permiso_abierto:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este equipo ya fue colocado en una fase del torneo, así que su "
            "plantel está congelado. Si hace falta un cambio, el organizador "
            "puede habilitarlo con "
            f"POST /ediciones/{edicion_id}/inscripciones/{inscripcion_id}"
            "/permitir-cambio-roster.",
        )

    # Los nicks de antes, para poder registrar qué cambió: unas líneas más
    # abajo el roster se reemplaza entero y estos jugadores se borran.
    nicks_previos = {j.nick for j in inscripcion.jugadores} if ya_en_fase else set()

    edicion = _obtener_edicion(db, edicion_id)
    resultado = _normalizar_y_validar_roster(
        db,
        edicion_id,
        edicion.juego,
        datos.jugadores,
        datos.capitan_declarado,
        excluir_inscripcion_id=inscripcion_id,
    )
    # Al reemplazar el roster vale la misma regla: la cuenta sale de la
    # sesión de quien edita, no de lo que mande el cliente.
    vincular_al_capitan(resultado, usuario)

    nombre_normalizado = datos.nombre_equipo.strip()
    duplicado = (
        db.query(Inscripcion)
        .join(Equipo)
        .filter(
            Inscripcion.edicion_id == edicion_id,
            Inscripcion.id != inscripcion_id,
            Equipo.nombre.ilike(nombre_normalizado),
            Inscripcion.estado != EstadoInscripcion.RECHAZADA,
        )
        .first()
    )
    if duplicado:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya hay otro equipo inscrito con el nombre '{nombre_normalizado}'.",
        )

    equipo = inscripcion.equipo
    equipo.nombre = nombre_normalizado
    equipo.tag = datos.tag
    equipo.logo_url = datos.logo_url
    equipo.contacto_nombre = datos.contacto_nombre
    equipo.contacto_whatsapp = datos.contacto_whatsapp
    equipo.contacto_discord = datos.contacto_discord

    # Reemplazo completo del roster: se borran los jugadores viejos y se
    # crean los nuevos ya normalizados. Es más simple y más seguro que
    # tratar de calcular un diff — con equipos de 5 a 7 personas no vale
    # la pena la complejidad de un merge fila por fila.
    for j_viejo in list(inscripcion.jugadores):
        db.delete(j_viejo)
    db.flush()

    for j in resultado.jugadores:
        db.add(
            Jugador(
                inscripcion_id=inscripcion.id,
                edicion_id=edicion_id,
                identidad=j.identidad,
                clave_identidad=j.clave_identidad,
                orden=j.orden,
                es_suplente=j.es_suplente,
                es_capitan=j.es_capitan,
                discord_id=j.discord_id,
            )
        )

    volvio_a_pendiente = inscripcion.estado == EstadoInscripcion.APROBADA
    if volvio_a_pendiente:
        inscripcion.estado = EstadoInscripcion.PENDIENTE
        inscripcion.revisada_at = None

    # El roster se reemplazó entero unas líneas arriba: los jugadores nuevos
    # nacen con el default y hay que dejarlos acordes al estado real.
    db.flush()
    sincronizar_cupo_de_elegibilidad(inscripcion)

    if ya_en_fase:
        # Cambio con el torneo en marcha: queda registrado. El permiso se
        # consume acá — vale para UN cambio, no para toda la ventana, para
        # que autorizar un reemplazo no habilite rehacer el plantel entero.
        #
        # Los nicks salen del roster normalizado y no de `inscripcion.jugadores`:
        # el roster se reemplazó borrando y volviendo a crear filas, y la
        # relación del ORM todavía no refleja eso.
        nicks_nuevos = {
            j.identidad.get("nick", "?") for j in resultado.jugadores
        }
        db.add(
            CambioDeRoster(
                inscripcion_id=inscripcion.id,
                entraron=", ".join(sorted(nicks_nuevos - nicks_previos)) or None,
                salieron=", ".join(sorted(nicks_previos - nicks_nuevos)) or None,
                motivo_autorizacion=inscripcion.cambio_roster_motivo,
                aplicado_por_usuario_id=usuario.id,
            )
        )
        inscripcion.cambio_roster_hasta = None

    db.commit()
    db.refresh(inscripcion)

    avisos = list(resultado.avisos)
    if volvio_a_pendiente:
        avisos.append(
            "Esta inscripción ya estaba aprobada — al editarla volvió a "
            "'pendiente' y el organizador tiene que revisarla de nuevo."
        )

    return InscripcionCreada(
        inscripcion=InscripcionRead.model_validate(inscripcion),
        avisos=avisos,
    )


def _redactar_para_publico(inscripciones: list[Inscripcion], usuario) -> list[InscripcionRead]:
    """El discord_id es un identificador real de una persona (a veces
    menor de edad) — no tiene por qué ser público solo porque la lista de
    equipos sí lo es. Se muestra completo únicamente si quien pregunta es
    organizador; para cualquier otro caso (incluido "nadie logueado", que
    es el 99% de las visitas a esta pantalla) se oculta.
    """
    es_organizador = usuario is not None and usuario.es_organizador
    resultado = []
    for insc in inscripciones:
        leida = InscripcionRead.model_validate(insc)
        if not es_organizador:
            for j in leida.jugadores:
                j.discord_id = None
        resultado.append(leida)
    return resultado


@router.get("", response_model=list[InscripcionRead])
def listar_inscripciones(
    edicion_id: int,
    db: DbSession,
    usuario: UsuarioOpcional,
    estado: EstadoInscripcion | None = Query(default=None),
) -> list[InscripcionRead]:
    _obtener_edicion(db, edicion_id)
    q = db.query(Inscripcion).filter(Inscripcion.edicion_id == edicion_id)
    if estado:
        q = q.filter(Inscripcion.estado == estado)
    inscripciones = q.order_by(Inscripcion.created_at).all()
    return _redactar_para_publico(inscripciones, usuario)


@router.get("/{inscripcion_id}", response_model=InscripcionRead)
def obtener_inscripcion(
    edicion_id: int, inscripcion_id: int, db: DbSession, usuario: UsuarioOpcional
) -> InscripcionRead:
    inscripcion = db.get(Inscripcion, inscripcion_id)
    if not inscripcion or inscripcion.edicion_id != edicion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La inscripción no existe.")
    return _redactar_para_publico([inscripcion], usuario)[0]


@router.post("/{inscripcion_id}/revisar", response_model=InscripcionRead)
def revisar_inscripcion(
    edicion_id: int, inscripcion_id: int, datos: RevisionInscripcion, db: DbSession,
    background_tasks: BackgroundTasks,
    _organizador: RequiereOrganizador,
) -> Inscripcion:
    """Aprobar o rechazar. Nunca se borra una inscripción: cambia de estado."""
    inscripcion = db.get(Inscripcion, inscripcion_id)
    if not inscripcion or inscripcion.edicion_id != edicion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La inscripción no existe.")

    if datos.estado == EstadoInscripcion.RECHAZADA and not datos.motivo_rechazo:
        raise HTTPException(
            422,
            "Para rechazar hay que indicar el motivo.",
        )

    inscripcion.estado = datos.estado
    inscripcion.motivo_rechazo = datos.motivo_rechazo
    inscripcion.revisada_at = datetime.now().astimezone()
    # Rechazar o retirar libera a sus jugadores para que puedan entrar en
    # otro equipo; descalificar los mantiene bloqueados a propósito.
    sincronizar_cupo_de_elegibilidad(inscripcion)

    edicion = _obtener_edicion(db, edicion_id)
    _notificar_revision(db, background_tasks, edicion, inscripcion, datos)

    db.commit()
    db.refresh(inscripcion)
    return inscripcion


def _notificar_revision(
    db: DbSession,
    background_tasks: BackgroundTasks,
    edicion: Edicion,
    inscripcion: Inscripcion,
    datos: RevisionInscripcion,
) -> None:
    """Avisa al plantel el veredicto. Solo para aprobada/rechazada: 'retirada'
    y 'descalificada' son acciones con contexto propio que el organizador ya
    conversa aparte, un aviso automático seco ahí haría más ruido que bien."""
    if datos.estado not in (EstadoInscripcion.APROBADA, EstadoInscripcion.RECHAZADA):
        return

    usuarios = notificaciones.usuarios_de_equipos(db, [inscripcion.equipo_id], edicion.id)
    if not usuarios:
        return

    nombre_equipo = inscripcion.equipo.nombre
    if datos.estado == EstadoInscripcion.APROBADA:
        titulo = f"Inscripción aprobada: {nombre_equipo}"
        cuerpo = f"{nombre_equipo} quedó adentro de {edicion.nombre}. Atentos al sorteo de llaves."
    else:
        titulo = f"Inscripción rechazada: {nombre_equipo}"
        cuerpo = f"{nombre_equipo} no fue aceptado en {edicion.nombre}.\nMotivo: {datos.motivo_rechazo}"

    notificaciones.notificar(
        db,
        background_tasks,
        tipo="inscripcion_revisada",
        usuarios=usuarios,
        titulo=titulo,
        cuerpo=cuerpo,
        url=f"/torneos/{edicion.slug}",
        edicion=edicion,
    )


@router.post("/sembrar-automatico", response_model=list[InscripcionRead])
def sembrar_automatico(
    edicion_id: int, db: DbSession, _organizador: RequiereOrganizador, semilla: int | None = None
) -> list[Inscripcion]:
    """Asigna un número de siembra (1..N) a los equipos aprobados.

    Aleatorio pero reproducible: si no se pasa semilla, se genera una y se
    puede consultar después — el sorteo tiene que poder demostrarse ante un
    reclamo, no ser una caja negra.
    """
    aprobadas = (
        db.query(Inscripcion)
        .filter(
            Inscripcion.edicion_id == edicion_id,
            Inscripcion.estado == EstadoInscripcion.APROBADA,
        )
        .order_by(Inscripcion.id)
        .all()
    )
    if len(aprobadas) < 2:
        raise HTTPException(422, "Hacen falta al menos 2 equipos aprobados para sembrar.")

    semilla_usada = semilla if semilla is not None else int.from_bytes(os.urandom(4), "big")
    rng = random.Random(semilla_usada)
    orden = list(range(len(aprobadas)))
    rng.shuffle(orden)

    for numero_seed, idx in enumerate(orden, start=1):
        aprobadas[idx].seed = numero_seed

    db.commit()
    for i in aprobadas:
        db.refresh(i)

    return sorted(aprobadas, key=lambda i: i.seed)


@router.patch("/{inscripcion_id}/seed", response_model=InscripcionRead)
def fijar_seed_manual(
    edicion_id: int, inscripcion_id: int, seed: int, db: DbSession, _organizador: RequiereOrganizador
) -> Inscripcion:
    """Ajuste manual de un seed puntual — el organizador corrige un caso,
    no re-sortea todo el torneo por eso."""
    inscripcion = db.get(Inscripcion, inscripcion_id)
    if not inscripcion or inscripcion.edicion_id != edicion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La inscripción no existe.")
    inscripcion.seed = seed
    db.commit()
    db.refresh(inscripcion)
    return inscripcion


@router.patch(
    "/{inscripcion_id}/jugadores/{jugador_id}/vincular-discord",
    response_model=InscripcionRead,
)
def vincular_discord(
    edicion_id: int,
    inscripcion_id: int,
    jugador_id: int,
    discord_id: str,
    db: DbSession,
    _organizador: RequiereOrganizador,
) -> Inscripcion:
    """El equipo se inscribió sin loguearse (es el caso normal); esto vincula
    a un jugador con su cuenta real de Discord después, para que pueda
    reportar resultados. Solo el organizador lo hace — evita que cualquiera
    se autoproclame capitán de un equipo ajeno.
    """
    inscripcion = db.get(Inscripcion, inscripcion_id)
    if not inscripcion or inscripcion.edicion_id != edicion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La inscripción no existe.")

    jugador = db.get(Jugador, jugador_id)
    if not jugador or jugador.inscripcion_id != inscripcion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese jugador no es de esta inscripción.")

    jugador.discord_id = discord_id
    db.commit()
    db.refresh(inscripcion)
    return inscripcion


@router.post(
    "/{inscripcion_id}/permitir-cambio-roster",
    response_model=PermisoCambioRosterOut,
)
def permitir_cambio_roster(
    edicion_id: int,
    inscripcion_id: int,
    datos: PermitirCambioRoster,
    db: DbSession,
    usuario: RequiereOrganizador,
) -> PermisoCambioRosterOut:
    """Habilita a un equipo a tocar su plantel con el torneo ya empezado.

    Existe por un caso concreto y muy común: a un titular se le rompe el
    celular en cuartos y el equipo necesita meter a alguien. Antes eso no
    tenía salida — el roster se congelaba al sortear y el bloqueo no tenía
    excepción ni siquiera para el organizador; el mensaje de error mandaba a
    hacerlo "directamente" y no existía ningún endpoint para eso.

    Tres límites, para que la puerta no quede abierta:

    - **Dura poco.** Como mucho una semana, 24 horas por defecto.
    - **Vale para un solo cambio.** Se consume al usarlo, así que autorizar
      un reemplazo no habilita rehacer el plantel entero.
    - **Deja rastro.** Cada cambio guarda quién entró, quién salió, cuándo y
      con qué motivo se autorizó. Cambiar un roster en cuartos es justo lo
      que se discute después, y sin registro es tu palabra contra la de
      ellos.

    La elegibilidad se sigue aplicando: el jugador que entra no puede estar
    en otro equipo de esta edición.
    """
    inscripcion = db.get(Inscripcion, inscripcion_id)
    if not inscripcion or inscripcion.edicion_id != edicion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La inscripción no existe.")

    if inscripcion.estado not in (EstadoInscripcion.PENDIENTE, EstadoInscripcion.APROBADA):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Esta inscripción está '{inscripcion.estado}': no tiene sentido "
            "habilitarle un cambio de plantel.",
        )

    inscripcion.cambio_roster_hasta = _ahora() + timedelta(hours=datos.horas)
    inscripcion.cambio_roster_motivo = datos.motivo.strip()
    db.commit()
    db.refresh(inscripcion)

    return PermisoCambioRosterOut(
        inscripcion_id=inscripcion.id,
        cambio_roster_hasta=inscripcion.cambio_roster_hasta,
        motivo=inscripcion.cambio_roster_motivo,
    )


@router.get("/{inscripcion_id}/cambios-de-roster", response_model=list[CambioDeRosterRead])
def historial_de_cambios(
    edicion_id: int, inscripcion_id: int, db: DbSession
) -> list[CambioDeRoster]:
    """Los cambios de plantel hechos con el torneo ya empezado, en orden.

    Público a propósito: la transparencia es el punto. Si un equipo cambió
    su roster antes de la final, cualquiera tiene que poder verlo — es lo que
    convierte una sospecha en un dato verificable.
    """
    inscripcion = db.get(Inscripcion, inscripcion_id)
    if not inscripcion or inscripcion.edicion_id != edicion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La inscripción no existe.")

    return (
        db.query(CambioDeRoster)
        .filter(CambioDeRoster.inscripcion_id == inscripcion_id)
        .order_by(CambioDeRoster.created_at)
        .all()
    )


@router.post("/{inscripcion_id}/transferir-capitania", response_model=InscripcionRead)
def transferir_capitania(
    edicion_id: int,
    inscripcion_id: int,
    jugador_id: int,
    db: DbSession,
    usuario: CurrentUser,
) -> Inscripcion:
    """Le pasa la capitanía a otro jugador del mismo equipo.

    Es el equivalente al ícono de estrella de Battlefy: el capitán entrega el
    rol a otro miembro. Sin esto el modelo queda rígido — si el capitán deja
    el equipo o simplemente no puede seguir, no habría forma de que otro
    reporte resultados, y despues del sorteo editar el roster está bloqueado.

    Lo puede hacer el capitán actual (entrega su propio rol) o el organizador
    (destraba el caso en que el capitán desapareció). Un jugador cualquiera
    no puede autoproclamarse.

    El jugador que recibe la capitanía queda SIN cuenta vinculada: el rol
    cambia de fila, pero la identidad de la persona no se puede adivinar. Que
    él vincule la suya es un paso aparte, del organizador
    (`vincular-discord`), que es el camino auditado.
    """
    inscripcion = db.get(Inscripcion, inscripcion_id)
    if not inscripcion or inscripcion.edicion_id != edicion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La inscripción no existe.")

    _verificar_capitan_de_inscripcion(db, usuario, inscripcion)

    nuevo = next((j for j in inscripcion.jugadores if j.id == jugador_id), None)
    if nuevo is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Ese jugador no es de este equipo."
        )
    if nuevo.es_capitan:
        raise HTTPException(422, "Ese jugador ya es el capitán.")

    for jugador in inscripcion.jugadores:
        jugador.es_capitan = jugador.id == jugador_id
        if jugador.id == jugador_id:
            # El rol se muda; la cuenta no. Nadie puede afirmar de quién es
            # la cuenta del nuevo capitán sin que él lo confirme.
            jugador.discord_id = None

    db.commit()
    db.refresh(inscripcion)
    return inscripcion


@router.post("/{inscripcion_id}/checkin", response_model=InscripcionRead)
def checkin_de_torneo(
    edicion_id: int, inscripcion_id: int, db: DbSession, usuario: CurrentUser
) -> Inscripcion:
    """El equipo confirma que va a estar en el torneo.

    Es el check-in DEL TORNEO, distinto del de cada partida: se hace una vez,
    antes del sorteo. Sirve para depurar equipos fantasma — entre inscribirse
    y arrancar pasan días y siempre hay algunos que no aparecen. Sortear con
    ellos deja el cuadro lleno de walkovers desde la primera ronda.

    Lo hace el capitán (o el organizador en su nombre, para el equipo que
    avisó por otro lado).
    """
    inscripcion = db.get(Inscripcion, inscripcion_id)
    if not inscripcion or inscripcion.edicion_id != edicion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La inscripción no existe.")

    _verificar_capitan_de_inscripcion(db, usuario, inscripcion)

    edicion = _obtener_edicion(db, edicion_id)
    if edicion.checkin_abre_at is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Este torneo no pide check-in."
        )

    ahora = _ahora()
    if ahora < edicion.checkin_abre_at:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El check-in abre el {edicion.checkin_abre_at:%d/%m a las %H:%M}.",
        )
    if edicion.checkin_cierra_at and ahora > edicion.checkin_cierra_at:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El check-in ya cerró. Hablá con el organizador.",
        )

    if inscripcion.estado != EstadoInscripcion.APROBADA:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Solo puede hacer check-in un equipo aprobado (está '{inscripcion.estado}').",
        )

    inscripcion.checkin_at = ahora
    db.commit()
    db.refresh(inscripcion)
    return inscripcion
