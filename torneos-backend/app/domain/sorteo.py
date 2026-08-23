"""Persiste la estructura pura de los generadores de formato como filas de
`Partida` + `ParticipacionEnPartida`, con los enlaces de avance resueltos.

Esta es la única pieza que toca la base de datos — los generadores en
`app/domain/formatos/` son puro Python y no saben nada de SQLAlchemy. No es
"dominio puro" en sentido estricto (sí toca DB), pero se mantiene separado
de los routers porque orquesta varias tablas y se reutiliza en más de un
lugar (sorteo inicial y avance de rondas suizas).
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.enums import EstadoFase, EstadoPartida, FormatoFase, LadoLlave
from app.domain.formatos import (
    eliminacion_doble,
    eliminacion_simple,
    round_robin,
    suizo,
)
from app.domain.formatos.base import Cruce, ErrorFormato, TipoFuente
from app.models import Fase, Partida, ParticipacionEnPartida


def sortear_fase(db: Session, fase: Fase, equipos_ordenados: list[int]) -> list[Partida]:
    """Genera y persiste toda la estructura de una fase de una vez.

    `equipos_ordenados`: ids de equipo en el orden de siembra correspondiente.
    """
    if fase.formato == FormatoFase.ELIMINACION_SIMPLE:
        # `tercer_puesto` en la config de la fase agrega el cruce entre los
        # perdedores de semifinales. La eliminación doble no lo necesita: ahí
        # el tercer puesto sale de la llave baja.
        con_tercero = bool((fase.config or {}).get("tercer_puesto"))
        return _persistir_llave(
            db, fase, eliminacion_simple.generar(equipos_ordenados, con_tercero)
        )

    if fase.formato == FormatoFase.ELIMINACION_DOBLE:
        return _persistir_llave(db, fase, eliminacion_doble.generar(equipos_ordenados))

    if fase.formato == FormatoFase.ROUND_ROBIN:
        return _persistir_round_robin(db, fase, equipos_ordenados)

    if fase.formato == FormatoFase.SUIZO:
        return _persistir_ronda_suiza(db, fase, equipos_ordenados, numero_ronda=1)

    raise ErrorFormato(f"Formato no soportado todavía: {fase.formato}")


def _persistir_llave(db: Session, fase: Fase, resultado) -> list[Partida]:
    """Común a eliminación simple y doble: dos pasadas — crear filas, después
    resolver los enlaces de avance ahora que ya existen los IDs reales.
    """
    partida_por_indice: dict[int, Partida] = {}

    for c in sorted(resultado.cruces, key=lambda c: c.indice):
        lado = LadoLlave(c.lado) if c.lado != "unica" else LadoLlave.UNICA
        partida = Partida(
            fase_id=fase.id,
            lado=lado,
            ronda=c.ronda,
            estado=EstadoPartida.BYE if c.es_bye else EstadoPartida.PROGRAMADA,
        )
        db.add(partida)
        db.flush()
        partida_por_indice[c.indice] = partida

        if c.fuente_a.tipo == TipoFuente.EQUIPO:
            db.add(
                ParticipacionEnPartida(
                    partida_id=partida.id,
                    equipo_id=c.fuente_a.valor,
                    slot=0,
                    es_ganador=True if c.es_bye else None,
                )
            )
        if c.fuente_b.tipo == TipoFuente.EQUIPO:
            db.add(
                ParticipacionEnPartida(
                    partida_id=partida.id,
                    equipo_id=c.fuente_b.valor,
                    slot=1,
                    es_ganador=True if c.es_bye else None,
                )
            )
        if c.es_bye:
            partida.confirmada_at = datetime.now(UTC)

    db.flush()

    for c in resultado.cruces:
        destino = partida_por_indice[c.indice]
        _enlazar_fuente(c.fuente_a, destino, slot=0, partida_por_indice=partida_por_indice)
        _enlazar_fuente(c.fuente_b, destino, slot=1, partida_por_indice=partida_por_indice)

    db.commit()

    partidas_creadas = list(partida_por_indice.values())
    for p in partidas_creadas:
        if p.estado == EstadoPartida.BYE:
            db.refresh(p)
            avanzar_ganador(db, p)

    fase.estado = EstadoFase.SORTEADA
    db.commit()

    for p in partidas_creadas:
        db.refresh(p)
    return partidas_creadas


def _enlazar_fuente(fuente, destino: Partida, slot: int, partida_por_indice: dict[int, Partida]) -> None:
    if fuente.tipo == TipoFuente.GANADOR_DE:
        origen = partida_por_indice[fuente.valor]
        origen.siguiente_partida_ganador_id = destino.id
        origen.siguiente_slot_ganador = slot
    elif fuente.tipo == TipoFuente.PERDEDOR_DE:
        origen = partida_por_indice[fuente.valor]
        origen.siguiente_partida_perdedor_id = destino.id
        origen.siguiente_slot_perdedor = slot
    # EQUIPO y VACIO no necesitan enlace: ya están resueltos o nunca llegan.


def _persistir_round_robin(db: Session, fase: Fase, equipos: list[int]) -> list[Partida]:
    cantidad_grupos = fase.config.get("grupos", 1)
    grupos = round_robin.dividir_en_grupos(equipos, cantidad_grupos) if cantidad_grupos > 1 else [equipos]

    creadas: list[Partida] = []
    for numero_grupo, g in enumerate(grupos):
        # Si hay un solo grupo (todo el mundo en el mismo round robin), no
        # tiene sentido numerar — se deja en None para que la tabla sepa que
        # no hay que separar por grupo.
        grupo_id = numero_grupo if cantidad_grupos > 1 else None
        for equipo_a, equipo_b in round_robin.generar_partidos_grupo(g):
            partida = Partida(fase_id=fase.id, lado=LadoLlave.UNICA, ronda=1, grupo_numero=grupo_id)
            db.add(partida)
            db.flush()
            db.add(ParticipacionEnPartida(partida_id=partida.id, equipo_id=equipo_a, slot=0))
            db.add(ParticipacionEnPartida(partida_id=partida.id, equipo_id=equipo_b, slot=1))
            creadas.append(partida)

    fase.estado = EstadoFase.SORTEADA
    db.commit()
    for p in creadas:
        db.refresh(p)
    return creadas


def _persistir_ronda_suiza(
    db: Session, fase: Fase, equipos_seed: list[int], numero_ronda: int
) -> list[Partida]:
    if numero_ronda != 1:
        # Las rondas 2+ las genera el endpoint dedicado
        # (/siguiente-ronda-suiza), que ya conoce la tabla de puntos real —
        # este camino solo existe para la ronda 1, sembrada por posición.
        return []

    pares, equipo_bye = suizo.generar_ronda_1(equipos_seed)
    creadas: list[Partida] = []
    for equipo_a, equipo_b in pares:
        partida = Partida(fase_id=fase.id, lado=LadoLlave.UNICA, ronda=numero_ronda)
        db.add(partida)
        db.flush()
        db.add(ParticipacionEnPartida(partida_id=partida.id, equipo_id=equipo_a, slot=0))
        db.add(ParticipacionEnPartida(partida_id=partida.id, equipo_id=equipo_b, slot=1))
        creadas.append(partida)

    if equipo_bye is not None:
        partida_bye = Partida(
            fase_id=fase.id, lado=LadoLlave.UNICA, ronda=numero_ronda,
            estado=EstadoPartida.BYE,
        )
        db.add(partida_bye)
        db.flush()
        db.add(
            ParticipacionEnPartida(
                partida_id=partida_bye.id, equipo_id=equipo_bye, slot=0, es_ganador=True
            )
        )
        creadas.append(partida_bye)

    fase.estado = EstadoFase.SORTEADA
    db.commit()
    for p in creadas:
        db.refresh(p)
    return creadas


def avanzar_ganador(db: Session, partida: Partida) -> None:
    """Se llama cada vez que una partida queda resuelta (walkover, disputa,
    o el futuro reporte normal de resultado) para propagar el ganador — y,
    si corresponde, el perdedor — hacia la llave.
    """
    ganador = next((p for p in partida.participaciones if p.es_ganador), None)
    if ganador and partida.siguiente_partida_ganador_id:
        _colocar_en_slot(
            db, partida.siguiente_partida_ganador_id, partida.siguiente_slot_ganador, ganador.equipo_id
        )

    if partida.siguiente_partida_perdedor_id:
        perdedor = next((p for p in partida.participaciones if p.es_ganador is False), None)
        if perdedor:
            _colocar_en_slot(
                db,
                partida.siguiente_partida_perdedor_id,
                partida.siguiente_slot_perdedor,
                perdedor.equipo_id,
            )

    db.commit()


def _colocar_en_slot(db: Session, partida_id: int, slot: int, equipo_id: int) -> None:
    destino = db.get(Partida, partida_id)
    if any(p.equipo_id == equipo_id for p in destino.participaciones):
        return  # idempotencia: no duplicar si esto ya se aplicó antes

    db.add(ParticipacionEnPartida(partida_id=destino.id, equipo_id=equipo_id, slot=slot))
    db.flush()
    db.refresh(destino)
