"""Perfiles públicos de equipos y jugadores, con historial entre torneos.

Hasta acá cada inscripción vivía aislada en su edición: un equipo que juega
cinco torneos eran cinco filas sin nada que las relacionara de cara al
público. Estos endpoints leen esa historia hacia atrás.

Todo es público y sin autenticación —es la vitrina del torneo—, con una
excepción que se respeta en cada respuesta: el `discord_id` de los jugadores
nunca sale. Identifica a una persona real y no tiene por qué ser público solo
porque la lista de equipos sí lo es.
"""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func

from app.api.deps import CurrentUser, DbSession
from app.domain.enums import EstadoInscripcion, EstadoPartida
from app.domain.perfiles import (
    PartidaDeEquipo,
    Record,
    calcular_record,
    gano_la_final,
    resumir_por_edicion,
)
from app.models import (
    Edicion,
    Equipo,
    Fase,
    Inscripcion,
    Jugador,
    Juego,
    Partida,
    ParticipacionEnPartida,
    Torneo,
)
from app.schemas.perfiles import (
    EquipoCreate,
    EquipoDeJugadorOut,
    EquipoEnListadoOut,
    EquipoUpdate,
    JugadorDePerfilOut,
    MiEquipoOut,
    ParticipacionEnTorneoOut,
    PerfilEquipoOut,
    PerfilJugadorOut,
    RecordOut,
)

router_equipos = APIRouter(prefix="/equipos", tags=["perfiles"])
router_jugadores = APIRouter(prefix="/jugadores", tags=["perfiles"])


def _a_record_out(record: Record) -> RecordOut:
    return RecordOut(
        jugadas=record.jugadas,
        ganadas=record.ganadas,
        perdidas=record.perdidas,
        mapas_favor=record.mapas_favor,
        mapas_contra=record.mapas_contra,
        diferencia_mapas=record.diferencia_mapas,
        byes=record.byes,
        porcentaje_victorias=record.porcentaje_victorias,
    )


def _partidas_del_equipo(db: DbSession, equipo_id: int) -> tuple[list[PartidaDeEquipo], dict[int, int | None]]:
    """Todas las partidas del equipo en cualquier torneo, más el mapa
    partida -> ganador (que hace falta aparte para decidir campeón).

    Se hace en dos consultas y se cruza en memoria en vez de con un join
    grande: la cantidad de partidas de un equipo es chica por definición
    (decenas, no miles) y así el mapeo a la vista de dominio queda a la
    vista en vez de escondido en un SELECT.
    """
    participaciones = (
        db.query(ParticipacionEnPartida)
        .filter(ParticipacionEnPartida.equipo_id == equipo_id)
        .all()
    )
    if not participaciones:
        return [], {}

    partida_ids = [p.partida_id for p in participaciones]
    partidas = db.query(Partida).filter(Partida.id.in_(partida_ids)).all()
    por_id = {p.id: p for p in partidas}

    fase_ids = {p.fase_id for p in partidas}
    fases = {f.id: f for f in db.query(Fase).filter(Fase.id.in_(fase_ids)).all()}

    ganadores: dict[int, int | None] = {}
    for p in partidas:
        ganador = next((part.equipo_id for part in p.participaciones if part.es_ganador), None)
        ganadores[p.id] = ganador

    vistas: list[PartidaDeEquipo] = []
    for participacion in participaciones:
        partida = por_id.get(participacion.partida_id)
        if partida is None:
            continue
        fase = fases.get(partida.fase_id)
        if fase is None:
            continue

        rival = next(
            (x for x in partida.participaciones if x.equipo_id != equipo_id), None
        )
        vistas.append(
            PartidaDeEquipo(
                partida_id=partida.id,
                edicion_id=fase.edicion_id,
                estado=str(partida.estado),
                es_ganador=participacion.es_ganador,
                mapas_propios=participacion.mapas_ganados,
                mapas_rival=rival.mapas_ganados if rival else None,
                ronda=partida.ronda,
                fase_id=partida.fase_id,
            )
        )

    return vistas, ganadores


def _roster_publico(inscripcion: Inscripcion | None) -> list[JugadorDePerfilOut]:
    if inscripcion is None:
        return []
    return [
        JugadorDePerfilOut(
            nick=j.nick, es_capitan=j.es_capitan, es_suplente=j.es_suplente
        )
        for j in sorted(inscripcion.jugadores, key=lambda j: j.orden)
    ]


@router_equipos.get("/mios", response_model=list[MiEquipoOut])
def mis_equipos(db: DbSession, usuario: CurrentUser) -> list[MiEquipoOut]:
    """Los equipos permanentes del usuario, para el selector de inscripción.

    Va ANTES de `/{equipo_id}` a propósito: si estuviera después, FastAPI
    intentaría interpretar "mios" como un id y devolvería un 422.
    """
    equipos = (
        db.query(Equipo)
        .filter(Equipo.propietario_usuario_id == usuario.id)
        .order_by(Equipo.nombre)
        .all()
    )
    if not equipos:
        return []

    ids = [e.id for e in equipos]
    torneos = dict(
        db.query(Inscripcion.equipo_id, func.count(func.distinct(Inscripcion.edicion_id)))
        .filter(
            Inscripcion.equipo_id.in_(ids),
            Inscripcion.estado == EstadoInscripcion.APROBADA,
        )
        .group_by(Inscripcion.equipo_id)
        .all()
    )
    return [
        MiEquipoOut(
            id=e.id, nombre=e.nombre, tag=e.tag, logo_url=e.logo_url,
            torneos_jugados=torneos.get(e.id, 0),
        )
        for e in equipos
    ]


@router_equipos.post("", response_model=MiEquipoOut, status_code=status.HTTP_201_CREATED)
def crear_equipo(datos: EquipoCreate, db: DbSession, usuario: CurrentUser) -> MiEquipoOut:
    """Crea un equipo permanente, del que el usuario queda dueño.

    A diferencia del equipo que nace de una inscripción, este existe por
    fuera de cualquier torneo y se puede inscribir en varios — que es lo que
    hace posible el historial acumulado.
    """
    nombre = datos.nombre.strip()
    ya_tiene = (
        db.query(Equipo)
        .filter(
            Equipo.propietario_usuario_id == usuario.id,
            Equipo.nombre.ilike(nombre),
        )
        .first()
    )
    if ya_tiene:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ya tenés un equipo llamado '{nombre}'.",
        )

    equipo = Equipo(
        nombre=nombre,
        tag=datos.tag,
        logo_url=datos.logo_url,
        propietario_usuario_id=usuario.id,
    )
    db.add(equipo)
    db.commit()
    db.refresh(equipo)
    return MiEquipoOut(
        id=equipo.id, nombre=equipo.nombre, tag=equipo.tag,
        logo_url=equipo.logo_url, torneos_jugados=0,
    )


@router_equipos.patch("/{equipo_id}", response_model=MiEquipoOut)
def editar_equipo(
    equipo_id: int, datos: EquipoUpdate, db: DbSession, usuario: CurrentUser
) -> MiEquipoOut:
    """Cambia nombre, tag o logo. Solo el dueño (o un organizador).

    El historial va con el equipo, no con el nombre: renombrarlo no borra ni
    reasigna nada de lo que ya jugó.
    """
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El equipo no existe.")
    if equipo.propietario_usuario_id != usuario.id and not usuario.es_organizador:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Este equipo no es tuyo."
        )

    if datos.nombre is not None:
        equipo.nombre = datos.nombre.strip()
    if datos.tag is not None:
        equipo.tag = datos.tag
    if datos.logo_url is not None:
        equipo.logo_url = datos.logo_url

    db.commit()
    db.refresh(equipo)
    return MiEquipoOut(
        id=equipo.id, nombre=equipo.nombre, tag=equipo.tag, logo_url=equipo.logo_url
    )


@router_equipos.get("", response_model=list[EquipoEnListadoOut])
def listar_equipos(
    db: DbSession,
    buscar: str | None = Query(default=None, description="Filtra por nombre o tag."),
    limite: int = Query(default=50, ge=1, le=200),
) -> list[EquipoEnListadoOut]:
    """Directorio de equipos, para poder llegar a un perfil sin tener el id.

    Solo aparecen los equipos con al menos una inscripción aprobada: un
    equipo que se anotó y fue rechazado no es parte de la vitrina.
    """
    q = (
        db.query(Equipo)
        .join(Inscripcion, Inscripcion.equipo_id == Equipo.id)
        .filter(Inscripcion.estado == EstadoInscripcion.APROBADA)
    )
    if buscar:
        patron = f"%{buscar.strip()}%"
        q = q.filter((Equipo.nombre.ilike(patron)) | (Equipo.tag.ilike(patron)))

    equipos = q.distinct().order_by(Equipo.nombre).limit(limite).all()
    if not equipos:
        return []

    ids = [e.id for e in equipos]

    torneos_por_equipo = dict(
        db.query(Inscripcion.equipo_id, func.count(func.distinct(Inscripcion.edicion_id)))
        .filter(
            Inscripcion.equipo_id.in_(ids),
            Inscripcion.estado == EstadoInscripcion.APROBADA,
        )
        .group_by(Inscripcion.equipo_id)
        .all()
    )

    ganadas_por_equipo = dict(
        db.query(ParticipacionEnPartida.equipo_id, func.count(ParticipacionEnPartida.id))
        .join(Partida, Partida.id == ParticipacionEnPartida.partida_id)
        .filter(
            ParticipacionEnPartida.equipo_id.in_(ids),
            ParticipacionEnPartida.es_ganador.is_(True),
            # Mismo criterio que el dominio: el bye no es una victoria.
            Partida.estado.in_([EstadoPartida.CONFIRMADA, EstadoPartida.WALKOVER]),
        )
        .group_by(ParticipacionEnPartida.equipo_id)
        .all()
    )

    return [
        EquipoEnListadoOut(
            id=e.id,
            nombre=e.nombre,
            tag=e.tag,
            logo_url=e.logo_url,
            torneos_jugados=torneos_por_equipo.get(e.id, 0),
            partidas_ganadas=ganadas_por_equipo.get(e.id, 0),
        )
        for e in equipos
    ]


@router_equipos.get("/{equipo_id}", response_model=PerfilEquipoOut)
def perfil_de_equipo(equipo_id: int, db: DbSession) -> PerfilEquipoOut:
    """Perfil público: récord acumulado entre todos los torneos, más el
    detalle de cada edición en la que participó."""
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El equipo no existe.")

    partidas, ganadores = _partidas_del_equipo(db, equipo_id)
    record_global = calcular_record(partidas)
    resumenes = {r.edicion_id: r for r in resumir_por_edicion(partidas)}

    inscripciones = (
        db.query(Inscripcion)
        .filter(
            Inscripcion.equipo_id == equipo_id,
            Inscripcion.estado == EstadoInscripcion.APROBADA,
        )
        .all()
    )

    historial: list[ParticipacionEnTorneoOut] = []
    titulos = 0

    for inscripcion in inscripciones:
        edicion = db.get(Edicion, inscripcion.edicion_id)
        if not edicion:
            continue
        torneo = db.get(Torneo, edicion.torneo_id)
        juego = db.get(Juego, edicion.juego_id)
        resumen = resumenes.get(edicion.id)

        # Campeón solo si ganó la última ronda de la ÚLTIMA fase de la
        # edición. Se pasa esa fase y nada más: `gano_la_final` es
        # conservador a propósito y no deduce campeones de una tabla.
        fases = (
            db.query(Fase).filter(Fase.edicion_id == edicion.id).order_by(Fase.orden).all()
        )
        campeon = False
        if fases:
            ultima_fase = fases[-1]
            del_final = [p for p in partidas if p.fase_id == ultima_fase.id]
            campeon = gano_la_final(del_final, equipo_id, ganadores)
        if campeon:
            titulos += 1

        historial.append(
            ParticipacionEnTorneoOut(
                edicion_id=edicion.id,
                edicion_nombre=edicion.nombre,
                edicion_slug=edicion.slug,
                torneo_nombre=torneo.nombre if torneo else "—",
                juego_nombre=juego.nombre if juego else "—",
                estado_edicion=str(edicion.estado),
                record=_a_record_out(resumen.record if resumen else Record()),
                ronda_maxima=resumen.ronda_maxima if resumen else None,
                campeon=campeon,
                roster=_roster_publico(inscripcion),
            )
        )

    # Más reciente primero: la última campaña es lo que interesa mirar.
    historial.sort(key=lambda h: h.edicion_id, reverse=True)

    return PerfilEquipoOut(
        id=equipo.id,
        nombre=equipo.nombre,
        tag=equipo.tag,
        logo_url=equipo.logo_url,
        created_at=equipo.created_at,
        propietario_usuario_id=equipo.propietario_usuario_id,
        record_global=_a_record_out(record_global),
        torneos_jugados=len(historial),
        titulos=titulos,
        historial=historial,
    )


@router_jugadores.get("/{juego_codigo}/{clave_identidad:path}", response_model=PerfilJugadorOut)
def perfil_de_jugador(juego_codigo: str, clave_identidad: str, db: DbSession) -> PerfilJugadorOut:
    """Carrera de un jugador dentro de un juego.

    La identidad va con el juego adelante porque `clave_identidad` se arma
    con los campos que pide cada juego (en MLBB es "id_juego|server"): la
    misma cadena en dos juegos distintos no es la misma persona.

    No devuelve estadísticas individuales porque el modelo no las tiene: los
    mapas, la posición y las bajas se registran por equipo. Lo que sí se
    puede afirmar es dónde jugó, y eso es lo que devuelve.
    """
    juego = db.query(Juego).filter(Juego.codigo == juego_codigo).first()
    if not juego:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El juego no existe.")

    jugadores = (
        db.query(Jugador)
        .join(Jugador.inscripcion)
        .join(Edicion, Edicion.id == Inscripcion.edicion_id)
        .filter(
            Jugador.clave_identidad == clave_identidad,
            Edicion.juego_id == juego.id,
            Inscripcion.estado == EstadoInscripcion.APROBADA,
        )
        .all()
    )
    if not jugadores:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No hay ningún jugador con esa identidad en este juego.",
        )

    equipos: list[EquipoDeJugadorOut] = []
    nicks: list[str] = []
    ediciones_vistas: set[int] = set()

    for j in jugadores:
        inscripcion = j.inscripcion
        edicion = db.get(Edicion, inscripcion.edicion_id)
        if not edicion:
            continue
        torneo = db.get(Torneo, edicion.torneo_id)
        equipo = db.get(Equipo, inscripcion.equipo_id)
        if not equipo:
            continue

        if j.nick not in nicks:
            nicks.append(j.nick)
        ediciones_vistas.add(edicion.id)

        equipos.append(
            EquipoDeJugadorOut(
                equipo_id=equipo.id,
                equipo_nombre=equipo.nombre,
                equipo_tag=equipo.tag,
                edicion_nombre=edicion.nombre,
                edicion_slug=edicion.slug,
                torneo_nombre=torneo.nombre if torneo else "—",
                es_capitan=j.es_capitan,
                es_suplente=j.es_suplente,
            )
        )

    equipos.sort(key=lambda e: e.equipo_id, reverse=True)

    return PerfilJugadorOut(
        clave_identidad=clave_identidad,
        juego_codigo=juego.codigo,
        juego_nombre=juego.nombre,
        nicks_usados=nicks,
        equipos=equipos,
        torneos_jugados=len(ediciones_vistas),
    )
