"""Prueba del escenario real de Leon: 40 equipos -> 8 grupos de 5 -> top 2
avanzan (16) -> eliminacion simple, solo ronda 1 (16->8 ganadores) -> esos
8 arrancan una llave de eliminacion DOBLE (alta+baja) nueva, sin necesidad
de que el resto de la llave simple original (rondas 2, 3, 4) se juegue ni
se cierre jamas.
"""

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from probar_utils import headers_capitan, headers_organizador


def linea(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def jugar_partida(c, fase_id, p, cap, org, bo=1):
    a, b = p["participaciones"][0]["equipo"]["id"], p["participaciones"][1]["equipo"]["id"]
    na, nb = p["participaciones"][0]["equipo"]["nombre"], p["participaciones"][1]["equipo"]["nombre"]
    pid = p["id"]
    ganador, perdedor = (a, b) if a < b else (b, a)  # determinista: gana el de menor id
    mapas_para_ganar = bo // 2 + 1  # el minimo valido para validar_marcador
    r0 = c.post(f"/api/fases/{fase_id}/partidas/{pid}/abrir-checkin", json={"minutos": 15}, headers=org)
    assert r0.status_code == 200, r0.json()
    cg = cap[na] if ganador == a else cap[nb]
    cp = cap[nb] if ganador == a else cap[na]
    r1 = c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin", json={"equipo_id": a}, headers=cap[na])
    assert r1.status_code == 200, r1.json()
    r2 = c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin", json={"equipo_id": b}, headers=cap[nb])
    assert r2.status_code == 200, r2.json()
    r3 = c.post(f"/api/fases/{fase_id}/partidas/{pid}/reportar", json={
        "equipo_id": ganador, "marcador_propio": mapas_para_ganar, "marcador_rival": 0,
        "evidencia_url": "https://ejemplo.com/cap.png",
    }, headers=cg)
    assert r3.status_code == 200, r3.json()
    r4 = c.post(f"/api/fases/{fase_id}/partidas/{pid}/confirmar", json={"equipo_id": perdedor}, headers=cp)
    assert r4.status_code == 200, r4.json()


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db)
    db.close()

    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")
    t = c.post("/api/torneos", json={"nombre": "Copa 40 Equipos"}, headers=org).json()
    e = c.post("/api/ediciones", json={
        "torneo_id": t["id"], "juego_id": mlbb["id"], "numero": 1, "nombre": "Edicion Real",
    }, headers=org).json()
    eid = e["id"]
    c.post(f"/api/ediciones/{eid}/estado", params={"estado": "inscripciones_abiertas"}, headers=org)

    def inscribir(nombre):
        r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
            "nombre_equipo": nombre,
            "jugadores": [
                {"identidad": {"nick": f"{nombre}{i}", "id_juego": str(hash(f"{nombre}{i}") % 10**8), "server": "2251"},
                 "es_suplente": None, "es_capitan": i == 0, "discord_id": f"cap_{nombre}" if i == 0 else None}
                for i in range(5)
            ],
        })
        return r.json()["inscripcion"]["equipo"]["id"], r.json()["inscripcion"]["id"]

    nombres = [f"E{i:02d}" for i in range(1, 41)]  # 40 equipos
    cap = {}
    for n in nombres:
        _, insc_id = inscribir(n)
        c.post(f"/api/ediciones/{eid}/inscripciones/{insc_id}/revisar", json={"estado": "aprobada"}, headers=org)
    db = SessionLocal()
    for n in nombres:
        cap[n] = headers_capitan(db, f"cap_{n}")
    db.close()
    c.post(f"/api/ediciones/{eid}/inscripciones/sembrar-automatico", params={"semilla": 5}, headers=org)

    # -----------------------------------------------------------------
    linea("FASE 1 — 8 grupos de 5 (40 equipos)")
    fase1 = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 1, "nombre": "Fase de Grupos", "modelo_competencia": "enfrentamiento_directo",
        "formato": "round_robin", "config": {"bo": 1, "grupos": 8},
    }, headers=org).json()
    partidas1 = c.post(f"/api/ediciones/{eid}/fases/{fase1['id']}/sortear", headers=org).json()
    print(f"Partidas de grupos: {len(partidas1)} (esperado 8 grupos * C(5,2)=10 = 80)")
    assert len(partidas1) == 80

    for p in partidas1:
        jugar_partida(c, fase1["id"], p, cap, org, bo=1)
    print("Las 80 partidas de grupos resueltas.")

    r_cerrar = c.post(f"/api/ediciones/{eid}/fases/{fase1['id']}/cerrar", headers=org)
    print(f"Cerrar fase de grupos -> HTTP {r_cerrar.status_code}: {r_cerrar.json()}")
    assert r_cerrar.status_code == 200, "La fase de grupos no se cerro de verdad"

    # -----------------------------------------------------------------
    linea("FASE 2 — Eliminacion simple con los 16 clasificados (top 2 de cada grupo)")
    fase2 = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 2, "nombre": "Ronda de 16", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_simple", "config": {"bo": 3},
    }, headers=org).json()

    r = c.post(f"/api/ediciones/{eid}/fases/{fase2['id']}/sortear-desde-fase-anterior", json={
        "fase_origen_id": fase1["id"], "cupos_por_grupo": 2,
    }, headers=org)
    partidas2 = r.json()
    print(f"HTTP {r.status_code}, respuesta: {r.json()}"); print(f"partidas generadas: {len(partidas2)} "
          f"(esperado 16-1=15: 8 ronda1 + 4 ronda2 + 2 ronda3 + 1 final)")
    assert len(partidas2) == 15

    ronda1_fase2 = [p for p in partidas2 if p["ronda"] == 1]
    print(f"Partidas de ronda 1 (16 -> 8): {len(ronda1_fase2)}")
    assert len(ronda1_fase2) == 8

    linea("SOLO SE JUEGA LA RONDA 1 de la Fase 2 (16 -> 8) — el resto queda sin jugar")
    for p in ronda1_fase2:
        jugar_partida(c, fase2["id"], p, cap, org, bo=3)
    print("Las 8 partidas de ronda 1 resueltas. Rondas 2, 3 y la final de esta fase")
    print("quedan sin jugar A PROPOSITO — no hace falta tocarlas nunca mas.")

    linea("INTENTAR SACAR CLASIFICADOS DE UNA RONDA SIN RESOLVER -> falla claro")
    fase3_falsa = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 99, "nombre": "Prueba", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_doble",
    }, headers=org).json()
    r = c.post(f"/api/ediciones/{eid}/fases/{fase3_falsa['id']}/sortear-desde-fase-anterior", json={
        "fase_origen_id": fase2["id"], "ronda_origen": 2,  # ronda 2 no se jugo
    }, headers=org)
    print(f"HTTP {r.status_code}: {r.json()['detail'][:80]}...")
    assert r.status_code == 409

    linea("FASE 3 — Eliminacion DOBLE (alta+baja) con los 8 ganadores de la ronda 1 de Fase 2")
    fase3 = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 3, "nombre": "Cuartos en adelante — Doble Eliminacion",
        "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_doble", "config": {"bo": 3},
    }, headers=org).json()

    r = c.post(f"/api/ediciones/{eid}/fases/{fase3['id']}/sortear-desde-fase-anterior", json={
        "fase_origen_id": fase2["id"], "ronda_origen": 1,
    }, headers=org)
    print(f"HTTP {r.status_code}")
    partidas3 = r.json()
    print(f"Partidas generadas en la llave doble: {len(partidas3)} (esperado 2*8-2=14)")
    assert len(partidas3) == 14

    por_lado = {}
    equipos_en_fase3 = set()
    for p in partidas3:
        por_lado[p["lado"]] = por_lado.get(p["lado"], 0) + 1
        for part in p["participaciones"]:
            equipos_en_fase3.add(part["equipo"]["id"])
    print("Distribucion por lado:", por_lado)
    print(f"Equipos en la fase 3: {len(equipos_en_fase3)}")
    assert por_lado.get("alta") and por_lado.get("baja") and por_lado.get("gran_final")
    assert len(equipos_en_fase3) == 8

    # Verificar que son EXACTAMENTE los ganadores de la ronda 1 de fase 2
    ganadores_ronda1_fase2 = set()
    for p in ronda1_fase2:
        detalle = c.get(f"/api/fases/{fase2['id']}/partidas/{p['id']}").json()
        ganador = next(part["equipo"]["id"] for part in detalle["participaciones"] if part["es_ganador"])
        ganadores_ronda1_fase2.add(ganador)

    print(f"\nCoinciden EXACTAMENTE los 8 ganadores de ronda 1 con los 8 de la llave doble: "
          f"{equipos_en_fase3 == ganadores_ronda1_fase2}")
    assert equipos_en_fase3 == ganadores_ronda1_fase2

print("\n" + "=" * 70)
print("CADENA COMPLETA FUNCIONA: 40 EQUIPOS -> GRUPOS -> RONDA DE 16 -> DOBLE ELIMINACION")
print("=" * 70)
