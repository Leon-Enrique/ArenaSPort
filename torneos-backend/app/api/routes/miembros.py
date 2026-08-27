"""Roster permanente de un equipo, e identidad de juego de cada persona.

El cambio de fondo es dónde vive el ID de juego. Antes se tipeaba de nuevo en
cada inscripción y lo tipeaba el capitán, así que nadie era dueño de sus
propios datos y salirse de un equipo dependía de que el capitán quisiera
sacarte. Ahora el ID vive en la cuenta (`IdentidadDeJuego`), se carga una vez
y el roster del equipo guarda solo el vínculo.

La regla que ordena todo el módulo:

    **Entrar no requiere aceptar; salir no requiere permiso.**

El capitán suma gente directo, porque armar el equipo no puede depender de
que cinco personas contesten un mensaje. Al sumado le llega una notificación
que le dice quién lo agregó, y se va solo cuando quiera sin pedirle nada a
nadie. La fricción se saca de entrar —que es lo que frena al capitán— y no
de salir, que es lo que protege al jugador.
"""

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.core import notificaciones
from app.domain.roster import ConfigJuego, ErrorRoster, validar_identidad
from app.models import (
    Equipo,
    IdentidadDeJuego,
    InvitacionAEquipo,
    Juego,
    MiembroEquipo,
    Usuario,
)
from app.schemas.miembros import (
    AgregarMiembro,
    IdentidadDeJuegoOut,
    IdentidadEntrada,
    InvitacionCreada,
    InvitacionCrear,
    InvitacionOut,
    InvitacionPreview,
    MiembroOut,
)

router_equipos = APIRouter(prefix="/equipos/{equipo_id}", tags=["miembros"])
router_invitaciones = APIRouter(prefix="/invitaciones", tags=["miembros"])
router_identidades = APIRouter(prefix="/usuarios/me/identidades", tags=["miembros"])


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
    sí: la identidad de MLBB (id + server) no es la de otro juego. Con un
    solo juego activo no tiene sentido hacérselo elegir a nadie.
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
        422, "Hay más de un juego activo: indicá para cuál es el roster con `juego_id`."
    )


def _config(juego: Juego) -> ConfigJuego:
    return ConfigJuego(
        titulares_requeridos=juego.titulares_requeridos,
        suplentes_maximos=juego.suplentes_maximos,
        campos_requeridos=juego.campos_requeridos(),
        campos_clave=juego.campos_clave(),
    )


def _armar_miembro_out(
    miembro: MiembroEquipo, usuario: Usuario | None, identidad: IdentidadDeJuego | None
) -> MiembroOut:
    return MiembroOut(
        id=miembro.id,
        usuario_id=miembro.usuario_id,
        usuario_nombre=usuario.discord_username if usuario else None,
        identidad=identidad.identidad if identidad else None,
        esta_activo=miembro.esta_activo,
        created_at=miembro.created_at,
    )


# --------------------------------------------------------------------------
# Identidad de juego: la carga cada uno para sí mismo
# --------------------------------------------------------------------------


@router_identidades.get("", response_model=list[IdentidadDeJuegoOut])
def mis_identidades(db: DbSession, usuario: CurrentUser) -> list[IdentidadDeJuego]:
    """Los IDs de juego cargados por el usuario, uno por juego."""
    return (
        db.query(IdentidadDeJuego)
        .filter(IdentidadDeJuego.usuario_id == usuario.id)
        .all()
    )


@router_identidades.put("", response_model=IdentidadDeJuegoOut)
def guardar_mi_identidad(
    datos: IdentidadEntrada, db: DbSession, usuario: CurrentUser
) -> IdentidadDeJuego:
    """Carga o corrige el ID de juego propio.

    Solo para uno mismo, sin excepción para el organizador: el sentido de
    mover la identidad a la cuenta es que nadie la escriba por vos. Si hay
    que arreglar el dato de otro, lo arregla esa persona.

    Corregirlo se propaga solo a todos los equipos donde estés, porque el
    roster guarda el vínculo y no una copia del ID.
    """
    juego = _resolver_juego(db, datos.juego_id)
    try:
        clave = validar_identidad(datos.identidad, _config(juego))
    except ErrorRoster as e:
        raise HTTPException(422, str(e)) from e

    de_otro = (
        db.query(IdentidadDeJuego)
        .filter(
            IdentidadDeJuego.juego_id == juego.id,
            IdentidadDeJuego.clave_identidad == clave,
            IdentidadDeJuego.usuario_id != usuario.id,
        )
        .first()
    )
    if de_otro:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Otra cuenta ya declaró esa identidad de juego. Si es tuya y "
            "perdiste el acceso a esa cuenta, escribile al organizador.",
        )

    identidad = (
        db.query(IdentidadDeJuego)
        .filter(
            IdentidadDeJuego.usuario_id == usuario.id,
            IdentidadDeJuego.juego_id == juego.id,
        )
        .first()
    )
    if identidad:
        identidad.identidad = datos.identidad
        identidad.clave_identidad = clave
        identidad.actualizada_at = _ahora()
    else:
        identidad = IdentidadDeJuego(
            usuario_id=usuario.id,
            juego_id=juego.id,
            identidad=datos.identidad,
            clave_identidad=clave,
        )
        db.add(identidad)

    db.commit()
    db.refresh(identidad)
    return identidad


# --------------------------------------------------------------------------
# Roster permanente
# --------------------------------------------------------------------------


@router_equipos.get("/miembros", response_model=list[MiembroOut])
def listar_miembros(
    equipo_id: int, db: DbSession, usuario: CurrentUser, juego_id: int | None = None
) -> list[MiembroOut]:
    """El roster permanente del equipo.

    `identidad` puede venir en null: es alguien que fue sumado pero todavía
    no cargó su ID de juego. No es un error —el equipo se arma igual— pero
    es lo que después deja la inscripción en 'pendiente'.
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

    ids = [m.usuario_id for m in miembros]
    usuarios = {u.id: u for u in db.query(Usuario).filter(Usuario.id.in_(ids)).all()}
    identidades = {
        i.usuario_id: i
        for i in db.query(IdentidadDeJuego)
        .filter(
            IdentidadDeJuego.usuario_id.in_(ids),
            IdentidadDeJuego.juego_id == juego.id,
        )
        .all()
    }
    return [
        _armar_miembro_out(m, usuarios.get(m.usuario_id), identidades.get(m.usuario_id))
        for m in miembros
    ]


def _sumar_al_roster(
    db: DbSession,
    background_tasks: BackgroundTasks,
    equipo: Equipo,
    juego: Juego,
    nuevo: Usuario,
    agregado_por: Usuario | None,
) -> MiembroEquipo:
    """Deja a `nuevo` en el roster y le avisa.

    Compartido por el alta directa y por la aceptación de una invitación,
    para que entrar por un camino o por el otro deje exactamente el mismo
    estado. El aviso es lo que hace legítima el alta sin consentimiento:
    nadie puede quedar en un equipo sin enterarse.
    """
    miembro = (
        db.query(MiembroEquipo)
        .filter(
            MiembroEquipo.equipo_id == equipo.id,
            MiembroEquipo.juego_id == juego.id,
            MiembroEquipo.usuario_id == nuevo.id,
        )
        .first()
    )
    if miembro and miembro.esta_activo:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya está en el equipo.")

    if miembro:
        # Volver reutiliza la fila: el equipo no acumula filas muertas de la
        # misma persona y el UNIQUE por usuario sigue teniendo sentido.
        miembro.esta_activo = True
        miembro.salio_at = None
        miembro.agregado_por_usuario_id = agregado_por.id if agregado_por else None
    else:
        miembro = MiembroEquipo(
            equipo_id=equipo.id,
            juego_id=juego.id,
            usuario_id=nuevo.id,
            agregado_por_usuario_id=agregado_por.id if agregado_por else None,
        )
        db.add(miembro)

    quien = agregado_por.discord_username if agregado_por else "El equipo"
    notificaciones.notificar(
        db,
        background_tasks,
        tipo="agregado_a_equipo",
        usuarios=[nuevo],
        titulo=f"Te sumaron a {equipo.nombre}",
        cuerpo=(
            f"{quien} te agregó al equipo {equipo.nombre}. Si no querés estar, "
            "podés salirte vos mismo desde tu perfil."
        ),
        url=f"/equipos/{equipo.id}",
    )
    return miembro


@router_equipos.post(
    "/miembros", response_model=MiembroOut, status_code=status.HTTP_201_CREATED
)
def agregar_miembro(
    equipo_id: int,
    datos: AgregarMiembro,
    db: DbSession,
    usuario: CurrentUser,
    background_tasks: BackgroundTasks,
) -> MiembroOut:
    """El capitán suma a alguien al roster, sin que tenga que aceptar.

    No hace falta saber su ID de juego: se toma de su cuenta. Si todavía no
    lo cargó, entra igual y el roster queda incompleto hasta que lo haga —
    bloquear el alta haría que armar el equipo dependa de la velocidad de
    los demás, que es justo lo que se quiere evitar.

    Al sumado le llega una notificación diciendo quién lo agregó, y puede
    salirse solo. Ese es el contrapeso de no pedirle permiso.
    """
    equipo = _equipo_administrable(db, equipo_id, usuario)
    juego = _resolver_juego(db, datos.juego_id)

    nuevo = db.get(Usuario, datos.usuario_id)
    if not nuevo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese usuario no existe.")

    miembro = _sumar_al_roster(db, background_tasks, equipo, juego, nuevo, usuario)
    db.commit()
    db.refresh(miembro)

    identidad = (
        db.query(IdentidadDeJuego)
        .filter(
            IdentidadDeJuego.usuario_id == nuevo.id,
            IdentidadDeJuego.juego_id == juego.id,
        )
        .first()
    )
    return _armar_miembro_out(miembro, nuevo, identidad)


@router_equipos.delete("/miembros/{miembro_id}", response_model=MiembroOut)
def sacar_del_roster(
    equipo_id: int,
    miembro_id: int,
    db: DbSession,
    usuario: CurrentUser,
    background_tasks: BackgroundTasks,
) -> MiembroOut:
    """Salirse del equipo, o que el capitán te saque.

    Las dos cosas pasan por acá porque son la misma operación, y la
    diferencia está en quién puede: **el jugador siempre puede salirse de
    su propia fila**, sin permiso de nadie. Ese es el problema que este
    rediseño vino a resolver — antes había que convencer al capitán.

    El capitán también puede sacar a otro, y en ese caso le llega aviso. Al
    que se va por su cuenta no se le notifica nada: ya sabe.
    """
    miembro = db.get(MiembroEquipo, miembro_id)
    if not miembro or miembro.equipo_id != equipo_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ese miembro no existe.")

    equipo = db.get(Equipo, equipo_id)
    es_uno_mismo = miembro.usuario_id == usuario.id
    if not es_uno_mismo:
        _equipo_administrable(db, equipo_id, usuario)

    if not miembro.esta_activo:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Esa persona ya no está en el equipo."
        )

    miembro.esta_activo = False
    miembro.salio_at = _ahora()

    if not es_uno_mismo:
        sacado = db.get(Usuario, miembro.usuario_id)
        if sacado:
            notificaciones.notificar(
                db,
                background_tasks,
                tipo="sacado_de_equipo",
                usuarios=[sacado],
                titulo=f"Ya no estás en {equipo.nombre}",
                cuerpo=f"{usuario.discord_username} te sacó del equipo {equipo.nombre}.",
                url=f"/equipos/{equipo.id}",
            )

    db.commit()
    db.refresh(miembro)
    return _armar_miembro_out(miembro, db.get(Usuario, miembro.usuario_id), None)


# --------------------------------------------------------------------------
# Invitaciones: solo para el que todavía no tiene cuenta
# --------------------------------------------------------------------------


@router_equipos.post(
    "/invitaciones",
    response_model=InvitacionCreada,
    status_code=status.HTTP_201_CREATED,
)
def crear_invitacion(
    equipo_id: int, datos: InvitacionCrear, db: DbSession, usuario: CurrentUser
) -> InvitacionCreada:
    """Un link para sumarse al equipo.

    No es el camino normal: al que ya tiene cuenta se lo agrega directo con
    `POST /miembros`. Esto cubre al que todavía no se registró — abre el
    link, se crea la cuenta y queda adentro sin que el capitán tenga que
    volver a buscarlo.

    El token se devuelve acá y no vuelve a aparecer en ninguna respuesta.
    """
    _equipo_administrable(db, equipo_id, usuario)
    juego = _resolver_juego(db, datos.juego_id)

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
            status.HTTP_409_CONFLICT, f"Esa invitación ya está '{invitacion.estado}'."
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
    if not invitacion or invitacion.estado != "pendiente":
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
    """Qué equipo te está invitando, antes de entrar."""
    invitacion = _invitacion_utilizable(db, token, usuario)
    equipo = db.get(Equipo, invitacion.equipo_id)
    juego = db.get(Juego, invitacion.juego_id)
    ya_cargo = (
        db.query(IdentidadDeJuego)
        .filter(
            IdentidadDeJuego.usuario_id == usuario.id,
            IdentidadDeJuego.juego_id == juego.id,
        )
        .first()
    )
    return InvitacionPreview(
        equipo_id=equipo.id,
        equipo_nombre=equipo.nombre,
        juego_id=juego.id,
        juego_nombre=juego.nombre,
        campos_requeridos=juego.campos_requeridos(),
        expira_at=invitacion.expira_at,
        dirigida_a_vos=invitacion.usuario_destino_id is not None,
        ya_cargaste_tu_identidad=ya_cargo is not None,
    )


@router_invitaciones.post(
    "/{token}/aceptar", response_model=MiembroOut, status_code=status.HTTP_201_CREATED
)
def aceptar_invitacion(
    token: str, db: DbSession, usuario: CurrentUser, background_tasks: BackgroundTasks
) -> MiembroOut:
    """Entra al equipo usando el link.

    No pide la identidad de juego: si ya la cargaste se usa la de tu
    cuenta, y si no, entrás igual y la cargás cuando quieras por
    `/usuarios/me/identidades`. Es el mismo criterio que el alta directa —
    el roster se completa después, la pertenencia no espera.
    """
    invitacion = _invitacion_utilizable(db, token, usuario)
    equipo = db.get(Equipo, invitacion.equipo_id)
    juego = db.get(Juego, invitacion.juego_id)
    creador = db.get(Usuario, invitacion.creada_por_usuario_id)

    miembro = _sumar_al_roster(db, background_tasks, equipo, juego, usuario, creador)

    invitacion.estado = "aceptada"
    invitacion.aceptada_por_usuario_id = usuario.id
    invitacion.aceptada_at = _ahora()

    db.commit()
    db.refresh(miembro)

    identidad = (
        db.query(IdentidadDeJuego)
        .filter(
            IdentidadDeJuego.usuario_id == usuario.id,
            IdentidadDeJuego.juego_id == juego.id,
        )
        .first()
    )
    return _armar_miembro_out(miembro, usuario, identidad)
