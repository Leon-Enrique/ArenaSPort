"""Prueba de la correccion de resultado (organizador, sin disputa activa).

Cubre: correccion que NO cambia el ganador (solo marcador), correccion que
SI cambia el ganador antes de que se haya propagado (se corrige solo, sin
advertencia), correccion que cambia el ganador DESPUES de que ya avanzo a
la siguiente ronda (advertencia explicita, no se revierte en cascada solo),
validaciones (empate, equipos que no corresponden, motivo muy corto), y el
historial completo de una partida.
"""

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from probar_utils import headers_capitan, headers_organizador


def linea(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db)
    db.close()

    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")
    t = c.post("/api/torneos", json={"nombre": "Copa Correccion"}, headers=org).json()
    e = c.post("/api/ediciones", json={
        "torneo_id": t["id"], "juego_id": mlbb["id"], "numero": 1, "nombre": "Ed 1",
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
    cap = {"Alfa": headers_capitan(db, "cap_Alfa"), "Beta": headers_capitan(db, "cap_Beta"),
           "Gamma": headers_capitan(db, "cap_Gamma"), "Delta": headers_capitan(db, "cap_Delta")}
    db.close()

    def jugar(fase_id, equipo_a, equipo_b, cap_a, cap_b, mapas_a, mapas_b):
        p = c.post(f"/api/fases/{fase_id}/partidas", json={"equipo_ids": [equipo_a, equipo_b]}, headers=org).json()
        pid = p["id"]
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/abrir-checkin", json={"minutos": 15}, headers=org)
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin", json={"equipo_id": equipo_a}, headers=cap_a)
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin", json={"equipo_id": equipo_b}, headers=cap_b)
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/reportar", json={
            "equipo_id": equipo_a, "marcador_propio": mapas_a, "marcador_rival": mapas_b,
            "evidencia_url": "https://ejemplo.com/cap.png",
        }, headers=cap_a)
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/confirmar", json={"equipo_id": equipo_b}, headers=cap_b)
        return pid

    fase = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 1, "nombre": "Grupo Unico", "modelo_competencia": "enfrentamiento_directo",
        "formato": "round_robin", "config": {"bo": 3},
    }, headers=org).json()
    fid = fase["id"]

    linea("VALIDACIONES")
    pid_val = jugar(fid, A, B, cap["Alfa"], cap["Beta"], 2, 0)

    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/corregir-resultado", json={
        "resultados": [{"equipo_id": A, "mapas_ganados": 1}, {"equipo_id": B, "mapas_ganados": 1}],
        "motivo": "Revision de captura",
    }, headers=org)
    print(f"Corregir a empate -> HTTP {r.status_code}: {r.json()['detail']}")

    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/corregir-resultado", json={
        "resultados": [{"equipo_id": A, "mapas_ganados": 2}, {"equipo_id": B, "mapas_ganados": 1}],
        "motivo": "corto",
    }, headers=org)
    print(f"Motivo muy corto -> HTTP {r.status_code}: {r.json()['detail']}")

    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/corregir-resultado", json={
        "resultados": [{"equipo_id": A, "mapas_ganados": 2}, {"equipo_id": C, "mapas_ganados": 1}],
        "motivo": "Equipo que no jugo esta partida",
    }, headers=org)
    print(f"Equipo que no corresponde -> HTTP {r.status_code}: {r.json()['detail']}")

    linea("CORRECCION SIN CAMBIAR EL GANADOR (solo el marcador de mapas)")
    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/corregir-resultado", json={
        "resultados": [{"equipo_id": A, "mapas_ganados": 2}, {"equipo_id": B, "mapas_ganados": 1}],
        "motivo": "La captura original mostraba 2-0 pero el VOD confirma que fue 2-1.",
    }, headers=org)
    d = r.json()
    print("HTTP", r.status_code, "| advertencia:", d["advertencia"])
    for p in d["partida"]["participaciones"]:
        print(f"  {p['equipo']['id']}: {p['mapas_ganados']} mapas, ganador={p['es_ganador']}")
    assert d["advertencia"] is None
    assert d["reporte"]["es_correccion"] is True
    assert d["reporte"]["motivo"] is not None

    linea("HISTORIAL DE LA PARTIDA (reporte original + confirmacion + correccion)")
    historial = c.get(f"/api/fases/{fid}/partidas/{pid_val}/historial-resultado").json()
    print(f"{len(historial)} registros:")
    for h in historial:
        tipo = "CORRECCION" if h["es_correccion"] else "reporte normal"
        print(f"  [{tipo}] {h['marcador_propio']}-{h['marcador_rival']} estado={h['estado']} motivo={h['motivo']}")
    assert len(historial) == 2

    linea("CORRECCION QUE CAMBIA EL GANADOR — antes de que se propague (sin advertencia)")
    pid_c = jugar(fid, C, D, cap["Gamma"], cap["Delta"], 2, 0)
    r = c.post(f"/api/fases/{fid}/partidas/{pid_c}/corregir-resultado", json={
        "resultados": [{"equipo_id": C, "mapas_ganados": 1}, {"equipo_id": D, "mapas_ganados": 2}],
        "motivo": "Se revisaron los VODs: Delta gano el tercer mapa, no Gamma.",
    }, headers=org)
    d = r.json()
    print("HTTP", r.status_code, "| advertencia:", d["advertencia"])
    ganador = next(p for p in d["partida"]["participaciones"] if p["es_ganador"])
    print("Nuevo ganador:", ganador["equipo"]["nombre"])
    assert ganador["equipo"]["id"] == D
    assert d["advertencia"] is None

    linea("CORRECCION QUE CAMBIA EL GANADOR — DESPUES de propagarse a la llave (con advertencia)")
    fase_llave = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 2, "nombre": "Semifinal", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_simple", "config": {"bo": 1},
    }, headers=org).json()
    c.post(f"/api/ediciones/{eid}/inscripciones/sembrar-automatico", params={"semilla": 1}, headers=org)
    r = c.post(f"/api/ediciones/{eid}/fases/{fase_llave['id']}/sortear", headers=org)
    partidas_llave = r.json()
    ronda1 = [p for p in partidas_llave if p["ronda"] == 1]
    final = [p for p in partidas_llave if p["ronda"] == 2][0]

    p1 = ronda1[0]
    ea = p1["participaciones"][0]["equipo"]["id"]
    eb = p1["participaciones"][1]["equipo"]["id"]
    na = p1["participaciones"][0]["equipo"]["nombre"]
    nb = p1["participaciones"][1]["equipo"]["nombre"]

    db = SessionLocal()
    cap_a1 = headers_capitan(db, f"cap_{na}")
    cap_b1 = headers_capitan(db, f"cap_{nb}")
    db.close()

    pid_ronda1 = p1["id"]  # jugar LA PARTIDA REAL del bracket, no una manual nueva
    c.post(f"/api/fases/{fase_llave['id']}/partidas/{pid_ronda1}/abrir-checkin", json={"minutos": 15}, headers=org)
    c.post(f"/api/fases/{fase_llave['id']}/partidas/{pid_ronda1}/checkin", json={"equipo_id": ea}, headers=cap_a1)
    c.post(f"/api/fases/{fase_llave['id']}/partidas/{pid_ronda1}/checkin", json={"equipo_id": eb}, headers=cap_b1)
    c.post(f"/api/fases/{fase_llave['id']}/partidas/{pid_ronda1}/reportar", json={
        "equipo_id": ea, "marcador_propio": 1, "marcador_rival": 0,
        "evidencia_url": "https://ejemplo.com/cap.png",
    }, headers=cap_a1)
    c.post(f"/api/fases/{fase_llave['id']}/partidas/{pid_ronda1}/confirmar", json={"equipo_id": eb}, headers=cap_b1)

    final_antes = c.get(f"/api/fases/{fase_llave['id']}/partidas/{final['id']}").json()
    print(f"Antes de corregir, la final tiene {len(final_antes['participaciones'])} participacion(es): "
          f"{[p['equipo']['nombre'] for p in final_antes['participaciones']]}")

    r = c.post(f"/api/fases/{fase_llave['id']}/partidas/{pid_ronda1}/corregir-resultado", json={
        "resultados": [{"equipo_id": ea, "mapas_ganados": 0}, {"equipo_id": eb, "mapas_ganados": 1}],
        "motivo": "El resultado se cargo al reves por error de tipeo del capitan.",
    }, headers=org)
    d = r.json()
    print("HTTP", r.status_code)
    print("ADVERTENCIA:", d["advertencia"])
    assert d["advertencia"] is not None, "Deberia advertir que la final ya tenia al ganador anterior"

    final_despues = c.get(f"/api/fases/{fase_llave['id']}/partidas/{final['id']}").json()
    print(f"Despues de corregir, la final SIGUE teniendo (a proposito, no se toca solo): "
          f"{[p['equipo']['nombre'] for p in final_despues['participaciones']]}")
    print("-> el organizador tiene que ir a la final a mano y corregir quien corresponde")

print("\n" + "=" * 70)
print("TODAS LAS PRUEBAS DE CORRECCION PASARON")
print("=" * 70)
