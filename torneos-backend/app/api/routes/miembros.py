"""Roster permanente de un equipo: quién lo integra entre torneos, y cómo
se entra.

El cambio de fondo que trae este módulo es que un miembro de equipo es una
persona con cuenta, no un texto que tipeó el capitán. Antes el capitán
cargaba a los cinco a mano, y salirse del equipo dependía de que él quisiera
sacarte; ahora cada uno entra aceptando una invitación y es dueño de su
propia fila.

Eso convierte a la invitación en el único camino de entrada, y por eso vive
en la base (`InvitacionAEquipo`) y no en memoria como los tickets de stream:
tiene que seguir viva si el jugador abre el link mañana.
"""

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.domain.roster import ConfigJuego, ErrorRoster, validar_identidad
from app.models import Equipo, InvitacionAEquipo, Juego, MiembroEquipo, Usuario
from app.schemas.miembros import (
    AceptarInvitacion,
    InvitacionCreada,
    InvitacionCrear,
    InvitacionOut,
    InvitacionPreview,
    MiembroOut,
)

router_equipos = APIRouter(prefix="/equipos/{equipo_id}", tags=["miembros"])
router_invitaciones = APIRouter(prefix="/invitaciones", tags=["miembros"])


def _ahora() -> datetime:
    return datetime.now().astimezone()


def _equipo_administrable(db: DbSession, equipo_id: int, usuario: Usuario) -> Equipo:
    """El equipo, comprobando que quien llama pueda administrarlo.

    Mismo criterio que `editar_equipo` en perfiles.py: el dueño, o un
    organizador global. Repartir el roster es administrar el equipo.
    """
    equipo = db.get(Equipo, equipo_id)
    if not equipo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El equipo no existe.")
    if equipo.propietario_usuario_id != usuario.id and not usuario.es_organizador:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Este equipo no es tuyo.")
    return equipo


def _resolver_juego(db: DbSession, juego_id: int | None) -> Juego:
    """El juego del roster que se está tocando.

    El equipo no está atado a un juego —puede jugar varios— pero el roster
    sí: la identidad de MLBB (id + server) no es la de otro juego. Cuando
    hay un solo juego activo no tiene sentido hacérselo elegir a nadie, así
    que se asume; con más de uno hay que decirlo.
    """
    if juego_id is not None:
        juego = db.get(Juego, juego_id)
        if not juego:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese juego no existe.")
        return juego

    activos = db.query(Juego).filter(Juego.esta_activo).all()
    if len(activos) == 1:
        return activos[0]
    raise HTTPException(
        422,
        "Hay más de un juego activo: indicá para cuál es el roster con "
        "`juego_id`.",
    )


def _config(juego: Juego) -> ConfigJuego:
    return ConfigJuego(
        titulares_requeridos=juego.titulares_requeridos,
        suplentes_maximos=juego.suplentes_maximos,
        campos_requeridos=juego.campos_requeridos(),
        campos_clave=juego.campos_clave(),
    )


@router_equipos.get("/miembros", response_model=list[MiembroOut])
def listar_miembros(
    equipo_id: int, db: DbSession, usuario: CurrentUser, juego_id: int | None = None
) -> list[MiembroOut]:
    """El roster permanente del equipo.

    Pide ser el dueño porque acá van los datos de juego de cada persona. El
    perfil público del equipo es otra cosa y tiene su propia ruta.
    """
    _equipo_administrable(db, equipo_id, usuario)
    juego = _resolver_juego(db, juego_id)

    miembros = (
        db.query(MiembroEquipo)
        .filter(
            MiembroEquipo.equipo_id == equipo_id,
            MiembroEquipo.juego_id == juego.id,
            MiembroEquipo.esta_activo,
        )
        .order_by(MiembroEquipo.created_at)
        .all()
    )
    if not miembros:
        return []

    nombres = {
        u.id: u.discord_username
        for u in db.query(Usuario)
        .filter(Usuario.id.in_([m.usuario_id for m in miembros]))
        .all()
    }
    return [
        MiembroOut(
            id=m.id,
            identidad=m.identidad,
            usuario_id=m.usuario_id,
            esta_activo=m.esta_activo,
            created_at=m.created_at,
            usuario_nombre=nombres.get(m.usuario_id),
        )
        for m in miembros
    ]


@router_equipos.post(
    "/invitaciones",
    response_model=InvitacionCreada,
    status_code=status.HTTP_201_CREATED,
)
def crear_invitacion(
    equipo_id: int,
    datos: InvitacionCrear,
    db: DbSession,
    usuario: CurrentUser,
    juego_id: int | None = None,
) -> InvitacionCreada:
    """Genera una invitación para sumarse al roster.

    Sin `usuario_destino_id` es un link abierto, para mandar por WhatsApp o
    Discord: lo acepta el primero que lo abra teniendo cuenta. Con destino,
    solo esa persona puede aceptarla aunque el link se filtre.

    El token se devuelve acá y no vuelve a aparecer en ninguna respuesta.
    """
    _equipo_administrable(db, equipo_id, usuario)
    juego = _resolver_juego(db, juego_id)

    if datos.usuario_destino_id is not None:
        destino = db.get(Usuario, datos.usuario_destino_id)
        if not destino:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese usuario no existe.")
        ya_miembro = (
            db.query(MiembroEquipo)
            .filter(
                MiembroEquipo.equipo_id == equipo_id,
                MiembroEquipo.juego_id == juego.id,
                MiembroEquipo.usuario_id == destino.id,
                MiembroEquipo.esta_activo,
            )
            .first()
        )
        if ya_miembro:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Esa persona ya está en el equipo."
            )

    invitacion = InvitacionAEquipo(
        equipo_id=equipo_id,
        juego_id=juego.id,
        token=secrets.token_urlsafe(32),
        creada_por_usuario_id=usuario.id,
        usuario_destino_id=datos.usuario_destino_id,
        expira_at=_ahora() + timedelta(days=datos.dias_de_vida),
    )
    db.add(invitacion)
    db.commit()
    db.refresh(invitacion)
    return InvitacionCreada(
        id=invitacion.id,
        token=invitacion.token,
        expira_at=invitacion.expira_at,
        usuario_destino_id=invitacion.usuario_destino_id,
    )


@router_equipos.get("/invitaciones", response_model=list[InvitacionOut])
def listar_invitaciones(
    equipo_id: int, db: DbSession, usuario: CurrentUser
) -> list[InvitacionAEquipo]:
    """Las invitaciones del equipo, sin el token — ver el módulo."""
    _equipo_administrable(db, equipo_id, usuario)
    return (
        db.query(InvitacionAEquipo)
        .filter(InvitacionAEquipo.equipo_id == equipo_id)
        .order_by(InvitacionAEquipo.created_at.desc())
        .all()
    )


@router_equipos.delete("/invitaciones/{invitacion_id}", response_model=InvitacionOut)
def revocar_invitacion(
    equipo_id: int, invitacion_id: int, db: DbSession, usuario: CurrentUser
) -> InvitacionAEquipo:
    """Anula una invitación que todavía no se usó.

    Revocar una ya aceptada no haría nada útil: el jugador ya está en el
    equipo y lo que corresponde es sacarlo del roster, no borrarle el link.
    """
    _equipo_administrable(db, equipo_id, usuario)
    invitacion = db.get(InvitacionAEquipo, invitacion_id)
    if not invitacion or invitacion.equipo_id != equipo_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esa invitación no existe.")
    if invitacion.estado != "pendiente":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Esa invitación ya está '{invitacion.estado}'.",
        )
    invitacion.estado = "revocada"
    db.commit()
    db.refresh(invitacion)
    return invitacion


def _invitacion_utilizable(
    db: DbSession, token: str, usuario: Usuario
) -> InvitacionAEquipo:
    """La invitación del token, si quien la trae puede usarla.

    Todos los rechazos son 404 a propósito, incluido el de la invitación
    dirigida a otro. Distinguir "no existe" de "existe pero no es para vos"
    convertiría a la ruta en un oráculo para adivinar tokens ajenos.
    """
    invitacion = (
        db.query(InvitacionAEquipo).filter(InvitacionAEquipo.token == token).first()
    )
    if not invitacion:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esta invitación no sirve.")
    if invitacion.estado != "pendiente":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esta invitación no sirve.")
    if _ahora() > invitacion.expira_at:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esta invitación venció.")
    if (
        invitacion.usuario_destino_id is not None
        and invitacion.usuario_destino_id != usuario.id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esta invitación no sirve.")
    return invitacion


@router_invitaciones.get("/{token}", response_model=InvitacionPreview)
def ver_invitacion(token: str, db: DbSession, usuario: CurrentUser) -> InvitacionPreview:
    """Qué equipo te está invitando, antes de aceptar.

    Devuelve `campos_requeridos` porque el jugador carga su propia identidad
    de juego al aceptar y el formulario tiene que saber qué pedirle.
    """
    invitacion = _invitacion_utilizable(db, token, usuario)
    equipo = db.get(Equipo, invitacion.equipo_id)
    juego = db.get(Juego, invitacion.juego_id)
    return InvitacionPreview(
        equipo_id=equipo.id,
        equipo_nombre=equipo.nombre,
        juego_nombre=juego.nombre,
        campos_requeridos=juego.campos_requeridos(),
        expira_at=invitacion.expira_at,
        dirigida_a_vos=invitacion.usuario_destino_id is not None,
    )


@router_invitaciones.post(
    "/{token}/aceptar", response_model=MiembroOut, status_code=status.HTTP_201_CREATED
)
def aceptar_invitacion(
    token: str, datos: AceptarInvitacion, db: DbSession, usuario: CurrentUser
) -> MiembroOut:
    """El jugador entra al equipo cargando SUS datos de juego.

    Es el punto del rediseño: la identidad la escribe su dueño. El capitán
    no puede tipear a nadie, así que tampoco puede equivocarse con el ID de
    otro ni dejar a alguien adentro sin que se entere.
    """
    invitacion = _invitacion_utilizable(db, token, usuario)
    juego = db.get(Juego, invitacion.juego_id)

    try:
        clave = validar_identidad(datos.identidad, _config(juego))
    except ErrorRoster as e:
        raise HTTPException(422, str(e)) from e

    ya_miembro = (
        db.query(MiembroEquipo)
        .filter(
            MiembroEquipo.equipo_id == invitacion.equipo_id,
            MiembroEquipo.juego_id == juego.id,
            MiembroEquipo.usuario_id == usuario.id,
        )
        .first()
    )
    if ya_miembro:
        # Volver a entrar a un equipo del que te fuiste reutiliza la fila:
        # así el equipo no acumula filas muertas de la misma persona, y el
        # UNIQUE de (equipo, juego, usuario) sigue teniendo sentido.
        if ya_miembro.esta_activo:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Ya estás en este equipo."
            )
        ya_miembro.esta_activo = True
        ya_miembro.identidad = datos.identidad
        ya_miembro.clave_identidad = clave
        miembro = ya_miembro
    else:
        choque = (
            db.query(MiembroEquipo)
            .filter(
                MiembroEquipo.equipo_id == invitacion.equipo_id,
                MiembroEquipo.juego_id == juego.id,
                MiembroEquipo.clave_identidad == clave,
            )
            .first()
        )
        if choque:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Ya hay alguien en este equipo con esa identidad de juego.",
            )
        miembro = MiembroEquipo(
            equipo_id=invitacion.equipo_id,
            juego_id=juego.id,
            identidad=datos.identidad,
            clave_identidad=clave,
            usuario_id=usuario.id,
        )
        db.add(miembro)

    invitacion.estado = "aceptada"
    invitacion.aceptada_por_usuario_id = usuario.id
    invitacion.aceptada_at = _ahora()

    db.commit()
    db.refresh(miembro)
    return MiembroOut(
        id=miembro.id,
        identidad=miembro.identidad,
        usuario_id=miembro.usuario_id,
        esta_activo=miembro.esta_activo,
        created_at=miembro.created_at,
        usuario_nombre=usuario.discord_username,
    )
