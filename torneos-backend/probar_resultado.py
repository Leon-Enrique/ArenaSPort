"""Prueba del reporte de resultado con doble confirmacion.

Cubre: reportar+confirmar (camino feliz), reportar+impugnar+resolver via
disputa, auto-confirmacion por vencimiento (con y sin evidencia), y
validaciones de marcador (empate, insuficiente, excede BO). Termina
verificando que un resultado CONFIRMADO DE VERDAD (no walkover) avanza
la llave igual de bien.
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.models import ReporteResultado
from probar_utils import headers_capitan, headers_organizador


def linea(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def vencer_reporte(partida_id: int) -> None:
    db = SessionLocal()
    r = (
        db.query(ReporteResultado)
        .filter(ReporteResultado.partida_id == partida_id, ReporteResultado.estado == "pendiente")
        .first()
    )
    r.vencimiento = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    db.close()


def poner_en_curso(c, org, cap_a, cap_b, fase_id, equipo_a, equipo_b):
    """Atajo: crea partida y la lleva a en_curso via checkin normal."""
    p = c.post(f"/api/fases/{fase_id}/partidas", json={"equipo_ids": [equipo_a, equipo_b]}, headers=org).json()
    pid = p["id"]
    c.post(f"/api/fases/{fase_id}/partidas/{pid}/abrir-checkin", json={"minutos": 15}, headers=org)
    c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin", json={"equipo_id": equipo_a}, headers=cap_a)
    c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin", json={"equipo_id": equipo_b}, headers=cap_b)
    return pid


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db)
    db.close()

    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")
    t = c.post("/api/torneos", json={"nombre": "Copa Resultados"}, headers=org).json()
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

    A = inscribir("Alfa")
    B = inscribir("Beta")
    C = inscribir("Gamma")
    D = inscribir("Delta")
    print(f"Equipos: Alfa={A} Beta={B} Gamma={C} Delta={D}")

    for iid in [i["id"] for i in c.get(f"/api/ediciones/{eid}/inscripciones").json()]:
        c.post(f"/api/ediciones/{eid}/inscripciones/{iid}/revisar", json={"estado": "aprobada"}, headers=org)

    db = SessionLocal()
    cap_a = headers_capitan(db, "cap_Alfa")
    cap_b = headers_capitan(db, "cap_Beta")
    cap_c = headers_capitan(db, "cap_Gamma")
    cap_d = headers_capitan(db, "cap_Delta")
    db.close()

    fase = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 1, "nombre": "Grupo Unico",
        "modelo_competencia": "enfrentamiento_directo",
        "formato": "round_robin",
        "config": {"bo": 3},
    }, headers=org).json()
    fid = fase["id"]

    linea("VALIDACIONES DE MARCADOR (BO3)")
    pid_val = poner_en_curso(c, org, cap_a, cap_b, fid, A, B)

    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/reportar", json={
        "equipo_id": A, "marcador_propio": 1, "marcador_rival": 1,
    }, headers=cap_a)
    print(f"Empate 1-1 -> HTTP {r.status_code}: {r.json()['detail']}")

    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/reportar", json={
        "equipo_id": A, "marcador_propio": 1, "marcador_rival": 0,
    }, headers=cap_a)
    print(f"1-0 en BO3 (no alcanza) -> HTTP {r.status_code}: {r.json()['detail']}")

    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/reportar", json={
        "equipo_id": A, "marcador_propio": 2, "marcador_rival": 2,
    }, headers=cap_a)
    print(f"2-2 en BO3 (suma > 3) -> HTTP {r.status_code}: {r.json()['detail']}")

    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/reportar", json={
        "equipo_id": B, "marcador_propio": 2, "marcador_rival": 1,
    }, headers=cap_a)
    print(f"Beta reporta pero firma cap_a (suplanta al rival) -> HTTP {r.status_code}: "
          f"{r.json()['detail'][:60]}...")

    linea("CAMINO FELIZ — reportar y confirmar")
    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/reportar", json={
        "equipo_id": A, "marcador_propio": 2, "marcador_rival": 1,
        "evidencia_url": "https://ejemplo.com/cap1.png",
    }, headers=cap_a)
    print("Reporte:", r.status_code, r.json()["estado"])

    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/confirmar", json={"equipo_id": A}, headers=cap_a)
    print(f"Confirmar el propio reporte -> HTTP {r.status_code}: {r.json()['detail']}")

    r = c.post(f"/api/fases/{fid}/partidas/{pid_val}/confirmar", json={"equipo_id": B}, headers=cap_b)
    d = r.json()
    print("Confirmado por el rival -> estado:", d["estado"])
    for p in d["participaciones"]:
        print(f"  {p['equipo']['nombre']}: {p['mapas_ganados']} mapas, ganador={p['es_ganador']}")

    linea("IMPUGNACION — el rival no esta de acuerdo")
    pid_imp = poner_en_curso(c, org, cap_c, cap_d, fid, C, D)
    c.post(f"/api/fases/{fid}/partidas/{pid_imp}/reportar", json={
        "equipo_id": C, "marcador_propio": 2, "marcador_rival": 0,
    }, headers=cap_c)
    r = c.post(f"/api/fases/{fid}/partidas/{pid_imp}/impugnar", json={
        "equipo_id": D, "motivo": "El marcador real fue 2-1, no 2-0.",
    }, headers=cap_d)
    disputa = r.json()
    print("Disputa creada:", disputa["id"], "| motivo:", disputa["motivo"])

    p_actual = c.get(f"/api/fases/{fid}/partidas/{pid_imp}").json()
    print("Estado de la partida tras impugnar:", p_actual["estado"])

    r = c.post(f"/api/disputas/{disputa['id']}/resolver", json={
        "resolucion": "Se revisaron las capturas de ambos: el marcador correcto es 2-1.",
        "accion": "confirmar_resultado",
        "resultados": [
            {"equipo_id": C, "mapas_ganados": 2},
            {"equipo_id": D, "mapas_ganados": 1},
        ],
    }, headers=org)
    print("Disputa resuelta con confirmar_resultado -> HTTP", r.status_code)

    p_final = c.get(f"/api/fases/{fid}/partidas/{pid_imp}").json()
    print("Estado final de la partida:", p_final["estado"])
    for p in p_final["participaciones"]:
        print(f"  {p['equipo']['nombre']}: {p['mapas_ganados']} mapas, ganador={p['es_ganador']}")
    assert p_final["estado"] == "confirmada"

    linea("AUTO-CONFIRMACION — con evidencia, tras vencer el plazo")
    pid_auto = poner_en_curso(c, org, cap_a, cap_c, fid, A, C)
    c.post(f"/api/fases/{fid}/partidas/{pid_auto}/reportar", json={
        "equipo_id": A, "marcador_propio": 2, "marcador_rival": 0,
        "evidencia_url": "https://ejemplo.com/cap2.png",
        "horas_para_confirmar": 3,
    }, headers=cap_a)
    r = c.post(f"/api/fases/{fid}/partidas/{pid_auto}/resolver-reporte-vencido", headers=org)
    print(f"Intentar auto-confirmar antes de tiempo -> HTTP {r.status_code}: {r.json()['detail']}")

    vencer_reporte(pid_auto)
    r = c.post(f"/api/fases/{fid}/partidas/{pid_auto}/resolver-reporte-vencido", headers=org)
    print("Auto-confirmado tras vencer ->", r.json()["estado"])
    assert r.json()["estado"] == "confirmada"

    linea("SIN EVIDENCIA — no se puede auto-confirmar, queda trabado a proposito")
    pid_sin_ev = poner_en_curso(c, org, cap_b, cap_d, fid, B, D)
    c.post(f"/api/fases/{fid}/partidas/{pid_sin_ev}/reportar", json={
        "equipo_id": B, "marcador_propio": 2, "marcador_rival": 0,
    }, headers=cap_b)
    vencer_reporte(pid_sin_ev)
    r = c.post(f"/api/fases/{fid}/partidas/{pid_sin_ev}/resolver-reporte-vencido", headers=org)
    print(f"Auto-confirmar sin evidencia -> HTTP {r.status_code}: {r.json()['detail'][:70]}...")
    assert r.status_code == 409

    linea("UN RESULTADO REAL AVANZA LA LLAVE (no solo walkover)")
    fase_llave = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 2, "nombre": "Semifinal", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_simple", "config": {"bo": 1},
    }, headers=org).json()
    c.post(f"/api/ediciones/{eid}/inscripciones/sembrar-automatico", params={"semilla": 1}, headers=org)
    ins = c.get(f"/api/ediciones/{eid}/inscripciones").json()
    equipos_ordenados = [i["equipo"]["id"] for i in sorted(ins, key=lambda i: i["seed"])]
    print("Orden de siembra:", equipos_ordenados)

    r = c.post(f"/api/ediciones/{eid}/fases/{fase_llave['id']}/sortear", headers=org)
    partidas_llave = r.json()
    print(f"Llave de 4 equipos sorteada: {len(partidas_llave)} partidas")

    ronda1 = [p for p in partidas_llave if p["ronda"] == 1]
    final = [p for p in partidas_llave if p["ronda"] == 2][0]
    print("Final (todavia sin equipos, esperando ganadores):",
          len(final["participaciones"]), "participaciones")

    p1 = ronda1[0]
    equipo_a1 = p1["participaciones"][0]["equipo"]["id"]
    equipo_b1 = p1["participaciones"][1]["equipo"]["id"]
    nombre_a1 = p1["participaciones"][0]["equipo"]["nombre"]
    nombre_b1 = p1["participaciones"][1]["equipo"]["nombre"]

    db = SessionLocal()
    cap_a1 = headers_capitan(db, f"cap_{nombre_a1}")
    cap_b1 = headers_capitan(db, f"cap_{nombre_b1}")
    db.close()

    c.post(f"/api/fases/{fase_llave['id']}/partidas/{p1['id']}/abrir-checkin", json={"minutos": 15}, headers=org)
    c.post(f"/api/fases/{fase_llave['id']}/partidas/{p1['id']}/checkin", json={"equipo_id": equipo_a1}, headers=cap_a1)
    c.post(f"/api/fases/{fase_llave['id']}/partidas/{p1['id']}/checkin", json={"equipo_id": equipo_b1}, headers=cap_b1)
    c.post(f"/api/fases/{fase_llave['id']}/partidas/{p1['id']}/reportar", json={
        "equipo_id": equipo_a1, "marcador_propio": 1, "marcador_rival": 0,
        "evidencia_url": "https://ejemplo.com/cap3.png",
    }, headers=cap_a1)
    r = c.post(f"/api/fases/{fase_llave['id']}/partidas/{p1['id']}/confirmar",
               json={"equipo_id": equipo_b1}, headers=cap_b1)
    print("Partida de ronda 1 confirmada:", r.json()["estado"])

    final_actualizada = c.get(f"/api/fases/{fase_llave['id']}/partidas/{final['id']}").json()
    print("Final ahora tiene", len(final_actualizada["participaciones"]), "participacion(es)")
    nombres = [p["equipo"]["nombre"] for p in final_actualizada["participaciones"]]
    print("  Equipo que avanzo:", nombres)
    assert len(final_actualizada["participaciones"]) == 1, \
        "El ganador de un resultado CONFIRMADO (no walkover) deberia haber avanzado a la final"

print("\n" + "=" * 70)
print("TODAS LAS PRUEBAS DE RESULTADO PASARON")
print("=" * 70)
