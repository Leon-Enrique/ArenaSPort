"""Prueba de los tres afinamientos: privacidad de discord_id, endpoint de
resumen (Vista general), y filtro de partidas por estado (Resultados / A
continuacion).
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
    t = c.post("/api/torneos", json={"nombre": "Copa Pulido"}, headers=org).json()
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
        return r.json()["inscripcion"]["equipo"]["id"]

    A, B, C, D = inscribir("Alfa"), inscribir("Beta"), inscribir("Gamma"), inscribir("Delta")
    for iid in [i["id"] for i in c.get(f"/api/ediciones/{eid}/inscripciones").json()]:
        c.post(f"/api/ediciones/{eid}/inscripciones/{iid}/revisar", json={"estado": "aprobada"}, headers=org)

    db = SessionLocal()
    cap = {n: headers_capitan(db, f"cap_{n}") for n in ["Alfa", "Beta", "Gamma", "Delta"]}
    db.close()

    linea("PRIVACIDAD — discord_id oculto sin login, visible para el organizador")
    r_publico = c.get(f"/api/ediciones/{eid}/inscripciones")
    r_org = c.get(f"/api/ediciones/{eid}/inscripciones", headers=org)
    print("Sin login:", r_publico.json()[0]["jugadores"][0]["discord_id"])
    print("Con organizador:", r_org.json()[0]["jugadores"][0]["discord_id"])
    assert r_publico.json()[0]["jugadores"][0]["discord_id"] is None
    assert r_org.json()[0]["jugadores"][0]["discord_id"] is not None

    linea("RESUMEN DE EDICION — sin fases todavia")
    resumen_vacio = c.get(f"/api/ediciones/{eid}/resumen").json()
    print("Equipos aprobados:", resumen_vacio["equipos_aprobados"])
    print("Fases:", len(resumen_vacio["fases"]))
    print("Ultimos resultados:", len(resumen_vacio["ultimos_resultados"]))
    assert resumen_vacio["equipos_aprobados"] == 4
    assert resumen_vacio["fases"] == []

    fase = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 1, "nombre": "Grupo Unico", "modelo_competencia": "enfrentamiento_directo",
        "formato": "round_robin", "config": {"bo": 1},
    }, headers=org).json()
    fid = fase["id"]

    def jugar(equipo_a, equipo_b, cap_a, cap_b, mapas_a, mapas_b):
        p = c.post(f"/api/fases/{fid}/partidas", json={"equipo_ids": [equipo_a, equipo_b]}, headers=org).json()
        pid = p["id"]
        c.post(f"/api/fases/{fid}/partidas/{pid}/abrir-checkin", json={"minutos": 15}, headers=org)
        c.post(f"/api/fases/{fid}/partidas/{pid}/checkin", json={"equipo_id": equipo_a}, headers=cap_a)
        c.post(f"/api/fases/{fid}/partidas/{pid}/checkin", json={"equipo_id": equipo_b}, headers=cap_b)
        c.post(f"/api/fases/{fid}/partidas/{pid}/reportar", json={
            "equipo_id": equipo_a, "marcador_propio": mapas_a, "marcador_rival": mapas_b,
            "evidencia_url": "https://ejemplo.com/cap.png",
        }, headers=cap_a)
        c.post(f"/api/fases/{fid}/partidas/{pid}/confirmar", json={"equipo_id": equipo_b}, headers=cap_b)
        return pid

    jugar(A, B, cap["Alfa"], cap["Beta"], 1, 0)
    jugar(C, D, cap["Gamma"], cap["Delta"], 1, 0)
    # una partida sin resolver, para que aparezca en "proximas"
    c.post(f"/api/fases/{fid}/partidas", json={"equipo_ids": [A, C]}, headers=org)

    linea("RESUMEN DE EDICION — con partidas jugadas y pendientes")
    resumen = c.get(f"/api/ediciones/{eid}/resumen").json()
    print("Juego:", resumen["juego"])
    print(f"Ultimos resultados ({len(resumen['ultimos_resultados'])}):")
    for r in resumen["ultimos_resultados"]:
        print(f"  {r['equipo_a_nombre']} {r['mapas_a']}-{r['mapas_b']} {r['equipo_b_nombre']} "
              f"(fase: {r['fase_nombre']})")
    print(f"Proximas partidas ({len(resumen['proximas_partidas'])}):")
    for r in resumen["proximas_partidas"]:
        print(f"  {r['equipo_a_nombre']} vs {r['equipo_b_nombre']} estado={r['estado']}")
    assert len(resumen["ultimos_resultados"]) == 2
    assert len(resumen["proximas_partidas"]) == 1

    linea("FILTRO DE PARTIDAS POR ESTADO — resultados vs a continuacion")
    todas = c.get(f"/api/fases/{fid}/partidas").json()
    resultados = c.get(f"/api/fases/{fid}/partidas", params={"resueltas": "true"}).json()
    proximas = c.get(f"/api/fases/{fid}/partidas", params={"resueltas": "false"}).json()
    print(f"Todas: {len(todas)} | Resultados: {len(resultados)} | A continuacion: {len(proximas)}")
    assert len(resultados) == 2
    assert len(proximas) == 1
    assert all(p["estado"] in ("confirmada", "walkover") for p in resultados)
    assert all(p["estado"] == "programada" for p in proximas)

    filtro_confirmadas = c.get(f"/api/fases/{fid}/partidas", params={"estado": "confirmada"}).json()
    print(f"Filtro estado=confirmada: {len(filtro_confirmadas)}")
    assert len(filtro_confirmadas) == 2

print("\n" + "=" * 70)
print("TODAS LAS PRUEBAS DE PULIDO PASARON")
print("=" * 70)
