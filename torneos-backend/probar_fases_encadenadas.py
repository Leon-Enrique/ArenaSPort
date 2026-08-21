"""Prueba de encadenar fases: grupos -> playoffs con los clasificados de la
fase anterior, el patron real de Toornament ('Outgoing Participants').

Cubre: no se puede cerrar una fase con partidas sin resolver, cerrar una
fase que si termino, no se puede sortear desde una fase que no esta
cerrada, y el caso real completo: 4 grupos de 6 equipos, top 2 de cada uno
avanzan (8 en total) a una llave de eliminacion simple, verificando que los
8 clasificados son exactamente los primeros 2 de cada grupo.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.models import Partida
from probar_utils import headers_capitan, headers_organizador


def linea(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db)
    db.close()

    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")
    t = c.post("/api/torneos", json={"nombre": "Copa Fases Encadenadas"}, headers=org).json()
    e = c.post("/api/ediciones", json={
        "torneo_id": t["id"], "juego_id": mlbb["id"], "numero": 1, "nombre": "Ed Uno",
    }, headers=org).json()
    eid = e["id"]
    c.post(f"/api/ediciones/{eid}/estado", params={"estado": "inscripciones_abiertas"}, headers=org)

    def inscribir(nombre):
        r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
            "nombre_equipo": nombre,
            "jugadores": [
                {"identidad": {"nick": f"{nombre}{i}", "id_juego": str(hash(f'{nombre}{i}') % 10**8), "server": "2251"},
                 "es_suplente": None, "es_capitan": i == 0,
                 "discord_id": f"cap_{nombre}" if i == 0 else None}
                for i in range(5)
            ],
        })
        return r.json()["inscripcion"]["equipo"]["id"], r.json()["inscripcion"]["id"]

    # 24 equipos, 4 grupos de 6
    nombres = [f"E{i:02d}" for i in range(1, 25)]
    equipos = {}
    for n in nombres:
        eq_id, insc_id = inscribir(n)
        equipos[n] = eq_id
        c.post(f"/api/ediciones/{eid}/inscripciones/{insc_id}/revisar", json={"estado": "aprobada"}, headers=org)

    db = SessionLocal()
    cap = {n: headers_capitan(db, f"cap_{n}") for n in nombres}
    db.close()

    c.post(f"/api/ediciones/{eid}/inscripciones/sembrar-automatico", params={"semilla": 42}, headers=org)

    linea("FASE 1 — Grupos, 4 grupos de 6")
    fase_grupos = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 1, "nombre": "Fase de Grupos", "modelo_competencia": "enfrentamiento_directo",
        "formato": "round_robin", "config": {"bo": 1, "grupos": 4},
    }, headers=org).json()
    fg_id = fase_grupos["id"]

    r = c.post(f"/api/ediciones/{eid}/fases/{fg_id}/sortear", headers=org)
    partidas_grupos = r.json()
    print(f"Partidas de grupos: {len(partidas_grupos)} (esperado 4 grupos * C(6,2)=15 = 60)")
    assert len(partidas_grupos) == 60

    linea("NO SE PUEDE CERRAR CON PARTIDAS SIN RESOLVER")
    r = c.post(f"/api/ediciones/{eid}/fases/{fg_id}/cerrar", headers=org)
    print(f"HTTP {r.status_code}: {r.json()['detail'][:80]}...")
    assert r.status_code == 409

    linea("RESOLVER TODAS LAS PARTIDAS DE GRUPOS (via reporte real, no walkover)")
    for p in partidas_grupos:
        a = p["participaciones"][0]["equipo"]["id"]
        b = p["participaciones"][1]["equipo"]["id"]
        na = p["participaciones"][0]["equipo"]["nombre"]
        nb = p["participaciones"][1]["equipo"]["nombre"]
        pid = p["id"]
        # Gana siempre el de menor id (determinista, para poder predecir
        # despues quienes deberian ser los clasificados de cada grupo)
        ganador, na_g = (a, na) if a < b else (b, nb)
        perdedor = b if ganador == a else a

        c.post(f"/api/fases/{fg_id}/partidas/{pid}/abrir-checkin", json={"minutos": 15}, headers=org)
        c.post(f"/api/fases/{fg_id}/partidas/{pid}/checkin", json={"equipo_id": a}, headers=cap[na])
        c.post(f"/api/fases/{fg_id}/partidas/{pid}/checkin", json={"equipo_id": b}, headers=cap[nb])
        cap_ganador = cap[na] if ganador == a else cap[nb]
        cap_perdedor = cap[nb] if ganador == a else cap[na]
        c.post(f"/api/fases/{fg_id}/partidas/{pid}/reportar", json={
            "equipo_id": ganador, "marcador_propio": 1, "marcador_rival": 0,
            "evidencia_url": "https://ejemplo.com/cap.png",
        }, headers=cap_ganador)
        c.post(f"/api/fases/{fg_id}/partidas/{pid}/confirmar", json={"equipo_id": perdedor}, headers=cap_perdedor)
    print("Las 60 partidas de grupos resueltas.")

    linea("AHORA SI SE PUEDE CERRAR LA FASE")
    r = c.post(f"/api/ediciones/{eid}/fases/{fg_id}/cerrar", headers=org)
    print(f"HTTP {r.status_code}, estado de la fase: {r.json()['estado']}")
    assert r.status_code == 200
    assert r.json()["estado"] == "cerrada"

    r = c.post(f"/api/ediciones/{eid}/fases/{fg_id}/cerrar", headers=org)
    print(f"Cerrar de nuevo una fase ya cerrada -> HTTP {r.status_code}: {r.json()['detail']}")
    assert r.status_code == 409

    linea("VER LA TABLA FINAL DE CADA GRUPO")
    tabla = c.get(f"/api/ediciones/{eid}/fases/{fg_id}/tabla").json()
    clasificados_esperados = set()
    for grupo in tabla:
        top2 = grupo["filas"][:2]
        print(f"  Grupo {grupo['grupo']}: 1° {top2[0]['equipo_nombre']}, 2° {top2[1]['equipo_nombre']}")
        clasificados_esperados.add(top2[0]["equipo_id"])
        clasificados_esperados.add(top2[1]["equipo_id"])
    print(f"Total clasificados esperados: {len(clasificados_esperados)}")

    linea("FASE 2 — Playoffs, creada vacia (pendiente)")
    fase_playoffs = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 2, "nombre": "Playoffs", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_simple", "config": {"bo": 1},
    }, headers=org).json()
    fp_id = fase_playoffs["id"]

    linea("NO SE PUEDE SORTEAR DESDE UNA FASE QUE NO ESTA CERRADA")
    fase_falsa = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 3, "nombre": "Otra", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_simple",
    }, headers=org).json()
    r = c.post(f"/api/ediciones/{eid}/fases/{fp_id}/sortear-desde-fase-anterior", json={
        "fase_origen_id": fase_falsa["id"], "cupos_por_grupo": 2,
    }, headers=org)
    print(f"HTTP {r.status_code}: {r.json()['detail'][:70]}...")
    assert r.status_code == 422

    linea("SORTEAR PLAYOFFS DESDE LOS CLASIFICADOS DE LA FASE DE GRUPOS")
    r = c.post(f"/api/ediciones/{eid}/fases/{fp_id}/sortear-desde-fase-anterior", json={
        "fase_origen_id": fg_id, "cupos_por_grupo": 2,
    }, headers=org)
    print(f"HTTP {r.status_code}")
    partidas_playoffs = r.json()
    print(f"Partidas de playoffs generadas: {len(partidas_playoffs)} (esperado 8-1=7, llave de 8)")
    assert len(partidas_playoffs) == 7  # llave de 8: 4+2+1 = 7 partidas

    equipos_en_playoffs = set()
    for p in partidas_playoffs:
        for part in p["participaciones"]:
            equipos_en_playoffs.add(part["equipo"]["id"])
    print(f"Equipos que entraron a playoffs: {len(equipos_en_playoffs)}")
    print(f"Coincide exactamente con los clasificados esperados: {equipos_en_playoffs == clasificados_esperados}")
    assert equipos_en_playoffs == clasificados_esperados, \
        "Los equipos en playoffs deberian ser EXACTAMENTE los top 2 de cada grupo"

    ronda1_playoffs = [p for p in partidas_playoffs if p["ronda"] == 1]
    print(f"\nCruces de ronda 1 de playoffs:")
    for p in ronda1_playoffs:
        nombres_p = [pp["equipo"]["nombre"] for pp in p["participaciones"]]
        print(" ", nombres_p)

print("\n" + "=" * 70)
print("TODAS LAS PRUEBAS DE FASES ENCADENADAS PASARON")
print("=" * 70)
