"""Equipos, jugadores e inscripciones.

La identidad del jugador es JSON (cada juego pide lo suyo) + una clave derivada
que permite el índice único de elegibilidad.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base, DateTimeUTC
from app.domain.enums import EstadoInscripcion


class Equipo(Base):
    """Un equipo, que puede vivir más allá de un torneo.

    Es la entidad PERMANENTE; el plantel de un torneo puntual es la
    `Inscripcion` con sus `Jugador`. Es la misma separación que hacen
    Battlefy (Team vs Tournament Roster) y Toornament: el equipo se conserva,
    el plantel se arma de nuevo en cada edición.

    `propietario_usuario_id` es quién lo administra: inscribirlo en torneos
    nuevos, renombrarlo, verlo en "mis equipos".

    Quien registra el equipo queda de dueño Y de capitán de esa inscripción,
    como en Battlefy. No son lo mismo —el dueño administra el equipo entre
    torneos, el capitán opera dentro de uno— pero arrancan siendo la misma
    persona a propósito. Antes no había nada que los conectara y se podía
    terminar con un equipo cuyo dueño no puede reportar resultados, o con un
    capitán que no puede reinscribirlo. Ver `vincular_al_capitan` en
    app/api/routes/inscripciones.py, y `transferir-capitania` para pasarle el
    rol a otro jugador.

    Nulo a propósito en dos casos que siguen existiendo: los equipos creados
    por una inscripción anónima (la plataforma deja anotarse sin cuenta, y esa
    es una ventaja para torneos de base que no queremos perder) y los que ya
    estaban antes de que esto existiera. Sin dueño, el equipo funciona igual
    dentro de su torneo — lo que no puede es reutilizarse en el siguiente,
    porque nadie puede demostrar que le pertenece.
    """

    __tablename__ = "equipos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), index=True)
    tag: Mapped[str | None] = mapped_column(String(12))
    logo_url: Mapped[str | None] = mapped_column(String(500))

    propietario_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), index=True
    )

    contacto_nombre: Mapped[str | None] = mapped_column(String(120))
    contacto_whatsapp: Mapped[str | None] = mapped_column(String(40))
    contacto_discord: Mapped[str | None] = mapped_column(String(80))

    esta_activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )

    inscripciones: Mapped[list["Inscripcion"]] = relationship(back_populates="equipo")
    miembros: Mapped[list["MiembroEquipo"]] = relationship(back_populates="equipo")


class IdentidadDeJuego(Base):
    """El ID de juego de una persona, en su cuenta y no en un equipo.

    Es el corazón del rediseño. Antes la identidad se tipeaba de nuevo en
    cada inscripción, y la tipeaba el capitán: de ahí salían los IDs mal
    copiados, y que nadie fuera dueño de sus propios datos.

    Acá se carga UNA vez por juego y sirve para siempre. El capitán que te
    suma a su equipo no tiene que saber tu ID —lo toma de tu cuenta— y vos
    lo corregís sin pedirle permiso a nadie.

    El UNIQUE sobre (juego_id, clave_identidad) es global a propósito, y
    tapa algo que antes no se podía ver: la misma cuenta de MLBB declarada
    por dos usuarios distintos de la plataforma. Con la identidad viviendo
    dentro de cada inscripción, esas dos filas nunca se cruzaban.
    """

    __tablename__ = "identidades_de_juego"
    __table_args__ = (
        UniqueConstraint("usuario_id", "juego_id", name="uq_identidad_usuario_juego"),
        UniqueConstraint("juego_id", "clave_identidad", name="uq_identidad_por_juego"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    juego_id: Mapped[int] = mapped_column(ForeignKey("juegos.id"), index=True)

    # Mismo formato que `Jugador.identidad`: {"nick": ..., "id_juego": ...}
    identidad: Mapped[dict] = mapped_column(JSON)
    # Derivada de los campos que el juego declara clave (`Juego.campos_clave`).
    clave_identidad: Mapped[str] = mapped_column(String(200), index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )
    actualizada_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )


class MiembroEquipo(Base):
    """Un jugador que pertenece al equipo ENTRE torneos.

    `Jugador` es el plantel de UNA inscripción y muere con ella; esto es la
    gente del equipo, que sobrevive a la edición. Sirve para lo que antes
    obligaba a retipear todo: el capitán inscribe su equipo en el torneo
    siguiente y el roster ya viene cargado.

    No guarda identidad de juego: esa vive en `IdentidadDeJuego`, en la
    cuenta de la persona. Acá solo está el vínculo. Es lo que permite que
    el capitán sume gente sin tipear los datos de nadie, y que corregir tu
    ID lo arregle en todos tus equipos de una vez.

    Va por juego igual, porque pertenecer al roster de MLBB de un equipo no
    dice nada sobre otro juego.

    **Entrar no requiere aceptar; salir no requiere permiso.** El capitán
    suma directo —armar el equipo no puede depender de que cinco personas
    contesten— pero al sumado le llega una notificación y se va solo cuando
    quiera. Esa asimetría es deliberada: la fricción se saca de entrar, que
    es lo que frena al capitán, y no de salir, que es lo que protege al
    jugador.
    """

    __tablename__ = "miembros_equipo"
    __table_args__ = (
        # Dos filas para la misma persona en el mismo equipo no significan
        # nada, y romperían "el jugador se va de SU fila" al no haber una.
        UniqueConstraint(
            "equipo_id", "juego_id", "usuario_id", name="uq_miembro_equipo_usuario"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipos.id"), index=True)
    juego_id: Mapped[int] = mapped_column(ForeignKey("juegos.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)

    # Quién lo sumó. Con alta directa esto deja de ser un detalle: es la
    # respuesta a "¿quién me metió acá?" que la notificación tiene que dar.
    agregado_por_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id")
    )

    # Baja sin borrar: quién estuvo en el equipo es historia, y borrar la
    # fila haría que un jugador que se fue y volvió pierda el rastro.
    esta_activo: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )
    salio_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )

    equipo: Mapped["Equipo"] = relationship(back_populates="miembros")


class InvitacionAEquipo(Base):
    """Una invitación a sumarse al roster permanente de un equipo.

    NO es el camino normal: al que ya tiene cuenta el capitán lo suma
    directo y listo. Esto es para el caso que eso no cubre — el amigo que
    todavía no se registró. El link lo trae, se crea la cuenta, y queda en
    el equipo sin que el capitán tenga que volver a buscarlo.

    Vive en una tabla y no en memoria como `app/core/tickets.py` porque un
    ticket de stream dura un minuto y se puede perder al reiniciar, y esto
    tiene que seguir vivo si el jugador abre el link mañana.

    Dos formas, misma tabla:
      - `usuario_destino_id` nulo: link abierto, lo acepta el primero que
        lo abra teniendo cuenta. Es el "mandale el link por WhatsApp".
      - `usuario_destino_id` puesto: dirigida a alguien que el capitán
        buscó por nombre. Nadie más la puede aceptar aunque tenga el link.

    No hay estado 'vencida': se deriva de `expira_at` al leerla. Un estado
    guardado que solo un cron mantiene al día es un estado que va a estar
    mal — la regla vive en el código que la consulta.
    """

    __tablename__ = "invitaciones_equipo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipos.id"), index=True)
    juego_id: Mapped[int] = mapped_column(ForeignKey("juegos.id"), index=True)

    # Se guarda en claro y se devuelve UNA sola vez, al crearla. Es un
    # secreto de portador de bajo valor —sirve para entrar a un equipo, no
    # para operar una cuenta— y hachearlo obligaría a re-mostrar un link
    # que ya no se podría reconstruir. Lo que sí se cuida es que no
    # aparezca en los listados.
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    creada_por_usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), index=True
    )
    usuario_destino_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), index=True
    )

    # pendiente | aceptada | revocada
    estado: Mapped[str] = mapped_column(String(20), default="pendiente", index=True)
    expira_at: Mapped[datetime] = mapped_column(DateTimeUTC)

    aceptada_por_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id")
    )
    aceptada_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )


class Inscripcion(Base):
    __tablename__ = "inscripciones"
    __table_args__ = (
        UniqueConstraint("edicion_id", "equipo_id", name="uq_inscripcion_equipo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    edicion_id: Mapped[int] = mapped_column(ForeignKey("ediciones.id"), index=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipos.id"), index=True)

    estado: Mapped[EstadoInscripcion] = mapped_column(
        Enum(EstadoInscripcion, native_enum=False, length=40),
        default=EstadoInscripcion.PENDIENTE,
        index=True,
    )
    motivo_rechazo: Mapped[str | None] = mapped_column(Text)
    seed: Mapped[int | None] = mapped_column(Integer)  # siembra para el sorteo

    # Puntos del equipo para ordenar la siembra: ranking previo, resultados
    # de temporadas pasadas, lo que el organizador decida. Battlefy los llama
    # "participant points" y sirven para lo mismo.
    #
    # Sin esto la siembra era o aleatoria o número por número a mano. Con 8
    # equipos da igual; con 32 de nivel muy dispar, sembrar al azar hace que
    # los dos mejores puedan cruzarse en primera ronda.
    puntos_siembra: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone()
    )
    revisada_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    # Cuándo confirmó asistencia al torneo (ver `Edicion.checkin_abre_at`).
    # Nulo mientras no confirmó: si la edición pide check-in, este equipo
    # queda afuera del sorteo.
    checkin_at: Mapped[datetime | None] = mapped_column(DateTimeUTC)

    # Ventana en la que el organizador autoriza a este equipo a tocar su
    # plantel aunque el torneo ya haya arrancado.
    #
    # Por defecto, apenas se sortea la fase el roster queda congelado: es lo
    # correcto, porque cambiarlo a mitad de torneo es la vía para meter un
    # jugador de refuerzo antes de la final. Pero el caso legítimo existe y
    # es común —a alguien se le rompe el celular en cuartos— y antes no había
    # forma de resolverlo: el bloqueo no tenía excepción ni siquiera para el
    # organizador, y el mensaje de error mandaba a hacer "directamente" algo
    # que ningún endpoint permitía.
    cambio_roster_hasta: Mapped[datetime | None] = mapped_column(DateTimeUTC)
    cambio_roster_motivo: Mapped[str | None] = mapped_column(Text)

    equipo: Mapped["Equipo"] = relationship(back_populates="inscripciones")
    jugadores: Mapped[list["Jugador"]] = relationship(
        back_populates="inscripcion",
        cascade="all, delete-orphan",
        order_by="Jugador.orden",
    )

    @property
    def titulares(self) -> list["Jugador"]:
        return [j for j in self.jugadores if not j.es_suplente]

    @property
    def suplentes(self) -> list["Jugador"]:
        return [j for j in self.jugadores if j.es_suplente]


class CambioDeRoster(Base):
    """Rastro de un cambio de plantel hecho con el torneo ya empezado.

    No es burocracia: modificar un roster en cuartos es exactamente lo que
    después se discute —"metieron un jugador de afuera para la final"— y sin
    registro queda la palabra de uno contra la del otro. Guarda quién entró,
    quién salió, cuándo, con qué motivo y quién lo autorizó.

    Mismo espíritu que `ReporteResultado`: append-only, cada cambio es su
    propia fila y nunca se pisa una anterior.

    Solo se registran los cambios hechos DESPUÉS del sorteo. Editar el roster
    mientras la inscripción está pendiente es parte normal de anotarse y no
    necesita rastro.
    """

    __tablename__ = "cambios_de_roster"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inscripcion_id: Mapped[int] = mapped_column(
        ForeignKey("inscripciones.id"), index=True
    )

    # Nicks, no ids: los `Jugador` que salen se borran al reemplazar el
    # roster, así que guardar su id dejaría una referencia a la nada.
    entraron: Mapped[str | None] = mapped_column(Text)
    salieron: Mapped[str | None] = mapped_column(Text)

    motivo_autorizacion: Mapped[str | None] = mapped_column(Text)
    autorizado_por_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id")
    )
    aplicado_por_usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTimeUTC, default=lambda: datetime.now().astimezone(), index=True
    )


class Jugador(Base):
    """Un jugador dentro de una inscripción concreta.

    El mismo humano puede aparecer en varias ediciones; lo que impide que esté en
    dos equipos de LA MISMA edición es el índice único sobre clave_identidad.
    """

    __tablename__ = "jugadores"
    __table_args__ = (
        # Único PARCIAL: la regla es "un jugador en un solo equipo por
        # edición", pero solo cuenta mientras su inscripción esté viva.
        #
        # Antes era un UNIQUE común y eso dejaba un agujero: al rechazar un
        # equipo, sus cinco jugadores seguían ocupando cupo y no podían
        # entrar en ningún otro, para siempre. El chequeo de la aplicación
        # solo no alcanza — sin restricción en la base, dos inscripciones
        # simultáneas del mismo jugador pasan las dos.
        #
        # La condición va sobre `ocupa_cupo` y no sobre el estado de la
        # inscripción porque un índice no puede mirar otra tabla.
        Index(
            "uq_jugador_elegibilidad",
            "edicion_id",
            "clave_identidad",
            unique=True,
            sqlite_where=text("ocupa_cupo = 1"),
            postgresql_where=text("ocupa_cupo"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inscripcion_id: Mapped[int] = mapped_column(
        ForeignKey("inscripciones.id"), index=True
    )
    # Desnormalizado a propósito: hace posible el constraint de elegibilidad.
    edicion_id: Mapped[int] = mapped_column(ForeignKey("ediciones.id"), index=True)

    # {"nick": "Lyon", "id_juego": "123456789", "server": "2251"}
    identidad: Mapped[dict] = mapped_column(JSON)
    # Derivada de los campos clave del juego: "123456789|2251"
    clave_identidad: Mapped[str] = mapped_column(String(200), index=True)

    orden: Mapped[int] = mapped_column(Integer, default=0)
    es_suplente: Mapped[bool] = mapped_column(Boolean, default=False)
    es_capitan: Mapped[bool] = mapped_column(Boolean, default=False)

    # Si este jugador bloquea el cupo de elegibilidad de la edición.
    #
    # Es un derivado del estado de la inscripción (ver
    # ESTADOS_QUE_OCUPAN_CUPO): existe desnormalizado acá solo porque el
    # índice único parcial de arriba no puede consultar otra tabla. La
    # sincronización vive en `sincronizar_cupo_de_elegibilidad`
    # (app/api/routes/inscripciones.py) y se llama desde los únicos tres
    # lugares que cambian el estado de una inscripción.
    ocupa_cupo: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="1", nullable=False
    )

    # Vincula a este jugador con una cuenta de Discord real. Nulo mientras
    # el equipo se inscribe sin que nadie haya iniciado sesión todavía — se
    # completa cuando el capitán se loguea por primera vez y confirma que es
    # él. Sin esto, reportar/confirmar resultados no tiene con qué verificar
    # que quien llama es realmente el capitán de este equipo.
    # Mismo largo que `Usuario.discord_id`: acá se guarda exactamente el
    # mismo valor, incluido el sintético "local:<email>" de las cuentas
    # locales. Si esta columna fuera más corta, vincular a un jugador con
    # una cuenta local de email largo fallaría solo en Postgres.
    discord_id: Mapped[str | None] = mapped_column(String(320), index=True)

    inscripcion: Mapped["Inscripcion"] = relationship(back_populates="jugadores")

    @property
    def nick(self) -> str:
        return self.identidad.get("nick", "?")
