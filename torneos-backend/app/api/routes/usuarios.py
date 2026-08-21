"""Gestión de organizadores. Todo acá exige `puede_gestionar_organizadores`
— no alcanza con ser organizador a secas — porque esta es la única parte
del sistema donde el propio permiso de gestión está en juego. Sin ese
segundo nivel, cualquier organizador promovido podría sacarle el rol a
quien lo promovió a él.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, RequiereGestionDeOrganizadores
from app.domain.enums import EstadoPartida
from app.models import Edicion, Fase, Jugador, Partida, ParticipacionEnPartida, Torneo, Usuario
from app.schemas.usuarios import CambiarRolIn, MiInscripcionOut, MiPartidaOut, UsuarioAdminOut

router = APIRouter(prefix="/usuarios", tags=["usuarios"])

_ESTADOS_RELEVANTES = [
    EstadoPartida.CHECK_IN,
    EstadoPartida.EN_CURSO,
    EstadoPartida.REPORTADA,
    EstadoPartida.PROGRAMADA,
]
_PRIORIDAD_ESTADO = {
    EstadoPartida.EN_CURSO: 0,
    EstadoPartida.CHECK_IN: 1,
    EstadoPartida.REPORTADA: 2,
    EstadoPartida.PROGRAMADA: 3,
}


@router.get("/me/inscripciones", response_model=list[MiInscripcionOut])
def mis_inscripciones(db: DbSession, usuario: CurrentUser) -> list[MiInscripcionOut]:
    """Los equipos del usuario logueado, en cualquier edición — se arma
    cruzando `Jugador.discord_id` con el del usuario. No depende de que
    `Equipo` tenga un dueño explícito: ese vínculo ya existe porque el
    capitán se registra con su `discord_id` (ver `inscribir_equipo`) o el
    organizador lo vincula después (`vincular_discord`).
    """
    jugadores = (
        db.query(Jugador)
        .filter(Jugador.discord_id == usuario.discord_id, Jugador.es_capitan.is_(True))
        .all()
    )

    resultado: list[MiInscripcionOut] = []
    vistas: set[int] = set()
    for jugador in jugadores:
        inscripcion = jugador.inscripcion
        if inscripcion.id in vistas:
            continue
        vistas.add(inscripcion.id)

        edicion = db.get(Edicion, inscripcion.edicion_id)
        if not edicion:
            continue
        torneo = db.get(Torneo, edicion.torneo_id)
        if not torneo:
            continue

        resultado.append(
            MiInscripcionOut(
                edicion_id=edicion.id,
                edicion_nombre=edicion.nombre,
                edicion_slug=edicion.slug,
                torneo_nombre=torneo.nombre,
                torneo_slug=torneo.slug,
                es_capitan=True,
                inscripcion=inscripcion,
            )
        )

    return resultado


@router.get("/me/partidas", response_model=list[MiPartidaOut])
def mis_partidas(db: DbSession, usuario: CurrentUser) -> list[MiPartidaOut]:
    """Las partidas de cualquiera de los equipos que el usuario capitanea,
    en cualquier torneo, que todavía necesitan algo de él (check-in,
    reportar, esperando al rival) o que ya tienen horario cargado —
    pensado para el 'Mis Partidas' del perfil: hoy nada le avisa al
    jugador que le toca actuar, tiene que ir a buscar el torneo a mano.

    No incluye partidas ya cerradas (`confirmada`, `walkover`, `bye`) ni
    sin horario/`programada` sin fecha — esas no necesitan que el jugador
    haga nada todavía.
    """
    equipo_ids = {
        j.inscripcion.equipo_id
        for j in db.query(Jugador)
        .filter(Jugador.discord_id == usuario.discord_id, Jugador.es_capitan.is_(True))
        .all()
    }
    if not equipo_ids:
        return []

    partida_ids = {
        pp.partida_id
        for pp in db.query(ParticipacionEnPartida).filter(ParticipacionEnPartida.equipo_id.in_(equipo_ids)).all()
    }
    if not partida_ids:
        return []

    partidas = (
        db.query(Partida)
        .filter(Partida.id.in_(partida_ids), Partida.estado.in_(_ESTADOS_RELEVANTES))
        .all()
    )
    # Sin horario, "programada" no es accionable todavía — el check-in ni
    # se puede abrir a mano sin saber cuándo es.
    partidas = [p for p in partidas if p.estado != EstadoPartida.PROGRAMADA or p.programada_para is not None]

    resultado: list[MiPartidaOut] = []
    for p in partidas:
        fase = db.get(Fase, p.fase_id)
        if not fase:
            continue
        edicion = db.get(Edicion, fase.edicion_id)
        if not edicion:
            continue
        torneo = db.get(Torneo, edicion.torneo_id)
        if not torneo:
            continue

        mi_participacion = next((part for part in p.participaciones if part.equipo_id in equipo_ids), None)
        rival = next((part for part in p.participaciones if part.equipo_id not in equipo_ids), None)

        resultado.append(
            MiPartidaOut(
                partida_id=p.id,
                fase_id=p.fase_id,
                fase_nombre=fase.nombre,
                edicion_nombre=edicion.nombre,
                edicion_slug=edicion.slug,
                torneo_nombre=torneo.nombre,
                estado=p.estado,
                ronda=p.ronda,
                mi_equipo_id=mi_participacion.equipo_id if mi_participacion else None,
                mi_equipo_nombre=mi_participacion.equipo.nombre if mi_participacion else None,
                rival_equipo_nombre=rival.equipo.nombre if rival else None,
                checkin_cierra_at=p.checkin_cierra_at,
                programada_para=p.programada_para,
            )
        )

    resultado.sort(
        key=lambda r: (
            _PRIORIDAD_ESTADO.get(r.estado, 9),
            r.programada_para or r.checkin_cierra_at or datetime.max.replace(tzinfo=timezone.utc),
        )
    )
    return resultado


@router.get("", response_model=list[UsuarioAdminOut])
def listar_usuarios(
    db: DbSession, _gestor: RequiereGestionDeOrganizadores, discord_id: str | None = None
) -> list[Usuario]:
    """Lista de quienes ya iniciaron sesión al menos una vez — de acá se
    elige a quién promover. Alguien que nunca hizo login no tiene fila
    todavía y no puede promoverse (no hay a quién).
    """
    q = db.query(Usuario)
    if discord_id:
        q = q.filter(Usuario.discord_id == discord_id)
    return q.order_by(Usuario.ultimo_login_at.desc()).all()


@router.patch("/{usuario_id}/rol", response_model=UsuarioAdminOut)
def cambiar_rol(
    usuario_id: int, datos: CambiarRolIn, db: DbSession, gestor_actual: RequiereGestionDeOrganizadores
) -> Usuario:
    """Promover a alguien a organizador, sacarle el rol, o darle/sacarle el
    permiso de gestionar organizadores en sí.

    Dos reglas que no se pueden romper con un click de más:

    1. No se puede dejar la plataforma con CERO organizadores activos.
    2. No se puede dejar la plataforma con CERO personas que puedan
       gestionar organizadores — si eso pasara, nadie podría corregirlo
       nunca más sin tocar la base de datos a mano.

    Un organizador promovido normal (`puede_gestionar_organizadores=False`)
    puede operar el torneo entero, pero nunca puede tocar esta lista — ni
    siquiera la suya propia.
    """
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese usuario no existe.")

    nuevo_es_organizador = datos.es_organizador

    if datos.puede_gestionar_organizadores is not None:
        # Se pidió explícitamente un valor — si es una combinación
        # imposible, hay que avisar, no adivinar qué quiso decir.
        nuevo_puede_gestionar = datos.puede_gestionar_organizadores
        if nuevo_puede_gestionar and not nuevo_es_organizador:
            raise HTTPException(
                422,
                "No se le puede dar permiso de gestionar organizadores a alguien "
                "que al mismo tiempo deja de ser organizador.",
            )
    else:
        # No se especificó: hereda el valor actual, salvo que se está
        # sacando el rol de organizador — ahí cae en cascada sin que haga
        # falta pedirlo aparte, porque no tiene sentido "poder gestionar
        # organizadores" sin ser uno.
        nuevo_puede_gestionar = usuario.puede_gestionar_organizadores and nuevo_es_organizador

    # No dejar a nadie sin gente que pueda gestionar organizadores.
    if usuario.puede_gestionar_organizadores and not nuevo_puede_gestionar:
        quedan = (
            db.query(Usuario)
            .filter(
                Usuario.puede_gestionar_organizadores.is_(True),
                Usuario.id != usuario.id,
                Usuario.esta_activo.is_(True),
            )
            .count()
        )
        if quedan == 0:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No se le puede sacar el permiso de gestionar organizadores a "
                "la última persona que lo tiene — nadie podría revertirlo después. "
                "Dale este permiso a alguien más primero.",
            )

    # No dejar la plataforma sin ningún organizador activo.
    if usuario.es_organizador and not nuevo_es_organizador:
        organizadores_activos = (
            db.query(Usuario)
            .filter(
                Usuario.es_organizador.is_(True),
                Usuario.id != usuario.id,
                Usuario.esta_activo.is_(True),
            )
            .count()
        )
        if organizadores_activos == 0:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No se puede sacar el rol al último organizador activo — "
                "la plataforma se quedaría sin nadie que pueda administrarla. "
                "Promové a otra persona primero.",
            )
        nuevo_puede_gestionar = False  # no tiene sentido gestionar organizadores sin ser uno

    usuario.es_organizador = nuevo_es_organizador
    usuario.puede_gestionar_organizadores = nuevo_puede_gestionar
    db.commit()
    db.refresh(usuario)
    return usuario
