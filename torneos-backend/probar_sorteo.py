"""Prueba end-to-end del sorteo de llaves, a traves de la API real.

Cubre: eliminacion simple con byes, eliminacion doble completa (llave alta +
baja + gran final) simulando TODOS los resultados via walkover hasta un
campeon, round robin con grupos, y ronda 1 de suizo. Con 45 equipos, el
tamano real del torneo de MLBB.
"""

import random
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.models import Partida
from probar_utils import headers_capitan, headers_organizador


def linea(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def crear_torneo_con_equipos(c, org, nombre_torneo, mlbb, cantidad):
    t = c.post("/api/torneos", json={"nombre": nombre_torneo}, headers=org).json()
    e = c.post("/api/ediciones", json={
        "torneo_id": t["id"], "juego_id": mlbb["id"], "numero": 1, "nombre": "Ed 1",
    }, headers=org).json()
    c.post(f"/api/ediciones/{e['id']}/estado", params={"estado": "inscripciones_abiertas"}, headers=org)

    ids_inscripcion = []
    for i in range(cantidad):
        nombre = f"Equipo{i:02d}"
        r = c.post(f"/api/ediciones/{e['id']}/inscripciones", json={
            "nombre_equipo": nombre,
            "jugadores": [
                {"identidad": {"nick": f"{nombre}_{j}", "id_juego": str(i * 10 + j), "server": "2251"},
                 "es_suplente": None, "es_capitan": j == 0,
                 "discord_id": f"cap_{nombre}" if j == 0 else None}
                for j in range(5)
            ],
        })
        ids_inscripcion.append(r.json()["inscripcion"]["id"])

    for iid in ids_inscripcion:
        c.post(f"/api/ediciones/{e['id']}/inscripciones/{iid}/revisar",
               json={"estado": "aprobada"}, headers=org)

    return e["id"]


def jugar_hasta_el_final(c, org, fase_id, semilla=7):
    """Resuelve TODAS las partidas pendientes por walkover, en orden, hasta
    que no quede ninguna partida programada. El organizador confirma el
    check-in de uno de los dos equipos (puede actuar en nombre de cualquiera)
    y deja vencer el plazo del otro, forzando un walkover con ganador.
    """
    rng = random.Random(semilla)
    vueltas = 0
    while True:
        vueltas += 1
        partidas = c.get(f"/api/fases/{fase_id}/partidas").json()
        pendientes = [
            p for p in partidas
            if p["estado"] == "programada" and len(p["participaciones"]) == 2
        ]
        if not pendientes:
            break
        if vueltas > 200:
            raise RuntimeError("Demasiadas vueltas, algo no esta convergiendo.")

        for p in pendientes:
            pid = p["id"]
            equipos = [part["equipo"]["id"] for part in p["participaciones"]]
            c.post(f"/api/fases/{fase_id}/partidas/{pid}/abrir-checkin",
                   json={"minutos": 15}, headers=org)

            ganador = rng.choice(equipos)
            c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin",
                   json={"equipo_id": ganador}, headers=org)

            db = SessionLocal()
            pp = db.get(Partida, pid)
            pp.checkin_cierra_at = datetime.now(UTC) - timedelta(seconds=1)
            db.commit()
            db.close()

            c.post(f"/api/fases/{fase_id}/partidas/{pid}/resolver-checkin", headers=org)

    return c.get(f"/api/fases/{fase_id}/partidas").json()


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db)
    db.close()

    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")

    # -----------------------------------------------------------------
    linea("ELIMINACION SIMPLE — 45 equipos (el tamano real del torneo)")
    eid = crear_torneo_con_equipos(c, org, "Copa 45 Simple", mlbb, 45)

    r = c.post(f"/api/ediciones/{eid}/inscripciones/sembrar-automatico", params={"semilla": 123})
    print(f"Sembrar sin login -> HTTP {r.status_code}")
    c.post(f"/api/ediciones/{eid}/inscripciones/sembrar-automatico", params={"semilla": 123}, headers=org)
    inscripciones = c.get(f"/api/ediciones/{eid}/inscripciones").json()
    print(f"{len(inscripciones)} equipos sembrados. Ejemplo:",
          {i["equipo"]["nombre"]: i["seed"] for i in inscripciones[:3]})

    fase = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 1, "nombre": "Llave Principal",
        "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_simple",
    }, headers=org).json()

    r = c.post(f"/api/ediciones/{eid}/fases/{fase['id']}/sortear", headers=org)
    print(f"Sorteo -> HTTP {r.status_code}, {len(r.json())} partidas creadas")

    todas = c.get(f"/api/fases/{fase['id']}/partidas").json()
    byes = [p for p in todas if p["estado"] == "bye"]
    programadas = [p for p in todas if p["estado"] == "programada"]
    print(f"Total: {len(todas)} | byes automaticos: {len(byes)} | "
          f"programadas ronda1: {len(programadas)}")

    finales = jugar_hasta_el_final(c, org, fase["id"])
    resueltas = [p for p in finales if p["estado"] in ("walkover", "bye")]
    print(f"Partidas resueltas: {len(resueltas)} de {len(finales)}")
    ultima_ronda = max(p["ronda"] for p in finales)
    final_match = next(p for p in finales if p["ronda"] == ultima_ronda)
    campeon = next(part["equipo"]["nombre"] for part in final_match["participaciones"] if part["es_ganador"])
    print(f"CAMPEON: {campeon}")
    assert len(resueltas) == len(finales), "Quedaron partidas sin resolver"

    # -----------------------------------------------------------------
    linea("ELIMINACION DOBLE — 45 equipos (llave alta + baja + gran final)")
    eid2 = crear_torneo_con_equipos(c, org, "Copa 45 Doble", mlbb, 45)
    c.post(f"/api/ediciones/{eid2}/inscripciones/sembrar-automatico", params={"semilla": 456}, headers=org)

    fase2 = c.post(f"/api/ediciones/{eid2}/fases", json={
        "orden": 1, "nombre": "Llave Doble",
        "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_doble",
    }, headers=org).json()

    r = c.post(f"/api/ediciones/{eid2}/fases/{fase2['id']}/sortear", headers=org)
    creadas = r.json()
    print(f"Sorteo -> HTTP {r.status_code}, {len(creadas)} partidas creadas")

    por_lado = {}
    for p in creadas:
        por_lado[p["lado"]] = por_lado.get(p["lado"], 0) + 1
    print("Distribucion por lado:", por_lado)

    finales2 = jugar_hasta_el_final(c, org, fase2["id"])
    byes2 = [p for p in finales2 if p["estado"] == "bye"]
    walkovers2 = [p for p in finales2 if p["estado"] == "walkover"]
    print(f"Total partidas: {len(finales2)} (WB 63 + LB 43 + gran final 1 = 107)")
    print(f"  byes automaticos: {len(byes2)}")
    print(f"  jugadas via walkover: {len(walkovers2)}")
    assert len(byes2) + len(walkovers2) == len(finales2), "Quedo alguna partida sin resolver"
    assert len(walkovers2) == 2 * 45 - 2, \
        f"Se esperaban {2*45-2} partidas realmente jugadas (2n-2), hubo {len(walkovers2)}"

    gran_final = next(p for p in finales2 if p["lado"] == "gran_final")
    print("Estado de la gran final:", gran_final["estado"])
    assert gran_final["estado"] in ("walkover", "bye", "confirmada"), "La gran final no se resolvio"
    campeon2 = next(
        part["equipo"]["nombre"] for part in gran_final["participaciones"] if part["es_ganador"]
    )
    print(f"CAMPEON (doble eliminacion): {campeon2}")

    sin_resolver = [p for p in finales2 if p["estado"] == "programada"]
    print(f"Partidas sin resolver al final: {len(sin_resolver)} (debe ser 0)")
    assert len(sin_resolver) == 0

    # -----------------------------------------------------------------
    linea("ROUND ROBIN CON GRUPOS — 24 equipos en 4 grupos")
    eid3 = crear_torneo_con_equipos(c, org, "Copa Grupos", mlbb, 24)
    c.post(f"/api/ediciones/{eid3}/inscripciones/sembrar-automatico", params={"semilla": 1}, headers=org)

    fase3 = c.post(f"/api/ediciones/{eid3}/fases", json={
        "orden": 1, "nombre": "Fase de Grupos",
        "modelo_competencia": "enfrentamiento_directo",
        "formato": "round_robin",
        "config": {"grupos": 4},
    }, headers=org).json()

    r = c.post(f"/api/ediciones/{eid3}/fases/{fase3['id']}/sortear", headers=org)
    creadas3 = r.json()
    print(f"Sorteo -> {len(creadas3)} partidas (esperado: 4 grupos * C(6,2)=15 = 60)")
    assert len(creadas3) == 60

    # -----------------------------------------------------------------
    linea("SUIZO — ronda 1 con 16 equipos")
    eid4 = crear_torneo_con_equipos(c, org, "Copa Suiza", mlbb, 16)
    c.post(f"/api/ediciones/{eid4}/inscripciones/sembrar-automatico", params={"semilla": 9}, headers=org)

    fase4 = c.post(f"/api/ediciones/{eid4}/fases", json={
        "orden": 1, "nombre": "Ronda Suiza",
        "modelo_competencia": "enfrentamiento_directo",
        "formato": "suizo",
    }, headers=org).json()

    r = c.post(f"/api/ediciones/{eid4}/fases/{fase4['id']}/sortear", headers=org)
    creadas4 = r.json()
    print(f"Ronda 1 suiza -> {len(creadas4)} partidas (esperado: 8)")
    assert len(creadas4) == 8

    # -----------------------------------------------------------------
    linea("VALIDACIONES DE ERROR")
    r = c.post(f"/api/ediciones/{eid4}/fases/{fase4['id']}/sortear", headers=org)
    print(f"Sortear una fase ya sorteada -> HTTP {r.status_code}: {r.json()['detail'][:60]}...")

    eid5 = crear_torneo_con_equipos(c, org, "Copa Sin Sembrar", mlbb, 8)
    fase5 = c.post(f"/api/ediciones/{eid5}/fases", json={
        "orden": 1, "nombre": "F1", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_simple",
    }, headers=org).json()
    r = c.post(f"/api/ediciones/{eid5}/fases/{fase5['id']}/sortear", headers=org)
    print(f"Sortear sin sembrar antes -> HTTP {r.status_code}: {r.json()['detail'][:70]}...")

print("\n" + "=" * 70)
print("TODAS LAS PRUEBAS PASARON")
print("=" * 70)
