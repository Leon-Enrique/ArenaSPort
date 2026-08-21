from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from slugify import slugify

from app.api.deps import DbSession, RequiereOrganizador
from app.core import notificaciones
from app.domain.enums import EstadoEdicion, EstadoInscripcion, EstadoPartida
from app.models import Edicion, Fase, Inscripcion, Jugador, Juego, Partida, ParticipacionEnPartida, Torneo
from app.schemas.fases import FaseRead, InfoJuegoResumen, PartidaResumen, ResumenEdicionOut
from app.schemas.inscripciones import (
    EdicionCreate,
    EdicionRead,
    EdicionUpdate,
    JuegoRead,
    TorneoCreate,
    TorneoRead,
)


class ResultadoPruebaWebhook(BaseModel):
    mensaje: str

router_juegos = APIRouter(prefix="/juegos", tags=["juegos"])
router_torneos = APIRouter(prefix="/torneos", tags=["torneos"])
router_ediciones = APIRouter(prefix="/ediciones", tags=["ediciones"])


@router_juegos.get("", response_model=list[JuegoRead])
def listar_juegos(db: DbSession) -> list[Juego]:
    """Catálogo de juegos soportados con sus campos de identidad.

    El formulario de inscripción se construye a partir de esto: no hardcodear
    los campos en el frontend.
    """
    return db.query(Juego).filter(Juego.esta_activo.is_(True)).all()


@router_torneos.post("", response_model=TorneoRead, status_code=status.HTTP_201_CREATED)
def crear_torneo(datos: TorneoCreate, db: DbSession, _organizador: RequiereOrganizador) -> Torneo:
    slug = slugify(datos.nombre)
    if db.query(Torneo).filter(Torneo.slug == slug).first():
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Ya existe un torneo con el slug '{slug}'."
        )
    torneo = Torneo(
        nombre=datos.nombre.strip(),
        slug=slug,
        descripcion=datos.descripcion,
        logo_url=datos.logo_url,
    )
    db.add(torneo)
    db.commit()
    db.refresh(torneo)
    return torneo


@router_torneos.get("", response_model=list[TorneoRead])
def listar_torneos(db: DbSession) -> list[Torneo]:
    return db.query(Torneo).order_by(Torneo.created_at.desc()).all()


@router_torneos.delete("/{torneo_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_torneo(torneo_id: int, db: DbSession, _organizador: RequiereOrganizador) -> None:
    """Borra un torneo completo — todas sus ediciones, fases, inscripciones
    (con sus jugadores) y partidas.

    Solo lo permite si NINGUNA partida de ninguna fase tuvo actividad real
    todavía (nada más que `programada` o `bye`) — un torneo con check-ins,
    reportes o resultados confirmados no se puede tirar así nomás, eso lo
    decide un organizador a mano. Pensado para limpiar torneos de prueba o
    mal configurados antes de que arranquen de verdad.

    Los equipos en sí (`Equipo`) NO se borran — son entidades independientes
    que pueden estar inscritas en otros torneos.
    """
    torneo = db.get(Torneo, torneo_id)
    if not torneo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El torneo no existe.")

    edicion_ids = [e.id for e in db.query(Edicion.id).filter(Edicion.torneo_id == torneo_id)]

    if edicion_ids:
        fase_ids = [f.id for f in db.query(Fase.id).filter(Fase.edicion_id.in_(edicion_ids))]

        if fase_ids:
            tocadas = (
                db.query(Partida)
                .filter(
                    Partida.fase_id.in_(fase_ids),
                    Partida.estado.notin_([EstadoPartida.PROGRAMADA, EstadoPartida.BYE]),
                )
                .count()
            )
            if tocadas:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Este torneo tiene {tocadas} partida(s) con actividad real (check-in, "
                    "reporte o resultado) — no se puede borrar desde acá.",
                )

            partida_ids = [p.id for p in db.query(Partida.id).filter(Partida.fase_id.in_(fase_ids))]
            if partida_ids:
                db.query(ParticipacionEnPartida).filter(
                    ParticipacionEnPartida.partida_id.in_(partida_ids)
                ).delete(synchronize_session=False)
                db.query(Partida).filter(Partida.id.in_(partida_ids)).delete(synchronize_session=False)

            db.query(Fase).filter(Fase.id.in_(fase_ids)).delete(synchronize_session=False)

        db.query(Jugador).filter(Jugador.edicion_id.in_(edicion_ids)).delete(synchronize_session=False)
        db.query(Inscripcion).filter(Inscripcion.edicion_id.in_(edicion_ids)).delete(synchronize_session=False)
        db.query(Edicion).filter(Edicion.id.in_(edicion_ids)).delete(synchronize_session=False)

    db.delete(torneo)
    db.commit()


@router_ediciones.post(
    "", response_model=EdicionRead, status_code=status.HTTP_201_CREATED
)
def crear_edicion(datos: EdicionCreate, db: DbSession, _organizador: RequiereOrganizador) -> Edicion:
    torneo = db.get(Torneo, datos.torneo_id)
    if not torneo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El torneo no existe.")
    if not db.get(Juego, datos.juego_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El juego no existe.")

    if (
        db.query(Edicion)
        .filter(Edicion.torneo_id == datos.torneo_id, Edicion.numero == datos.numero)
        .first()
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El torneo ya tiene una edición número {datos.numero}.",
        )

    edicion = Edicion(
        torneo_id=datos.torneo_id,
        juego_id=datos.juego_id,
        numero=datos.numero,
        nombre=datos.nombre.strip(),
        slug=slugify(f"{torneo.nombre}-{datos.nombre}"),
        max_equipos=datos.max_equipos,
        zona_horaria=datos.zona_horaria,
        fecha_inicio=datos.fecha_inicio,
        bolsa_premios=datos.bolsa_premios,
    )
    db.add(edicion)
    db.commit()
    db.refresh(edicion)
    return edicion


def _contar_equipos_aprobados(db: DbSession, edicion_id: int) -> int:
    return (
        db.query(Inscripcion)
        .filter(Inscripcion.edicion_id == edicion_id, Inscripcion.estado == EstadoInscripcion.APROBADA)
        .count()
    )


@router_ediciones.get("", response_model=list[EdicionRead])
def listar_ediciones(
    db: DbSession, torneo_id: int | None = None, slug: str | None = None
) -> list[Edicion]:
    q = db.query(Edicion)
    if torneo_id:
        q = q.filter(Edicion.torneo_id == torneo_id)
    if slug:
        q = q.filter(Edicion.slug == slug)
    ediciones = q.order_by(Edicion.numero.desc()).all()
    for edicion in ediciones:
        edicion.equipos_aprobados = _contar_equipos_aprobados(db, edicion.id)
    return ediciones


@router_ediciones.get("/{edicion_id}", response_model=EdicionRead)
def obtener_edicion(edicion_id: int, db: DbSession) -> Edicion:
    edicion = db.get(Edicion, edicion_id)
    if not edicion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La edición no existe.")
    edicion.equipos_aprobados = _contar_equipos_aprobados(db, edicion_id)
    return edicion


@router_ediciones.patch("/{edicion_id}", response_model=EdicionRead)
def actualizar_edicion(
    edicion_id: int, datos: EdicionUpdate, db: DbSession, _organizador: RequiereOrganizador
) -> Edicion:
    """Ajustes de una edición ya creada — hasta ahora lo único editable
    después del alta era el estado.

    `exclude_unset` es lo que hace que mandar solo `{"requiere_aprobacion":
    true}` no borre la bolsa de premios de paso.
    """
    edicion = db.get(Edicion, edicion_id)
    if not edicion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La edición no existe.")

    cambios = datos.model_dump(exclude_unset=True)

    if cambios.get("discord_webhook_url"):
        try:
            cambios["discord_webhook_url"] = notificaciones.validar_url_webhook(
                cambios["discord_webhook_url"]
            )
        except notificaciones.ErrorWebhook as e:
            raise HTTPException(422, str(e)) from e

    for campo, valor in cambios.items():
        setattr(edicion, campo, valor)

    db.commit()
    db.refresh(edicion)
    edicion.equipos_aprobados = _contar_equipos_aprobados(db, edicion_id)
    return edicion


@router_ediciones.post("/{edicion_id}/probar-webhook", response_model=ResultadoPruebaWebhook)
def probar_webhook(
    edicion_id: int, db: DbSession, _organizador: RequiereOrganizador
) -> ResultadoPruebaWebhook:
    """Manda un mensaje de prueba al canal. Sin esto, configurar un webhook
    es a ciegas: el envío real es una tarea de fondo que se traga los errores
    a propósito, así que un webhook mal pegado no se notaría hasta que un
    equipo reclame que nunca le avisaron."""
    edicion = db.get(Edicion, edicion_id)
    if not edicion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La edición no existe.")
    if not edicion.discord_webhook_url:
        raise HTTPException(422, "Esta edición no tiene webhook de Discord configurado.")

    try:
        notificaciones.enviar_a_discord_estricto(
            edicion.discord_webhook_url,
            "Prueba de configuración",
            f"Si ves este mensaje, los avisos de **{edicion.nombre}** van a llegar a este canal.",
        )
    except notificaciones.ErrorWebhook as e:
        raise HTTPException(422, str(e)) from e

    return ResultadoPruebaWebhook(mensaje="Mensaje enviado. Revisá el canal de Discord.")


@router_ediciones.post("/{edicion_id}/estado", response_model=EdicionRead)
def cambiar_estado_edicion(
    edicion_id: int, estado: EstadoEdicion, db: DbSession, _organizador: RequiereOrganizador
) -> Edicion:
    """Abrir o cerrar inscripciones, arrancar el torneo, etc."""
    edicion = db.get(Edicion, edicion_id)
    if not edicion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La edición no existe.")
    edicion.estado = estado
    db.commit()
    db.refresh(edicion)
    return edicion


def _partida_a_resumen(p: Partida, nombre_fase: str) -> PartidaResumen:
    a = p.participaciones[0] if len(p.participaciones) > 0 else None
    b = p.participaciones[1] if len(p.participaciones) > 1 else None
    return PartidaResumen(
        id=p.id,
        fase_id=p.fase_id,
        fase_nombre=nombre_fase,
        ronda=p.ronda,
        estado=p.estado,
        equipo_a_nombre=a.equipo.nombre if a else None,
        equipo_b_nombre=b.equipo.nombre if b else None,
        mapas_a=a.mapas_ganados if a else None,
        mapas_b=b.mapas_ganados if b else None,
        confirmada_at=p.confirmada_at,
        programada_para=p.programada_para,
    )


@router_ediciones.get("/{edicion_id}/resumen", response_model=ResumenEdicionOut)
def obtener_resumen(edicion_id: int, db: DbSession) -> ResumenEdicionOut:
    """Todo lo que necesita la pantalla pública de 'Vista general' de un
    torneo, en un solo pedido: últimos resultados, próximas partidas, info
    del juego, cantidad de equipos aprobados, y las fases — en vez de que
    el frontend arme eso combinando media docena de llamadas.
    """
    edicion = db.get(Edicion, edicion_id)
    if not edicion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La edición no existe.")

    juego = edicion.juego
    fases = db.query(Fase).filter(Fase.edicion_id == edicion_id).order_by(Fase.orden).all()
    fase_por_id = {f.id: f for f in fases}

    equipos_aprobados = _contar_equipos_aprobados(db, edicion_id)
    edicion.equipos_aprobados = equipos_aprobados

    if not fases:
        return ResumenEdicionOut(
            edicion=edicion,
            juego=InfoJuegoResumen(codigo=juego.codigo, nombre=juego.nombre),
            equipos_aprobados=equipos_aprobados,
            fases=[],
            ultimos_resultados=[],
            proximas_partidas=[],
        )

    fase_ids = list(fase_por_id.keys())
    todas_las_partidas = db.query(Partida).filter(Partida.fase_id.in_(fase_ids)).all()

    resueltas = [
        p for p in todas_las_partidas
        if p.estado in (EstadoPartida.CONFIRMADA, EstadoPartida.WALKOVER)
        and len(p.participaciones) == 2
    ]
    resueltas.sort(key=lambda p: p.confirmada_at or p.created_at, reverse=True)

    proximas = [
        p for p in todas_las_partidas
        if p.estado in (EstadoPartida.PROGRAMADA, EstadoPartida.CHECK_IN, EstadoPartida.EN_CURSO)
        and len(p.participaciones) == 2
    ]
    proximas.sort(key=lambda p: p.programada_para or p.created_at)

    return ResumenEdicionOut(
        edicion=edicion,
        juego=InfoJuegoResumen(codigo=juego.codigo, nombre=juego.nombre),
        equipos_aprobados=equipos_aprobados,
        fases=[FaseRead.model_validate(f) for f in fases],
        ultimos_resultados=[
            _partida_a_resumen(p, fase_por_id[p.fase_id].nombre) for p in resueltas[:6]
        ],
        proximas_partidas=[
            _partida_a_resumen(p, fase_por_id[p.fase_id].nombre) for p in proximas[:6]
        ],
    )
