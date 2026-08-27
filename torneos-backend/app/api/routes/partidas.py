from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentUser,
    DbSession,
    RequiereOrganizador,
    RequiereStaffDeDisputa,
    RequiereStaffDeFase,
)
from app.core import notificaciones
from app.core.eventos import PUBLICADOR, topico_chat, topico_edicion
from app.domain import sorteo
from app.domain.enums import EstadoPartida, ModeloCompetencia
from app.domain.partidas import (
    CHECKIN_MINUTOS_ANTES,
    ErrorPartida,
    ResultadoCheckin,
    bo_para_ronda,
    debe_auto_abrir_checkin,
    evaluar_checkin,
    validar_marcador,
)
from app.models import (
    Disputa,
    Equipo,
    Fase,
    Inscripcion,
    Jugador,
    MensajePartida,
    Partida,
    ParticipacionEnPartida,
    ReporteResultado,
    Usuario,
)
from app.schemas.partidas import (
    AbrirCheckinIn,
    ConfirmarCheckinIn,
    ConfirmarResultadoIn,
    CorreccionAplicadaOut,
    CorregirResultadoIn,
    DisputaRead,
    ImpugnarResultadoIn,
    MensajePartidaIn,
    MensajePartidaRead,
    PartidaCreate,
    PartidaRead,
    ProgramarPartidaIn,
    ReportarResultadoIn,
    ReporteResultadoRead,
    ReportarProblemaIn,
    ResolverDisputaIn,
)

router = APIRouter(prefix="/fases/{fase_id}/partidas", tags=["partidas"])
router_disputas = APIRouter(prefix="/disputas", tags=["disputas"])


def _ahora() -> datetime:
    return datetime.now().astimezone()


def _publicar_cambio(db: Session, partida: Partida, tipo: str = "partida_actualizada") -> None:
    """Avisa a los streams SSE de la edición que esta partida cambió.

    Manda solo identificadores y el estado nuevo, no la partida serializada:
    el cliente ya sabe pedir los datos que necesita y con el permiso que le
    corresponde. Si el evento cargara la partida entera, el stream tendría
    que repetir las reglas de redacción de cada endpoint — y ahí es donde se
    filtra un campo que no debía salir.

    Se llama SIEMPRE después del commit: un suscriptor que reciba el aviso va
    a volver a consultar de inmediato, y si la transacción todavía no cerró
    leería el estado viejo.
    """
    fase = db.get(Fase, partida.fase_id)
    if fase is None:
        return
    PUBLICADOR.publicar(
        topico_edicion(fase.edicion_id),
        tipo,
        {
            "partida_id": partida.id,
            "fase_id": partida.fase_id,
            "estado": str(partida.estado),
        },
    )


def _obtener_fase(db: Session, fase_id: int) -> Fase:
    fase = db.get(Fase, fase_id)
    if not fase:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La fase no existe.")
    return fase


def _obtener_partida(db: Session, fase_id: int, partida_id: int) -> Partida:
    partida = db.get(Partida, partida_id)
    if not partida or partida.fase_id != fase_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La partida no existe.")
    return partida


def _equipos_y_nombres(partida: Partida) -> tuple[list[int], str]:
    """Los ids de los equipos de una partida y su nombre para mostrar
    ("Dragons vs Wolves")."""
    equipo_ids = [p.equipo_id for p in partida.participaciones]
    nombres = " vs ".join(p.equipo.nombre for p in partida.participaciones)
    return equipo_ids, nombres or f"Partida #{partida.id}"


def _notificar_partida(
    db: Session,
    background_tasks: BackgroundTasks,
    partida: Partida,
    *,
    tipo: str,
    titulo_plantilla: str,
    cuerpo: str,
) -> None:
    """Avisa a los planteles de ambos equipos de la partida. La edición sale
    de la fase — es la dueña del webhook y del slug de la URL."""
    fase = db.get(Fase, partida.fase_id)
    edicion = fase.edicion
    equipo_ids, nombres = _equipos_y_nombres(partida)

    usuarios = notificaciones.usuarios_de_equipos(db, equipo_ids, edicion.id)
    if not usuarios:
        return

    notificaciones.notificar(
        db,
        background_tasks,
        tipo=tipo,
        usuarios=usuarios,
        titulo=titulo_plantilla.format(partida=nombres),
        cuerpo=cuerpo,
        url=f"/torneos/{edicion.slug}",
        edicion=edicion,
    )


def _auto_abrir_checkins_vencidos(
    db: Session, partidas: list[Partida], background_tasks: BackgroundTasks
) -> None:
    """Abre solo el check-in de cualquier partida programada cuyo horario ya
    llegó — así el organizador no tiene que apretar "Abrir Check-in" a mano
    en cada cruce, solo cargar el horario una vez con /programar.

    Se llama desde los GET de partidas (piggyback en la lectura, no hace
    falta un scheduler aparte corriendo en segundo plano): cada vez que
    alguien mira el bracket, de paso se ponen al día las que ya vencieron.

    El aviso sale una sola vez por partida sin necesitar ningún registro de
    "ya notificada": la transición PROGRAMADA -> CHECK_IN ocurre una única
    vez, y las recargas siguientes ya no entran en este `if`.
    """
    ahora = _ahora()
    cambio = False
    for p in partidas:
        if p.estado == EstadoPartida.PROGRAMADA and debe_auto_abrir_checkin(p.programada_para, ahora):
            p.estado = EstadoPartida.CHECK_IN
            p.checkin_abre_at = ahora
            p.checkin_cierra_at = p.programada_para
            _notificar_partida(
                db, background_tasks, p,
                tipo="checkin_abierto",
                titulo_plantilla="Check-in abierto: {partida}",
                cuerpo="Confirmá tu presencia ahora. Si no hacés check-in a tiempo, la partida se pierde por walkover.",
            )
            cambio = True
    if cambio:
        db.commit()
        for p in partidas:
            if p.estado == EstadoPartida.CHECK_IN:
                _publicar_cambio(db, p, "checkin_abierto")


def _auto_resolver_reportes_vencidos(db: Session, partidas: list[Partida]) -> None:
    """Mismo patrón que `_auto_abrir_checkins_vencidos`, aplicado a reportes
    de resultado: si el plazo para que el rival confirme ya venció Y el
    reporte tiene evidencia adjunta, se autoconfirma con que alguien mire
    el bracket — no hace falta que el organizador entre a apretar
    "Resolver Reporte Vencido" a mano en cada partida.

    Sin evidencia sigue quedando trabado a propósito (ver
    `resolver_reporte_vencido`, que tiene la misma regla para el botón
    manual) — eso no lo resuelve solo ni por lectura ni por botón.
    """
    ahora = _ahora()
    for p in partidas:
        if p.estado != EstadoPartida.REPORTADA:
            continue
        reporte = _reporte_pendiente(db, p.id)
        if not reporte or not reporte.evidencia_url:
            continue
        if reporte.vencimiento and ahora < reporte.vencimiento:
            continue

        _aplicar_marcador(p, reporte.equipo_reportante_id, reporte.marcador_propio, reporte.marcador_rival)
        p.estado = EstadoPartida.CONFIRMADA
        p.confirmada_at = ahora
        reporte.estado = "confirmado"
        reporte.confirmado_at = ahora
        db.commit()
        db.refresh(p)
        sorteo.avanzar_ganador(db, p)
        db.refresh(p)
        _publicar_cambio(db, p, "resultado_confirmado")


def _verificar_capitan_del_equipo(db: Session, usuario: Usuario, equipo_id: int) -> None:
    """El equipo_id que manda el cliente en el body NO alcanza por sí solo —
    hay que comprobar que la persona detrás del token es realmente el
    capitán declarado de ese equipo. Sin esto, cualquiera con una cuenta de
    Discord podría reportar resultados en nombre de un equipo ajeno.
    """
    if usuario.es_organizador:
        return  # el organizador puede actuar en nombre de cualquier equipo

    es_capitan = (
        db.query(Jugador)
        .join(Jugador.inscripcion)
        .filter(
            Jugador.discord_id == usuario.discord_id,
            Jugador.es_capitan.is_(True),
            Jugador.inscripcion.has(equipo_id=equipo_id),
        )
        .first()
    )
    if not es_capitan:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Esta acción solo la puede hacer el capitán del equipo. Si sos el "
            "capitán y ves este error, pedile al organizador que vincule tu "
            "cuenta de Discord con tu inscripción.",
        )


def _verificar_pertenece_al_equipo(db: Session, usuario: Usuario, equipo_id: int) -> None:
    """Versión más laxa: cualquier jugador del equipo (no solo el capitán)
    puede reportar un problema — no hace falta ser capitán para avisar que
    el rival no apareció."""
    if usuario.es_organizador:
        return

    pertenece = (
        db.query(Jugador)
        .join(Jugador.inscripcion)
        .filter(
            Jugador.discord_id == usuario.discord_id,
            Jugador.inscripcion.has(equipo_id=equipo_id),
        )
        .first()
    )
    if not pertenece:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Esta acción solo la puede hacer un jugador de ese equipo.",
        )


def _verificar_participa_en_partida(db: Session, usuario: Usuario, partida: Partida) -> None:
    """Para el chat: cualquier jugador de CUALQUIERA de los dos equipos de
    la partida puede leer/escribir — no hace falta ser capitán, esto es
    coordinación informal entre los planteles, no una acción con
    consecuencias en el resultado."""
    if usuario.es_organizador:
        return

    equipos_partida = [p.equipo_id for p in partida.participaciones]
    pertenece = (
        db.query(Jugador)
        .join(Jugador.inscripcion)
        .filter(
            Jugador.discord_id == usuario.discord_id,
            Jugador.inscripcion.has(Inscripcion.equipo_id.in_(equipos_partida)),
        )
        .first()
    )
    if not pertenece:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Esta partida no es tuya — no podés ver ni escribir en este chat."
        )


@router.post("", response_model=PartidaRead, status_code=status.HTTP_201_CREATED)
def crear_partida(
    fase_id: int, datos: PartidaCreate, db: DbSession, _staff: RequiereStaffDeFase
) -> Partida:
    """Alta manual de una partida.

    Provisorio: hasta que exista el generador de llaves, el organizador arma
    los cruces a mano. La cantidad de equipos se valida contra el modelo de
    competencia de la fase — nunca se asume 2v2 ni ningún otro número fijo.
    """
    fase = _obtener_fase(db, fase_id)

    if fase.modelo_competencia == ModeloCompetencia.ENFRENTAMIENTO_DIRECTO:
        if len(datos.equipo_ids) != 2:
            raise HTTPException(
                422, "Un enfrentamiento directo necesita exactamente 2 equipos."
            )
    else:
        if len(datos.equipo_ids) < 2:
            raise HTTPException(
                422, "Una partida multi-equipo necesita al menos 2 escuadras."
            )

    if len(set(datos.equipo_ids)) != len(datos.equipo_ids):
        raise HTTPException(422, "Un equipo no puede repetirse en la misma partida.")

    for eid in datos.equipo_ids:
        if not db.get(Equipo, eid):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"El equipo {eid} no existe.")

    partida = Partida(
        fase_id=fase_id,
        numero_caida=datos.numero_caida,
        programada_para=datos.programada_para,
    )
    db.add(partida)
    db.flush()

    for eid in datos.equipo_ids:
        db.add(ParticipacionEnPartida(partida_id=partida.id, equipo_id=eid))

    db.commit()
    db.refresh(partida)
    return partida


@router.get("", response_model=list[PartidaRead])
def listar_partidas_de_fase(
    fase_id: int,
    db: DbSession,
    background_tasks: BackgroundTasks,
    estado: EstadoPartida | None = None,
    resueltas: bool | None = None,
) -> list[Partida]:
    """El bracket completo: todas las partidas de la fase, con su lado
    (alta/baja/única) y ronda, listas para que el frontend arme el árbol.

    `estado` filtra por un estado puntual. `resueltas=true` es el atajo
    para la pestaña 'Resultados' (confirmada o walkover);
    `resueltas=false` es 'A continuación' (todo lo que todavía no cerró).
    """
    _obtener_fase(db, fase_id)
    _auto_abrir_checkins_vencidos(
        db,
        db.query(Partida).filter(Partida.fase_id == fase_id, Partida.estado == EstadoPartida.PROGRAMADA).all(),
        background_tasks,
    )
    _auto_resolver_reportes_vencidos(
        db, db.query(Partida).filter(Partida.fase_id == fase_id, Partida.estado == EstadoPartida.REPORTADA).all()
    )

    q = db.query(Partida).filter(Partida.fase_id == fase_id)

    if estado:
        q = q.filter(Partida.estado == estado)
    elif resueltas is True:
        q = q.filter(Partida.estado.in_([EstadoPartida.CONFIRMADA, EstadoPartida.WALKOVER]))
    elif resueltas is False:
        q = q.filter(
            Partida.estado.in_(
                [EstadoPartida.PROGRAMADA, EstadoPartida.CHECK_IN, EstadoPartida.EN_CURSO]
            )
        )

    return q.order_by(Partida.lado, Partida.ronda, Partida.id).all()


@router.get("/{partida_id}", response_model=PartidaRead)
def obtener_partida(
    fase_id: int, partida_id: int, db: DbSession, background_tasks: BackgroundTasks
) -> Partida:
    partida = _obtener_partida(db, fase_id, partida_id)
    _auto_abrir_checkins_vencidos(db, [partida], background_tasks)
    _auto_resolver_reportes_vencidos(db, [partida])
    return partida


@router.patch("/{partida_id}/programar", response_model=PartidaRead)
def programar_partida(
    fase_id: int, partida_id: int, datos: ProgramarPartidaIn, db: DbSession,
    background_tasks: BackgroundTasks, _staff: RequiereStaffDeFase,
) -> Partida:
    """Fija el horario de una partida — el check-in se abre solo
    `CHECKIN_MINUTOS_ANTES` antes de esa hora, sin que haga falta abrirlo
    a mano (ver `_auto_abrir_checkins_vencidos`). Se puede reprogramar
    mientras la partida siga en 'programada'.
    """
    partida = _obtener_partida(db, fase_id, partida_id)
    if partida.estado != EstadoPartida.PROGRAMADA:
        raise HTTPException(
            422, f"Solo se puede programar una partida en 'programada' (estado actual: {partida.estado})."
        )
    partida.programada_para = datos.programada_para

    fase = db.get(Fase, partida.fase_id)
    cuando = datos.programada_para.astimezone(ZoneInfo(fase.edicion.zona_horaria))
    _notificar_partida(
        db, background_tasks, partida,
        tipo="partida_programada",
        titulo_plantilla="Horario confirmado: {partida}",
        cuerpo=(
            f"Se juega el {cuando:%d/%m a las %H:%M} ({fase.edicion.zona_horaria}). "
            f"El check-in se abre {CHECKIN_MINUTOS_ANTES} minutos antes."
        ),
    )

    db.commit()
    db.refresh(partida)
    _publicar_cambio(db, partida, "partida_programada")
    return partida


@router.get("/{partida_id}/mensajes", response_model=list[MensajePartidaRead])
def listar_mensajes(fase_id: int, partida_id: int, db: DbSession, usuario: CurrentUser) -> list[MensajePartida]:
    """Chat de coordinación de esta partida puntual. Se pensó para
    refrescarse con polling (pedir esto cada pocos segundos mientras el
    modal está abierto), no hay WebSocket — para coordinar un horario de
    partida un par de segundos de demora no los nota nadie."""
    partida = _obtener_partida(db, fase_id, partida_id)
    _verificar_participa_en_partida(db, usuario, partida)
    return (
        db.query(MensajePartida)
        .filter(MensajePartida.partida_id == partida_id)
        .order_by(MensajePartida.created_at)
        .all()
    )


@router.post("/{partida_id}/mensajes", response_model=MensajePartidaRead, status_code=status.HTTP_201_CREATED)
def enviar_mensaje(
    fase_id: int, partida_id: int, datos: MensajePartidaIn, db: DbSession, usuario: CurrentUser
) -> MensajePartida:
    partida = _obtener_partida(db, fase_id, partida_id)
    equipos_partida = [p.equipo_id for p in partida.participaciones]

    if datos.equipo_id is not None:
        if datos.equipo_id not in equipos_partida:
            raise HTTPException(422, "Ese equipo no participa en esta partida.")
        _verificar_pertenece_al_equipo(db, usuario, datos.equipo_id)
        equipo = db.get(Equipo, datos.equipo_id)
        autor_nombre = equipo.nombre if equipo else "Equipo"
    else:
        if not usuario.es_organizador:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Sin equipo_id, este mensaje solo lo puede mandar el organizador."
            )
        autor_nombre = "Organizador"

    mensaje = MensajePartida(
        partida_id=partida_id,
        equipo_id=datos.equipo_id,
        autor_nombre=autor_nombre,
        texto=datos.texto.strip(),
    )
    db.add(mensaje)
    db.commit()
    db.refresh(mensaje)

    PUBLICADOR.publicar(
        topico_chat(partida_id),
        "mensaje_nuevo",
        {
            "id": mensaje.id,
            "partida_id": partida_id,
            "equipo_id": mensaje.equipo_id,
            "autor_nombre": mensaje.autor_nombre,
            "texto": mensaje.texto,
            "created_at": mensaje.created_at,
        },
    )
    return mensaje


@router.post("/{partida_id}/abrir-checkin", response_model=PartidaRead)
def abrir_checkin(
    fase_id: int, partida_id: int, datos: AbrirCheckinIn, db: DbSession,
    background_tasks: BackgroundTasks, _staff: RequiereStaffDeFase,
) -> Partida:
    """El organizador abre la ventana de check-in de una partida programada."""
    partida = _obtener_partida(db, fase_id, partida_id)

    if partida.estado != EstadoPartida.PROGRAMADA:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Solo se puede abrir check-in desde 'programada' "
            f"(estado actual: {partida.estado}).",
        )

    ahora = _ahora()
    partida.estado = EstadoPartida.CHECK_IN
    partida.checkin_abre_at = ahora
    partida.checkin_cierra_at = ahora + timedelta(minutes=datos.minutos)

    _notificar_partida(
        db, background_tasks, partida,
        tipo="checkin_abierto",
        titulo_plantilla="Check-in abierto: {partida}",
        cuerpo=(
            f"Confirmá tu presencia dentro de los próximos {datos.minutos} minutos. "
            "Si no hacés check-in a tiempo, la partida se pierde por walkover."
        ),
    )

    db.commit()
    db.refresh(partida)
    _publicar_cambio(db, partida, "checkin_abierto")
    return partida


@router.post("/{partida_id}/checkin", response_model=PartidaRead)
def confirmar_checkin(
    fase_id: int, partida_id: int, datos: ConfirmarCheckinIn, db: DbSession, usuario: CurrentUser
) -> Partida:
    """Un jugador del equipo confirma que está presente y listo.

    Cuando confirman todos los participantes, la partida pasa a 'en_curso'
    automáticamente — no hace falta que el organizador intervenga.
    """
    _verificar_pertenece_al_equipo(db, usuario, datos.equipo_id)
    partida = _obtener_partida(db, fase_id, partida_id)

    if partida.estado != EstadoPartida.CHECK_IN:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"El check-in no está abierto (estado: {partida.estado}).",
        )

    if partida.checkin_cierra_at and _ahora() > partida.checkin_cierra_at:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "La ventana de check-in ya venció. Pedile al organizador que resuelva.",
        )

    participacion = next(
        (p for p in partida.participaciones if p.equipo_id == datos.equipo_id), None
    )
    if not participacion:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Ese equipo no participa en esta partida."
        )

    if participacion.checkin_at:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este equipo ya confirmó su check-in.")

    participacion.checkin_at = _ahora()
    db.flush()

    if all(p.checkin_at is not None for p in partida.participaciones):
        partida.estado = EstadoPartida.EN_CURSO

    db.commit()
    db.refresh(partida)
    _publicar_cambio(db, partida, "checkin_confirmado")
    return partida


@router.post("/{partida_id}/resolver-checkin", response_model=PartidaRead)
def resolver_checkin(
    fase_id: int, partida_id: int, db: DbSession, _staff: RequiereStaffDeFase
) -> Partida:
    """Cierra una ventana de check-in vencida y aplica walkover si corresponde.

    Lo dispara el organizador por ahora. El candidato natural para
    automatizar esto más adelante es un cron, no un cliente humano — pero
    la regla vive acá, no en el scheduler que la vaya a llamar.
    """
    partida = _obtener_partida(db, fase_id, partida_id)

    if partida.estado != EstadoPartida.CHECK_IN:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"La partida no está en check-in (estado: {partida.estado}).",
        )

    confirmaciones = {p.equipo_id: p.checkin_at for p in partida.participaciones}
    evaluacion = evaluar_checkin(confirmaciones, partida.checkin_cierra_at, _ahora())

    if evaluacion.resultado == ResultadoCheckin.EN_ESPERA:
        raise HTTPException(status.HTTP_409_CONFLICT, "La ventana de check-in todavía no venció.")

    if evaluacion.resultado == ResultadoCheckin.TODOS_LISTOS:
        partida.estado = EstadoPartida.EN_CURSO

    elif evaluacion.resultado == ResultadoCheckin.NADIE_CONFIRMO:
        # No hay ganador que declarar si nadie apareció: vuelve a programada
        # para que el organizador la reprograme.
        partida.estado = EstadoPartida.PROGRAMADA
        partida.checkin_abre_at = None
        partida.checkin_cierra_at = None

    elif evaluacion.resultado == ResultadoCheckin.WALKOVER:
        partida.estado = EstadoPartida.WALKOVER
        if evaluacion.equipo_ganador_id:
            for p in partida.participaciones:
                p.es_ganador = p.equipo_id == evaluacion.equipo_ganador_id

    db.commit()
    db.refresh(partida)

    if evaluacion.resultado == ResultadoCheckin.WALKOVER and evaluacion.equipo_ganador_id:
        sorteo.avanzar_ganador(db, partida)
        db.refresh(partida)

    _publicar_cambio(db, partida, "checkin_resuelto")
    return partida


def _bo_de_la_fase(db: Session, fase_id: int, ronda: int | None = None) -> int:
    fase = db.get(Fase, fase_id)
    return bo_para_ronda(fase.config, ronda)


def _reporte_pendiente(db: Session, partida_id: int) -> ReporteResultado | None:
    return (
        db.query(ReporteResultado)
        .filter(ReporteResultado.partida_id == partida_id, ReporteResultado.estado == "pendiente")
        .order_by(ReporteResultado.created_at.desc())
        .first()
    )


def _aplicar_marcador(
    partida: Partida, equipo_reportante_id: int, marcador_propio: int, marcador_rival: int
) -> None:
    """Escribe el marcador confirmado en las participaciones. No decide
    reglas de negocio (eso ya se validó antes con `validar_marcador`), solo
    persiste."""
    for p in partida.participaciones:
        if p.equipo_id == equipo_reportante_id:
            p.mapas_ganados = marcador_propio
            p.es_ganador = marcador_propio > marcador_rival
        else:
            p.mapas_ganados = marcador_rival
            p.es_ganador = marcador_rival > marcador_propio


@router.post("/{partida_id}/reportar", response_model=ReporteResultadoRead)
def reportar_resultado(
    fase_id: int, partida_id: int, datos: ReportarResultadoIn, db: DbSession, usuario: CurrentUser
) -> ReporteResultado:
    """Un capitán reporta cómo terminó la partida. Queda pendiente hasta que
    el rival confirme o impugne — nunca se aplica de una."""
    partida = _obtener_partida(db, fase_id, partida_id)

    fase = _obtener_fase(db, fase_id)
    if fase.edicion.solo_organizador_reporta and not usuario.es_organizador:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "En este torneo los resultados los carga el organizador.",
        )
    _verificar_capitan_del_equipo(db, usuario, datos.equipo_id)

    if partida.estado != EstadoPartida.EN_CURSO:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Solo se puede reportar desde 'en_curso' (estado actual: {partida.estado}). "
            "Si la partida no llegó a jugarse, usá 'reportar-problema' en vez de esto.",
        )

    if not any(p.equipo_id == datos.equipo_id for p in partida.participaciones):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese equipo no participa en esta partida.")

    bo = _bo_de_la_fase(db, fase_id, ronda=partida.ronda)
    try:
        validar_marcador(bo, datos.marcador_propio, datos.marcador_rival)
    except ErrorPartida as e:
        raise HTTPException(422, str(e)) from e

    reporte = ReporteResultado(
        partida_id=partida.id,
        equipo_reportante_id=datos.equipo_id,
        marcador_propio=datos.marcador_propio,
        marcador_rival=datos.marcador_rival,
        evidencia_url=datos.evidencia_url,
        vencimiento=_ahora() + timedelta(hours=datos.horas_para_confirmar),
    )
    partida.estado = EstadoPartida.REPORTADA
    db.add(reporte)
    db.commit()
    db.refresh(reporte)
    db.refresh(partida)
    _publicar_cambio(db, partida, "resultado_reportado")
    return reporte


@router.post("/{partida_id}/confirmar", response_model=PartidaRead)
def confirmar_resultado(
    fase_id: int, partida_id: int, datos: ConfirmarResultadoIn, db: DbSession, usuario: CurrentUser
) -> Partida:
    """El rival confirma el marcador que reportó el otro capitán. Con esto
    la partida queda cerrada y la llave avanza sola."""
    _verificar_capitan_del_equipo(db, usuario, datos.equipo_id)
    partida = _obtener_partida(db, fase_id, partida_id)

    if partida.estado != EstadoPartida.REPORTADA:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"No hay nada que confirmar (estado: {partida.estado}).",
        )

    reporte = _reporte_pendiente(db, partida_id)
    if not reporte:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay un reporte pendiente.")

    if datos.equipo_id == reporte.equipo_reportante_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Quien reportó no puede confirmar su propio reporte — tiene que ser el rival.",
        )
    if not any(p.equipo_id == datos.equipo_id for p in partida.participaciones):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese equipo no participa en esta partida.")

    _aplicar_marcador(partida, reporte.equipo_reportante_id, reporte.marcador_propio, reporte.marcador_rival)
    partida.estado = EstadoPartida.CONFIRMADA
    partida.confirmada_at = _ahora()
    reporte.estado = "confirmado"
    reporte.confirmado_por_equipo_id = datos.equipo_id
    reporte.confirmado_at = _ahora()

    db.commit()
    db.refresh(partida)
    sorteo.avanzar_ganador(db, partida)
    db.refresh(partida)
    _publicar_cambio(db, partida, "resultado_confirmado")
    return partida


@router.post("/{partida_id}/impugnar", response_model=DisputaRead)
def impugnar_resultado(
    fase_id: int, partida_id: int, datos: ImpugnarResultadoIn, db: DbSession, usuario: CurrentUser
) -> Disputa:
    """El rival no está de acuerdo con lo reportado. Abre una disputa igual
    que 'reportar-problema' — cae en la misma bandeja del organizador."""
    _verificar_capitan_del_equipo(db, usuario, datos.equipo_id)
    partida = _obtener_partida(db, fase_id, partida_id)

    if partida.estado != EstadoPartida.REPORTADA:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"No hay nada que impugnar (estado: {partida.estado})."
        )

    reporte = _reporte_pendiente(db, partida_id)
    if not reporte:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay un reporte pendiente.")
    if datos.equipo_id == reporte.equipo_reportante_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Quien reportó no puede impugnar su propio reporte."
        )

    reporte.estado = "impugnado"
    disputa = Disputa(
        partida_id=partida.id,
        abierta_por_equipo_id=datos.equipo_id,
        motivo=f"Resultado reportado impugnado: {datos.motivo}",
    )
    partida.estado = EstadoPartida.EN_DISPUTA
    db.add(disputa)
    db.commit()
    db.refresh(disputa)
    db.refresh(partida)
    _publicar_cambio(db, partida, "resultado_impugnado")
    return disputa


@router.post("/{partida_id}/resolver-reporte-vencido", response_model=PartidaRead)
def resolver_reporte_vencido(
    fase_id: int, partida_id: int, db: DbSession, _staff: RequiereStaffDeFase
) -> Partida:
    """Auto-confirmación: si venció el plazo y el rival no reaccionó (ni
    confirmó ni impugnó), el reporte se da por bueno — pero solo si tiene
    evidencia. Sin evidencia, esto queda trabado a propósito hasta que el
    organizador lo resuelva a mano vía disputa.
    """
    partida = _obtener_partida(db, fase_id, partida_id)

    if partida.estado != EstadoPartida.REPORTADA:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"No hay nada pendiente (estado: {partida.estado})."
        )

    reporte = _reporte_pendiente(db, partida_id)
    if not reporte:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay un reporte pendiente.")

    if not reporte.evidencia_url:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Este reporte no tiene evidencia adjunta: no se puede auto-confirmar. "
            "Hace falta que el rival confirme explícitamente, o resolverlo como disputa.",
        )
    if reporte.vencimiento and _ahora() < reporte.vencimiento:
        raise HTTPException(status.HTTP_409_CONFLICT, "El plazo para confirmar todavía no venció.")

    _aplicar_marcador(partida, reporte.equipo_reportante_id, reporte.marcador_propio, reporte.marcador_rival)
    partida.estado = EstadoPartida.CONFIRMADA
    partida.confirmada_at = _ahora()
    reporte.estado = "confirmado"
    reporte.confirmado_at = _ahora()  # confirmado_por queda None: fue automático

    db.commit()
    db.refresh(partida)
    sorteo.avanzar_ganador(db, partida)
    db.refresh(partida)
    _publicar_cambio(db, partida, "resultado_confirmado")
    return partida


@router.post("/{partida_id}/corregir-resultado", response_model=CorreccionAplicadaOut)
def corregir_resultado(
    fase_id: int, partida_id: int, datos: CorregirResultadoIn, db: DbSession, usuario: RequiereStaffDeFase
) -> CorreccionAplicadaOut:
    """Corrige el marcador de una partida YA `confirmada`, sin que nadie la
    haya impugnado — el organizador nota un error días después.

    Distinto del camino de disputa (`resolver_disputa` con acción
    `confirmar_resultado`), que resuelve una partida `en_disputa` activa.
    Este endpoint es para el caso "nadie reclamó nada, pero está mal".

    Nunca sobrescribe el registro anterior — crea un `ReporteResultado`
    nuevo marcado `es_correccion=True` con el motivo, y deja el rastro
    completo consultable en `GET .../historial-resultado`.

    Si el marcador corregido cambia QUIÉN GANÓ y esta partida ya había
    avanzado su ganador a la siguiente ronda, la corrección se aplica igual
    acá, pero la respuesta trae una advertencia explícita — no se deshace
    el avance en cascada solo, eso lo revisa el organizador a mano.
    """
    partida = _obtener_partida(db, fase_id, partida_id)

    if partida.estado != EstadoPartida.CONFIRMADA:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Solo se puede corregir una partida 'confirmada' (estado actual: "
            f"{partida.estado}). Si está en disputa, usá "
            "/disputas/{id}/resolver con accion='confirmar_resultado'.",
        )

    ids_partida = {p.equipo_id for p in partida.participaciones}
    ids_dados = {r.equipo_id for r in datos.resultados}
    if ids_dados != ids_partida:
        raise HTTPException(422, "Los equipos del resultado no coinciden con los de la partida.")

    marcadores_nuevos = {r.equipo_id: r.mapas_ganados for r in datos.resultados}
    valores = list(marcadores_nuevos.values())
    if valores[0] == valores[1]:
        raise HTTPException(422, "El resultado no puede terminar en empate.")

    ganador_anterior_id = next(
        (p.equipo_id for p in partida.participaciones if p.es_ganador), None
    )
    ganador_nuevo_id = max(marcadores_nuevos, key=marcadores_nuevos.get)
    cambio_el_ganador = ganador_anterior_id != ganador_nuevo_id

    advertencia = None
    if cambio_el_ganador and partida.siguiente_partida_ganador_id:
        siguiente = db.get(Partida, partida.siguiente_partida_ganador_id)
        ya_propago = any(
            p.equipo_id == ganador_anterior_id for p in siguiente.participaciones
        )
        if ya_propago:
            advertencia = (
                f"El ganador cambió y ya había avanzado a la partida "
                f"#{siguiente.id}. Esa partida sigue teniendo al equipo "
                f"{ganador_anterior_id} cargado — revisala a mano, esto no "
                f"se corrige solo en cascada."
            )

    # Guardamos como equipo_reportante_id al que ahora gana, solo para que
    # _aplicar_marcador tenga un punto de referencia — el campo real de
    # autoría de esta corrección es aplicado_por_usuario_id, no este.
    for p in partida.participaciones:
        p.mapas_ganados = marcadores_nuevos[p.equipo_id]
        p.es_ganador = p.equipo_id == ganador_nuevo_id

    reporte = ReporteResultado(
        partida_id=partida.id,
        equipo_reportante_id=None,
        marcador_propio=marcadores_nuevos[ganador_nuevo_id],
        marcador_rival=min(valores),
        estado="corregido",
        es_correccion=True,
        motivo=datos.motivo,
        aplicado_por_usuario_id=usuario.id,
    )
    db.add(reporte)
    db.commit()
    db.refresh(partida)
    db.refresh(reporte)

    if cambio_el_ganador and not advertencia:
        # Cambió el ganador pero todavía no se había propagado nada (por
        # ejemplo la fase recién se sorteó y esta era la única partida
        # jugada) — no hace falta advertir, avanzar_ganador de acá para
        # abajo va a colocar al equipo correcto sin pisar nada.
        sorteo.avanzar_ganador(db, partida)
        db.refresh(partida)

    _publicar_cambio(db, partida, "resultado_corregido")
    return CorreccionAplicadaOut(
        partida=partida,
        reporte=reporte,
        advertencia=advertencia,
    )


@router.get("/{partida_id}/historial-resultado", response_model=list[ReporteResultadoRead])
def historial_resultado(fase_id: int, partida_id: int, db: DbSession) -> list[ReporteResultado]:
    """Todos los reportes y correcciones de una partida, en orden — la
    trazabilidad completa de 'qué se sabía en cada momento'."""
    _obtener_partida(db, fase_id, partida_id)
    return (
        db.query(ReporteResultado)
        .filter(ReporteResultado.partida_id == partida_id)
        .order_by(ReporteResultado.created_at)
        .all()
    )


@router.post("/{partida_id}/reportar-problema", response_model=DisputaRead)
def reportar_problema(
    fase_id: int, partida_id: int, datos: ReportarProblemaIn, db: DbSession, usuario: CurrentUser
) -> Disputa:
    """Escalamiento directo al organizador — separado del reporte normal de
    resultado. Para: el rival no aparece, hay lag, sospecha de trampa.
    """
    _verificar_pertenece_al_equipo(db, usuario, datos.equipo_id)
    partida = _obtener_partida(db, fase_id, partida_id)

    if partida.estado in (EstadoPartida.CONFIRMADA, EstadoPartida.BYE):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"No se puede reportar un problema en una partida {partida.estado}.",
        )

    if not any(p.equipo_id == datos.equipo_id for p in partida.participaciones):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Ese equipo no participa en esta partida."
        )

    disputa = Disputa(
        partida_id=partida.id,
        abierta_por_equipo_id=datos.equipo_id,
        motivo=datos.motivo,
        evidencia_url=datos.evidencia_url,
    )
    partida.estado = EstadoPartida.EN_DISPUTA
    db.add(disputa)
    db.commit()
    db.refresh(disputa)
    db.refresh(partida)
    _publicar_cambio(db, partida, "problema_reportado")
    return disputa


@router.get("/{partida_id}/disputas", response_model=list[DisputaRead])
def listar_disputas_de_partida(
    fase_id: int, partida_id: int, db: DbSession
) -> list[Disputa]:
    partida = _obtener_partida(db, fase_id, partida_id)
    return partida.disputas


@router_disputas.get("", response_model=list[DisputaRead])
def listar_disputas(
    db: DbSession, _organizador: RequiereOrganizador, estado: str | None = None
) -> list[Disputa]:
    """Bandeja del organizador: todas las disputas abiertas, de cualquier fase."""
    q = db.query(Disputa)
    if estado:
        q = q.filter(Disputa.estado == estado)
    return q.order_by(Disputa.created_at).all()


@router_disputas.post("/{disputa_id}/resolver", response_model=DisputaRead)
def resolver_disputa(
    disputa_id: int, datos: ResolverDisputaIn, db: DbSession, _staff: RequiereStaffDeDisputa
) -> Disputa:
    """El organizador o el staff del torneo de esta disputa deciden. Tres
    acciones:

    - 'reprogramar': la partida vuelve a 'programada', se juega de nuevo.
    - 'walkover': se declara ganador directo sin jugar.
    - 'confirmar_resultado': se carga el marcador que corresponde.

    Alcanza con ser árbitro — resolver una disputa es trabajo de día de
    partido, igual que programar o corregir un resultado. Hasta que
    existió `RequiereStaffDeDisputa`, esta ruta se había quedado en
    organizador global porque no tiene `fase_id` en la URL para resolver
    el torneo con un simple `get()`; un árbitro igual podía dejar la
    partida resuelta desde `/corregir-resultado`, pero la `Disputa` en sí
    seguía 'abierta' hasta que pasara un organizador.
    """
    disputa = db.get(Disputa, disputa_id)
    if not disputa:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La disputa no existe.")
    if disputa.estado == "resuelta":
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta disputa ya fue resuelta.")

    partida = disputa.partida

    if datos.accion == "reprogramar":
        partida.estado = EstadoPartida.PROGRAMADA
        partida.checkin_abre_at = None
        partida.checkin_cierra_at = None
        for p in partida.participaciones:
            p.checkin_at = None
            p.es_ganador = None

    elif datos.accion == "walkover":
        if not datos.equipo_ganador_id:
            raise HTTPException(422, "Un walkover necesita indicar el equipo ganador.")
        if not any(
            p.equipo_id == datos.equipo_ganador_id for p in partida.participaciones
        ):
            raise HTTPException(422, "Ese equipo no participa en la partida.")
        partida.estado = EstadoPartida.WALKOVER
        for p in partida.participaciones:
            p.es_ganador = p.equipo_id == datos.equipo_ganador_id

    elif datos.accion == "confirmar_resultado":
        # El organizador zanja una impugnación cargando el marcador que
        # corresponde, en vez de forzar un walkover sin haberse jugado.
        if not datos.resultados or len(datos.resultados) != 2:
            raise HTTPException(422, "Hacen falta los resultados de los 2 equipos.")

        ids_partida = {p.equipo_id for p in partida.participaciones}
        ids_dados = {r.equipo_id for r in datos.resultados}
        if ids_dados != ids_partida:
            raise HTTPException(
                422, "Los equipos del resultado no coinciden con los de la partida."
            )

        marcadores = {r.equipo_id: r.mapas_ganados for r in datos.resultados}
        valores = list(marcadores.values())
        if valores[0] == valores[1]:
            raise HTTPException(422, "El resultado no puede terminar en empate.")

        ganador_id = max(marcadores, key=marcadores.get)
        for p in partida.participaciones:
            p.mapas_ganados = marcadores[p.equipo_id]
            p.es_ganador = p.equipo_id == ganador_id
        partida.estado = EstadoPartida.CONFIRMADA
        partida.confirmada_at = _ahora()

        reporte_pendiente = _reporte_pendiente(db, partida.id)
        if reporte_pendiente:
            reporte_pendiente.estado = "resuelto_por_organizador"
        else:
            impugnado = (
                db.query(ReporteResultado)
                .filter(ReporteResultado.partida_id == partida.id, ReporteResultado.estado == "impugnado")
                .order_by(ReporteResultado.created_at.desc())
                .first()
            )
            if impugnado:
                impugnado.estado = "resuelto_por_organizador"

    else:
        raise HTTPException(422, "Acción inválida: usar 'reprogramar', 'walkover' o 'confirmar_resultado'.")

    disputa.estado = "resuelta"
    disputa.resolucion = datos.resolucion
    disputa.resuelta_at = _ahora()

    db.commit()
    db.refresh(disputa)

    if datos.accion in ("walkover", "confirmar_resultado"):
        db.refresh(partida)
        sorteo.avanzar_ganador(db, partida)

    db.refresh(partida)
    _publicar_cambio(db, partida, "disputa_resuelta")
    return disputa
