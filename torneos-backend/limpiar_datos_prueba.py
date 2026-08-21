"""Borra los torneos de PRUEBA/QA que quedaron de verificar las Fases A/B/C
a mano (Copa 45 Simple, Debug Torneo x2, Copa QA *), dejando intactos los
torneos de demo reales (Copa Elite, Liga Doble Impacto, Copa de Grupos,
Mundial Suizo) y el torneo real del usuario (Copa Santa Cruz MLBB).

Ejecutar: python limpiar_datos_prueba.py
"""

from sqlalchemy import text

from app.db.database import SessionLocal

TORNEO_IDS_A_BORRAR = [2, 3, 4, 5, 6]

db = SessionLocal()
try:
    torneo_in_inicial = ",".join(map(str, TORNEO_IDS_A_BORRAR))
    edicion_ids = db.execute(
        text(f"SELECT id FROM ediciones WHERE torneo_id IN ({torneo_in_inicial})")
    ).scalars().all()
    print("Ediciones a borrar:", edicion_ids)

    if edicion_ids:
        ed_in = ",".join(map(str, edicion_ids))

        fase_ids = db.execute(text(f"SELECT id FROM fases WHERE edicion_id IN ({ed_in})")).scalars().all()
        fase_in = ",".join(map(str, fase_ids)) or "-1"

        partida_ids = db.execute(text(f"SELECT id FROM partidas WHERE fase_id IN ({fase_in})")).scalars().all()
        partida_in = ",".join(map(str, partida_ids)) or "-1"

        inscripcion_ids = db.execute(text(f"SELECT id FROM inscripciones WHERE edicion_id IN ({ed_in})")).scalars().all()
        insc_in = ",".join(map(str, inscripcion_ids)) or "-1"

        equipo_ids = db.execute(text(f"SELECT equipo_id FROM inscripciones WHERE edicion_id IN ({ed_in})")).scalars().all()
        equipo_in = ",".join(map(str, equipo_ids)) or "-1"

        db.execute(text(f"DELETE FROM disputas WHERE partida_id IN ({partida_in})"))
        db.execute(text(f"DELETE FROM reportes_resultado WHERE partida_id IN ({partida_in})"))
        db.execute(text(f"DELETE FROM participaciones_partida WHERE partida_id IN ({partida_in})"))
        db.execute(text(f"DELETE FROM partidas WHERE id IN ({partida_in})"))
        db.execute(text(f"DELETE FROM fases WHERE id IN ({fase_in})"))
        db.execute(text(f"DELETE FROM jugadores WHERE inscripcion_id IN ({insc_in})"))
        db.execute(text(f"DELETE FROM inscripciones WHERE id IN ({insc_in})"))
        db.execute(text(f"DELETE FROM equipos WHERE id IN ({equipo_in})"))
        db.execute(text(f"DELETE FROM ediciones WHERE id IN ({ed_in})"))

    torneo_in = ",".join(map(str, TORNEO_IDS_A_BORRAR))
    db.execute(text(f"DELETE FROM torneos WHERE id IN ({torneo_in})"))

    db.commit()
    print("Listo. Torneos de prueba eliminados.")
finally:
    db.close()
