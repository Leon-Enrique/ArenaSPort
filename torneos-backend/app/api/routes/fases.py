from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession, RequiereOrganizador
from app.domain import sorteo
from app.domain.enums import EstadoFase, EstadoInscripcion, EstadoPartida, FormatoFase, LadoLlave
from app.domain.formatos import suizo
from app.domain.formatos.base import ErrorFormato
from app.domain.partidas import bo_para_ronda
from app.domain.tabla import PartidaParaTabla, calcular_tabla, clasificados_ordenados
from app.models import Edicion, Fase, Inscripcion, Partida, ParticipacionEnPartida
from app.schemas.fases import FaseCreate, FaseRead, SortearDesdeFaseAnteriorIn, TablaGrupoRead
from app.schemas.partidas import PartidaRead

router = APIRouter(prefix="/ediciones/{edicion_id}/fases", tags=["fases"])


@router.post("", response_model=FaseRead, status_code=status.HTTP_201_CREATED)
def crear_fase(edicion_id: int, datos: FaseCreate, db: DbSession, _organizador: RequiereOrganizador) -> Fase:
    if not db.get(Edicion, edicion_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La edición no existe.")

    if (
        db.query(Fase)
        .filter(Fase.edicion_id == edicion_id, Fase.orden == datos.orden)
        .first()
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Ya existe una fase con orden {datos.orden}."
        )

    fase = Fase(
        edicion_id=edicion_id,
        orden=datos.orden,
        nombre=datos.nombre.strip(),
        modelo_competencia=datos.modelo_competencia,
        formato=datos.formato,
        config=datos.config,
    )
    db.add(fase)
    db.commit()
    db.refresh(fase)
    return fase


@router.get("", response_model=list[FaseRead])
def listar_fases(edicion_id: int, db: DbSession) -> list[Fase]:
    return (
        db.query(Fase)
        .filter(Fase.edicion_id == edicion_id)
        .order_by(Fase.orden)
        .all()
    )


def _obtener_fase(db: DbSession, edicion_id: int, fase_id: int) -> Fase:
    fase = db.get(Fase, fase_id)
    if not fase or fase.edicion_id != edicion_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "La fase no existe.")
    return fase


@router.post("/{fase_id}/sortear", response_model=list[PartidaRead])
def sortear_fase(edicion_id: int, fase_id: int, db: DbSession, _organizador: RequiereOrganizador) -> list:
    """Genera toda la estructura de la fase de una vez: llave, grupos, o
    ronda 1 de suizo — según el formato configurado.

    Usa el equipo `seed` de la inscripción para ordenar la siembra. Si algún
    equipo aprobado no tiene seed asignado, hay que sembrar primero
    (`POST /ediciones/{id}/inscripciones/sembrar-automatico`).
    """
    fase = _obtener_fase(db, edicion_id, fase_id)

    if fase.estado != EstadoFase.PENDIENTE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Esta fase ya fue sorteada (estado: {fase.estado}). "
            "Sortear de nuevo requeriría borrar las partidas existentes — "
            "no es una operación que este endpoint haga por vos.",
        )

    aprobadas = (
        db.query(Inscripcion)
        .filter(
            Inscripcion.edicion_id == edicion_id,
            Inscripcion.estado == EstadoInscripcion.APROBADA,
        )
        .all()
    )
    if len(aprobadas) < 2:
        raise HTTPException(422, "Hacen falta al menos 2 equipos aprobados.")

    sin_seed = [i for i in aprobadas if i.seed is None]
    if sin_seed:
        nombres = ", ".join(i.equipo.nombre for i in sin_seed[:5])
        extra = "..." if len(sin_seed) > 5 else ""
        raise HTTPException(
            422,
            f"{len(sin_seed)} equipo(s) sin seed asignado ({nombres}{extra}). "
            "Sembrá primero con /inscripciones/sembrar-automatico.",
        )

    equipos_ordenados = [
        i.equipo_id for i in sorted(aprobadas, key=lambda i: i.seed)
    ]

    try:
        partidas = sorteo.sortear_fase(db, fase, equipos_ordenados)
    except ErrorFormato as e:
        raise HTTPException(422, str(e)) from e

    return partidas


@router.get("/{fase_id}/tabla", response_model=list[TablaGrupoRead])
def obtener_tabla(edicion_id: int, fase_id: int, db: DbSession) -> list[TablaGrupoRead]:
    """Tabla de posiciones, calculada al vuelo desde las partidas confirmadas
    — nunca es la fuente de verdad, se recalcula cada vez que se pide.

    Solo tiene sentido en round robin y suizo. En llaves de eliminación no
    hay "tabla", hay bracket — usar `GET /fases/{id}/partidas` para eso.
    """
    fase = _obtener_fase(db, edicion_id, fase_id)

    if fase.formato not in (FormatoFase.ROUND_ROBIN, FormatoFase.SUIZO):
        raise HTTPException(
            422,
            f"El formato '{fase.formato}' no tiene tabla de posiciones — "
            "usá /partidas para ver el bracket.",
        )

    todas_las_partidas = db.query(Partida).filter(Partida.fase_id == fase_id).all()
    if not todas_las_partidas:
        return []

    hay_grupos = any(p.grupo_numero is not None for p in todas_las_partidas)
    grupos_numeros = sorted({p.grupo_numero for p in todas_las_partidas}) if hay_grupos else [None]

    sistema_puntaje = fase.edicion.sistema_puntaje or {}
    criterios = fase.edicion.criterios_desempate or None

    resultado: list[TablaGrupoRead] = []
    equipos_cache: dict[int, str] = {}

    for grupo_numero in grupos_numeros:
        partidas_del_grupo = [
            p for p in todas_las_partidas
            if (p.grupo_numero == grupo_numero if hay_grupos else True)
        ]

        equipos_ids: set[int] = set()
        for p in partidas_del_grupo:
            for part in p.participaciones:
                equipos_ids.add(part.equipo_id)
                if part.equipo_id not in equipos_cache:
                    equipos_cache[part.equipo_id] = part.equipo.nombre

        partidas_para_tabla: list[PartidaParaTabla] = []
        for p in partidas_del_grupo:
            if p.estado not in (EstadoPartida.CONFIRMADA, EstadoPartida.WALKOVER):
                continue
            if len(p.participaciones) != 2:
                continue
            pa, pb = p.participaciones[0], p.participaciones[1]

            mapas_a, mapas_b = pa.mapas_ganados, pb.mapas_ganados
            if mapas_a is None or mapas_b is None:
                # Walkover sin marcador cargado a mano: se cuenta con el
                # resultado "de reglamento" para no perjudicar la diferencia
                # de mapas — máximo del BO para el ganador, 0 para el otro.
                maximo = bo_para_ronda(fase.config, p.ronda) // 2 + 1
                mapas_a = maximo if pa.es_ganador else 0
                mapas_b = maximo if pb.es_ganador else 0

            partidas_para_tabla.append(
                PartidaParaTabla(
                    equipo_a_id=pa.equipo_id,
                    equipo_b_id=pb.equipo_id,
                    mapas_a=mapas_a,
                    mapas_b=mapas_b,
                )
            )

        filas = calcular_tabla(
            equipos_ids=list(equipos_ids),
            partidas=partidas_para_tabla,
            sistema_puntaje=sistema_puntaje,
            criterios_desempate=criterios,
        )

        # Bye suizo (cantidad impar de equipos): partida de una sola
        # participación, no entra en calcular_tabla porque no tiene rival
        # real — se le suma la victoria a mano. El desempate fino entre
        # empatados después de este bono no se reevalúa con los criterios
        # completos; para la cantidad de equipos donde esto aplica (suizo
        # con número impar) el efecto práctico es marginal, pero es una
        # simplificación real, no un descuido silencioso.
        pts_victoria = (sistema_puntaje or {}).get("victoria", 3)
        por_id = {f.equipo_id: f for f in filas}
        hubo_bye = False
        for p in partidas_del_grupo:
            if p.estado == EstadoPartida.BYE and len(p.participaciones) == 1:
                ganador_bye = p.participaciones[0]
                fila = por_id.get(ganador_bye.equipo_id)
                if fila:
                    fila.jugados += 1
                    fila.victorias += 1
                    fila.puntos += pts_victoria
                    hubo_bye = True
        if hubo_bye:
            filas = sorted(filas, key=lambda f: -f.puntos)
            for i, f in enumerate(filas, start=1):
                f.posicion = i

        resultado.append(
            TablaGrupoRead(
                grupo=grupo_numero,
                filas=[
                    {
                        "equipo_id": f.equipo_id,
                        "equipo_nombre": equipos_cache[f.equipo_id],
                        "posicion": f.posicion,
                        "jugados": f.jugados,
                        "victorias": f.victorias,
                        "empates": f.empates,
                        "derrotas": f.derrotas,
                        "mapas_favor": f.mapas_favor,
                        "mapas_contra": f.mapas_contra,
                        "diferencia_mapas": f.diferencia_mapas,
                        "puntos": f.puntos,
                    }
                    for f in filas
                ],
            )
        )

    return resultado


@router.post("/{fase_id}/siguiente-ronda-suiza", response_model=list[PartidaRead])
def generar_siguiente_ronda_suiza(
    edicion_id: int, fase_id: int, db: DbSession, _organizador: RequiereOrganizador
) -> list[Partida]:
    """Genera la próxima ronda del suizo, emparejando por puntaje y evitando
    repetir rivales cuando es posible.

    Solo se puede pedir una ronda a la vez, y solo cuando la anterior está
    completa — el formato suizo no permite precalcular todo de una, cada
    ronda depende de los resultados de la anterior.
    """
    fase = _obtener_fase(db, edicion_id, fase_id)

    if fase.formato != FormatoFase.SUIZO:
        raise HTTPException(422, f"Esta fase es '{fase.formato}', no suizo.")
    if fase.estado != EstadoFase.SORTEADA:
        raise HTTPException(
            422,
            "Todavía no se sorteó la ronda 1 — usá /sortear primero.",
        )

    todas = db.query(Partida).filter(Partida.fase_id == fase_id).all()
    if not todas:
        raise HTTPException(422, "Esta fase no tiene partidas todavía.")

    ronda_actual = max(p.ronda for p in todas)
    partidas_ronda_actual = [p for p in todas if p.ronda == ronda_actual]

    sin_resolver = [
        p for p in partidas_ronda_actual
        if p.estado not in (EstadoPartida.CONFIRMADA, EstadoPartida.WALKOVER, EstadoPartida.BYE)
    ]
    if sin_resolver:
        raise HTTPException(
            409,
            f"Todavía hay {len(sin_resolver)} partida(s) de la ronda {ronda_actual} "
            "sin resolver — no se puede generar la próxima ronda hasta que termine esta.",
        )

    # Tabla acumulada con TODO lo jugado hasta ahora, no solo la última ronda.
    equipos_ids: set[int] = set()
    partidas_para_tabla: list[PartidaParaTabla] = []
    enfrentamientos_previos: set[tuple[int, int]] = set()

    for p in todas:
        for part in p.participaciones:
            equipos_ids.add(part.equipo_id)

        if p.estado == EstadoPartida.BYE and len(p.participaciones) == 1:
            continue  # el bono de bye se aplica en /tabla, no acá

        if p.estado not in (EstadoPartida.CONFIRMADA, EstadoPartida.WALKOVER):
            continue
        if len(p.participaciones) != 2:
            continue

        pa, pb = p.participaciones[0], p.participaciones[1]
        enfrentamientos_previos.add((min(pa.equipo_id, pb.equipo_id), max(pa.equipo_id, pb.equipo_id)))

        mapas_a, mapas_b = pa.mapas_ganados, pb.mapas_ganados
        if mapas_a is None or mapas_b is None:
            maximo = bo_para_ronda(fase.config, p.ronda) // 2 + 1
            mapas_a = maximo if pa.es_ganador else 0
            mapas_b = maximo if pb.es_ganador else 0

        partidas_para_tabla.append(
            PartidaParaTabla(equipo_a_id=pa.equipo_id, equipo_b_id=pb.equipo_id, mapas_a=mapas_a, mapas_b=mapas_b)
        )

    sistema_puntaje = fase.edicion.sistema_puntaje or {}
    filas = calcular_tabla(
        equipos_ids=list(equipos_ids),
        partidas=partidas_para_tabla,
        sistema_puntaje=sistema_puntaje,
    )
    # Aplicar bonos de bye de rondas anteriores para que el emparejamiento
    # de la ronda nueva también respete el puntaje real acumulado.
    pts_victoria = sistema_puntaje.get("victoria", 3)
    por_id = {f.equipo_id: f for f in filas}
    for p in todas:
        if p.estado == EstadoPartida.BYE and len(p.participaciones) == 1:
            fila = por_id.get(p.participaciones[0].equipo_id)
            if fila:
                fila.puntos += pts_victoria
                fila.victorias += 1

    # Suizo "con corte" (MPL/M7): N victorias clasifica, N derrotas elimina
    # — a partir de ahí ese equipo ya no vuelve a jugar. Sin esta config en
    # la fase, el suizo sigue siendo el genérico de siempre (todos juegan
    # todas las rondas que pida el organizador).
    meta_victorias = fase.config.get("meta_victorias") if fase.config else None
    meta_derrotas = fase.config.get("meta_derrotas") if fase.config else None

    tabla_suizo = [
        suizo.EquipoConPuntaje(
            equipo_id=f.equipo_id, puntos=f.puntos, diferencia=f.diferencia_mapas,
            victorias=f.victorias, derrotas=f.derrotas,
        )
        for f in filas
    ]

    if (meta_victorias is not None or meta_derrotas is not None):
        activos = [
            e for e in tabla_suizo
            if (meta_victorias is None or e.victorias < meta_victorias)
            and (meta_derrotas is None or e.derrotas < meta_derrotas)
        ]
        if len(activos) < 2:
            raise HTTPException(
                422,
                "El suizo ya terminó — todos los equipos activos llegaron a su "
                "corte de victorias o derrotas. Cerrá la fase y avanzá a los "
                "clasificados a la siguiente etapa.",
            )

    try:
        pares = suizo.generar_siguiente_ronda(
            tabla_suizo, enfrentamientos_previos,
            meta_victorias=meta_victorias, meta_derrotas=meta_derrotas,
        )
    except ErrorFormato as e:
        raise HTTPException(422, str(e)) from e

    nueva_ronda = ronda_actual + 1
    creadas: list[Partida] = []

    for equipo_a, equipo_b in pares:
        partida = Partida(fase_id=fase_id, lado=LadoLlave.UNICA, ronda=nueva_ronda)
        db.add(partida)
        db.flush()
        db.add(ParticipacionEnPartida(partida_id=partida.id, equipo_id=equipo_a, slot=0))
        db.add(ParticipacionEnPartida(partida_id=partida.id, equipo_id=equipo_b, slot=1))
        creadas.append(partida)

    ya_emparejados = {eid for par in pares for eid in par}
    activos_count = len([
        e for e in tabla_suizo
        if (meta_victorias is None or e.victorias < meta_victorias)
        and (meta_derrotas is None or e.derrotas < meta_derrotas)
    ])
    if activos_count % 2 != 0:
        libre = suizo.equipo_libre(tabla_suizo, ya_emparejados, meta_victorias=meta_victorias, meta_derrotas=meta_derrotas)
        if libre:
            partida_bye = Partida(
                fase_id=fase_id, lado=LadoLlave.UNICA, ronda=nueva_ronda,
                estado=EstadoPartida.BYE,
            )
            db.add(partida_bye)
            db.flush()
            db.add(
                ParticipacionEnPartida(
                    partida_id=partida_bye.id, equipo_id=libre, slot=0, es_ganador=True
                )
            )
            creadas.append(partida_bye)

    db.commit()
    for p in creadas:
        db.refresh(p)
    return creadas


@router.post("/{fase_id}/cerrar", response_model=FaseRead)
def cerrar_fase(edicion_id: int, fase_id: int, db: DbSession, _organizador: RequiereOrganizador) -> Fase:
    """Marca la fase como `cerrada` — requiere que TODAS sus partidas estén
    en un estado terminal (confirmada, walkover o bye). Si queda algo
    pendiente (en curso, en disputa, sin siquiera empezar), se rechaza con
    el detalle de cuántas faltan.

    Cerrar una fase es lo que habilita sacar sus clasificados para
    sembrar la siguiente (`/sortear-desde-fase-anterior`) — no tiene
    sentido clasificar a nadie desde una tabla todavía incompleta.
    """
    fase = _obtener_fase(db, edicion_id, fase_id)

    if fase.estado == EstadoFase.CERRADA:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta fase ya está cerrada.")
    if fase.estado == EstadoFase.PENDIENTE:
        raise HTTPException(422, "Esta fase todavía ni se sorteó.")

    todas = db.query(Partida).filter(Partida.fase_id == fase_id).all()
    terminales = (EstadoPartida.CONFIRMADA, EstadoPartida.WALKOVER, EstadoPartida.BYE)
    sin_terminar = [p for p in todas if p.estado not in terminales]

    if sin_terminar:
        estados = {}
        for p in sin_terminar:
            estados[p.estado] = estados.get(p.estado, 0) + 1
        detalle = ", ".join(f"{cant} en '{est}'" for est, cant in estados.items())
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Quedan {len(sin_terminar)} partida(s) sin resolver ({detalle}) — "
            "no se puede cerrar la fase todavía.",
        )

    fase.estado = EstadoFase.CERRADA
    db.commit()
    db.refresh(fase)
    return fase


def _tabla_por_grupo_pura(
    db: DbSession, fase: Fase
) -> dict[int | None, tuple[list[int], list[PartidaParaTabla]]]:
    """Arma, por cada grupo de la fase, la lista de equipos y las partidas
    resueltas en formato apto para `calcular_tabla` — la misma
    recolección que usa GET /tabla, extraída para reusar acá sin duplicar
    la lógica de walkover-sin-marcador.
    """
    todas_las_partidas = db.query(Partida).filter(Partida.fase_id == fase.id).all()
    hay_grupos = any(p.grupo_numero is not None for p in todas_las_partidas)
    grupos_numeros = sorted({p.grupo_numero for p in todas_las_partidas}) if hay_grupos else [None]

    resultado: dict[int | None, tuple[list[int], list[PartidaParaTabla]]] = {}
    for grupo_numero in grupos_numeros:
        partidas_del_grupo = [
            p for p in todas_las_partidas
            if (p.grupo_numero == grupo_numero if hay_grupos else True)
        ]
        equipos_ids: set[int] = set()
        for p in partidas_del_grupo:
            for part in p.participaciones:
                equipos_ids.add(part.equipo_id)

        partidas_para_tabla: list[PartidaParaTabla] = []
        for p in partidas_del_grupo:
            if p.estado not in (EstadoPartida.CONFIRMADA, EstadoPartida.WALKOVER):
                continue
            if len(p.participaciones) != 2:
                continue
            pa, pb = p.participaciones[0], p.participaciones[1]
            mapas_a, mapas_b = pa.mapas_ganados, pb.mapas_ganados
            if mapas_a is None or mapas_b is None:
                maximo = bo_para_ronda(fase.config, p.ronda) // 2 + 1
                mapas_a = maximo if pa.es_ganador else 0
                mapas_b = maximo if pb.es_ganador else 0
            partidas_para_tabla.append(
                PartidaParaTabla(equipo_a_id=pa.equipo_id, equipo_b_id=pb.equipo_id, mapas_a=mapas_a, mapas_b=mapas_b)
            )

        resultado[grupo_numero] = (list(equipos_ids), partidas_para_tabla)

    return resultado


def _ganadores_de_ronda_bracket(db: DbSession, fase_origen: Fase, ronda: int) -> list[int]:
    """Los ganadores de una ronda puntual de una llave de eliminación —
    fuente alternativa a la tabla, para encadenar 'ronda de 16 -> 8
    ganadores -> fase nueva' sin que haga falta que el resto de esa llave
    (rondas siguientes) se juegue ni se cierre jamás.
    """
    partidas_ronda = (
        db.query(Partida)
        .filter(
            Partida.fase_id == fase_origen.id,
            Partida.ronda == ronda,
            Partida.lado == LadoLlave.UNICA,
        )
        .order_by(Partida.id)
        .all()
    )
    if not partidas_ronda:
        raise HTTPException(
            422, f"La fase de origen no tiene partidas en la ronda {ronda}."
        )

    terminales = (EstadoPartida.CONFIRMADA, EstadoPartida.WALKOVER, EstadoPartida.BYE)
    sin_resolver = [p for p in partidas_ronda if p.estado not in terminales]
    if sin_resolver:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Quedan {len(sin_resolver)} partida(s) sin resolver en la ronda "
            f"{ronda} de la fase de origen — no se puede sacar a los "
            "ganadores todavía.",
        )

    ganadores = []
    for p in partidas_ronda:
        ganador_id = next((part.equipo_id for part in p.participaciones if part.es_ganador), None)
        if ganador_id is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"La partida #{p.id} no tiene un ganador definido.",
            )
        ganadores.append(ganador_id)
    return ganadores


@router.post("/{fase_id}/sortear-desde-fase-anterior", response_model=list[PartidaRead])
def sortear_desde_fase_anterior(
    edicion_id: int, fase_id: int, datos: SortearDesdeFaseAnteriorIn, db: DbSession,
    _organizador: RequiereOrganizador,
) -> list[Partida]:
    """Arma la llave de esta fase con los clasificados de una fase
    anterior — dos fuentes posibles, según qué tipo de fase sea la de
    origen:

    - **Grupos o suizo** (tiene tabla): usa `cupos_por_grupo`, exige que la
      fase de origen esté `cerrada` (todas sus partidas resueltas). Patrón
      real de Toornament ('Outgoing Participants' ordenados por rango).
    - **Eliminación simple** (tiene bracket, no tabla): usa `ronda_origen`,
      toma los ganadores de esa ronda puntual — NO exige que el resto de
      esa llave se juegue ni se cierre. Sirve para el caso real de
      "grupos → ronda de 16 → los 8 ganadores arrancan una llave doble
      completamente nueva", sin necesitar terminar la llave simple original.
    """
    fase = _obtener_fase(db, edicion_id, fase_id)
    if fase.estado != EstadoFase.PENDIENTE:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Esta fase ya fue sorteada (estado: {fase.estado}).",
        )

    fase_origen = _obtener_fase(db, edicion_id, datos.fase_origen_id)

    if fase_origen.formato in (FormatoFase.ROUND_ROBIN, FormatoFase.SUIZO):
        if fase_origen.estado != EstadoFase.CERRADA:
            raise HTTPException(
                422,
                f"La fase de origen tiene que estar 'cerrada' (está en "
                f"'{fase_origen.estado}') — cerrala primero con /cerrar.",
            )
        if datos.cupos_por_grupo is None:
            raise HTTPException(
                422, "Hace falta 'cupos_por_grupo' para una fase de origen de grupos/suizo."
            )

        datos_por_grupo = _tabla_por_grupo_pura(db, fase_origen)
        sistema_puntaje = fase_origen.edicion.sistema_puntaje or {}
        criterios = fase_origen.edicion.criterios_desempate or None
        tablas_por_grupo = {
            grupo: calcular_tabla(equipos_ids, partidas, sistema_puntaje, criterios)
            for grupo, (equipos_ids, partidas) in datos_por_grupo.items()
        }
        clasificados = clasificados_ordenados(tablas_por_grupo, datos.cupos_por_grupo)

    elif fase_origen.formato == FormatoFase.ELIMINACION_SIMPLE:
        if datos.ronda_origen is None:
            raise HTTPException(
                422, "Hace falta 'ronda_origen' para una fase de origen de eliminación simple."
            )
        clasificados = _ganadores_de_ronda_bracket(db, fase_origen, datos.ronda_origen)

    else:
        raise HTTPException(
            422,
            f"No se puede sacar clasificados automáticos de una fase "
            f"'{fase_origen.formato}' todavía.",
        )

    if len(clasificados) < 2:
        raise HTTPException(
            422,
            f"Solo salieron {len(clasificados)} clasificado(s) — hacen falta al menos 2.",
        )

    try:
        partidas_creadas = sorteo.sortear_fase(db, fase, clasificados)
    except ErrorFormato as e:
        raise HTTPException(422, str(e)) from e

    return partidas_creadas


@router.post("/{fase_id}/resetear-sorteo", response_model=FaseRead)
def resetear_sorteo(edicion_id: int, fase_id: int, db: DbSession, _organizador: RequiereOrganizador) -> Fase:
    """Deshace un sorteo hecho por error (ej. se sorteó con todos los
    inscritos de la edición en vez de con los clasificados de la fase
    anterior): borra sus partidas y la devuelve a `pendiente` para volver
    a sortear.

    Solo lo permite si NINGUNA partida tuvo actividad real todavía (nada
    más que `programada` o `bye`) — si ya hubo check-in, reporte o
    confirmación, borrar partidas se llevaría resultados reales por
    delante, y eso lo tiene que decidir un organizador a mano, no un
    endpoint solo.
    """
    fase = _obtener_fase(db, edicion_id, fase_id)
    if fase.estado not in (EstadoFase.SORTEADA, EstadoFase.EN_CURSO):
        raise HTTPException(422, f"Esta fase está '{fase.estado}' — no hay sorteo que resetear.")

    todas = db.query(Partida).filter(Partida.fase_id == fase_id).all()
    tocadas = [p for p in todas if p.estado not in (EstadoPartida.PROGRAMADA, EstadoPartida.BYE)]
    if tocadas:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Hay {len(tocadas)} partida(s) con actividad (check-in, reporte o resultado) — "
            "no se puede resetear el sorteo sin perder eso. Revisalo a mano.",
        )

    for p in todas:
        db.delete(p)
    fase.estado = EstadoFase.PENDIENTE
    db.commit()
    db.refresh(fase)
    return fase


@router.delete("/{fase_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_fase(edicion_id: int, fase_id: int, db: DbSession, _organizador: RequiereOrganizador) -> None:
    """Borra una fase entera (no solo su sorteo) — para cuando se agregó
    por error o se cambió de opinión sobre el formato.

    Mismo criterio que `/resetear-sorteo`: solo lo permite si NINGUNA
    partida tuvo actividad real todavía (nada más que `programada` o
    `bye`). Si la fase está `cerrada` o tiene resultados reales, no se
    puede borrar desde acá — eso lo revisa un organizador a mano.
    """
    fase = _obtener_fase(db, edicion_id, fase_id)

    todas = db.query(Partida).filter(Partida.fase_id == fase_id).all()
    tocadas = [p for p in todas if p.estado not in (EstadoPartida.PROGRAMADA, EstadoPartida.BYE)]
    if tocadas:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Esta fase tiene {len(tocadas)} partida(s) con actividad (check-in, reporte o "
            "resultado) — no se puede borrar. Si hace falta, revisalo a mano.",
        )

    partida_ids = [p.id for p in todas]
    if partida_ids:
        db.query(ParticipacionEnPartida).filter(
            ParticipacionEnPartida.partida_id.in_(partida_ids)
        ).delete(synchronize_session=False)
        db.query(Partida).filter(Partida.id.in_(partida_ids)).delete(synchronize_session=False)

    db.delete(fase)
    db.commit()
