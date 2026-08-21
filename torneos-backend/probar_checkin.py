"""Prueba manual de check-in y disputas. Ejecutar: python probar_checkin.py"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.models import Partida
from probar_utils import headers_capitan, headers_organizador


def linea(titulo):
    print(f"\n{'=' * 70}\n{titulo}\n{'=' * 70}")


def vencer_checkin(partida_id: int) -> None:
    """Simula que ya pasó el tiempo de la ventana (lo haría un cron real)."""
    db = SessionLocal()
    p = db.get(Partida, partida_id)
    p.checkin_cierra_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    db.close()


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db)
    db.close()

    linea("SETUP")
    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")
    t = c.post("/api/torneos", json={"nombre": "Copa Checkin"}, headers=org).json()
    e = c.post("/api/ediciones", json={
        "torneo_id": t["id"], "juego_id": mlbb["id"], "numero": 1, "nombre": "Ed 1",
    }, headers=org).json()
    c.post(f"/api/ediciones/{e['id']}/estado", params={"estado": "inscripciones_abiertas"}, headers=org)

    # cada equipo tiene su capitan con un discord_id predecible: cap_<Nombre>
    def inscribir(nombre):
        r = c.post(f"/api/ediciones/{e['id']}/inscripciones", json={
            "nombre_equipo": nombre,
            "jugadores": [
                {"identidad": {"nick": f"{nombre}{i}", "id_juego": str(hash(f'{nombre}{i}') % 10**8), "server": "2251"},
                 "es_suplente": None, "es_capitan": i == 0,
                 "discord_id": f"cap_{nombre}" if i == 0 else None}
                for i in range(5)
            ],
        })
        equipo_id = r.json()["inscripcion"]["equipo"]["id"]
        return equipo_id

    equipo_a = inscribir("Halcones")
    equipo_b = inscribir("Serpientes")
    equipo_c = inscribir("Lobos")
    equipo_d = inscribir("Aguilas")
    print(f"Equipos: Halcones={equipo_a} Serpientes={equipo_b} Lobos={equipo_c} Aguilas={equipo_d}")

    db = SessionLocal()
    cap_a = headers_capitan(db, "cap_Halcones")
    cap_b = headers_capitan(db, "cap_Serpientes")
    cap_c = headers_capitan(db, "cap_Lobos")
    cap_d = headers_capitan(db, "cap_Aguilas")
    db.close()

    fase = c.post(f"/api/ediciones/{e['id']}/fases", json={
        "orden": 1, "nombre": "Grupo A",
        "modelo_competencia": "enfrentamiento_directo",
        "formato": "round_robin",
    }, headers=org).json()
    fid = fase["id"]
    print("Fase creada:", fase["nombre"], "modelo:", fase["modelo_competencia"])

    # ---------------------------------------------------------------
    linea("ESCENARIO 1 — Check-in exitoso, arranca la partida sola")
    p1 = c.post(f"/api/fases/{fid}/partidas", json={
        "equipo_ids": [equipo_a, equipo_b],
    }, headers=org).json()
    pid1 = p1["id"]
    print("Partida creada, estado:", p1["estado"])

    r = c.post(f"/api/fases/{fid}/partidas/{pid1}/checkin", json={"equipo_id": equipo_a})
    print(f"Checkin sin login -> HTTP {r.status_code}: {r.json()['detail']}")

    c.post(f"/api/fases/{fid}/partidas/{pid1}/abrir-checkin", json={"minutos": 15}, headers=org)
    r = c.post(f"/api/fases/{fid}/partidas/{pid1}/checkin", json={"equipo_id": equipo_a}, headers=cap_a)
    print("Halcones confirma -> estado:", r.json()["estado"])

    r = c.post(f"/api/fases/{fid}/partidas/{pid1}/checkin", json={"equipo_id": equipo_a}, headers=cap_b)
    print(f"Serpientes intenta confirmar POR Halcones -> HTTP {r.status_code}: {r.json()['detail'][:60]}...")

    r = c.post(f"/api/fases/{fid}/partidas/{pid1}/checkin", json={"equipo_id": equipo_b}, headers=cap_b)
    print("Serpientes confirma -> estado:", r.json()["estado"], "(esperado: en_curso)")

    r = c.post(f"/api/fases/{fid}/partidas/{pid1}/checkin", json={"equipo_id": equipo_a}, headers=cap_a)
    print(f"Doble check-in del mismo equipo -> HTTP {r.status_code}: {r.json()['detail']}")

    # ---------------------------------------------------------------
    linea("ESCENARIO 2 — Un equipo no aparece: walkover automatico")
    p2 = c.post(f"/api/fases/{fid}/partidas", json={
        "equipo_ids": [equipo_c, equipo_d],
    }, headers=org).json()
    pid2 = p2["id"]

    c.post(f"/api/fases/{fid}/partidas/{pid2}/abrir-checkin", json={"minutos": 15}, headers=org)
    r = c.post(f"/api/fases/{fid}/partidas/{pid2}/checkin", json={"equipo_id": equipo_c}, headers=cap_c)
    print("Solo Lobos confirma (dentro de la ventana) -> estado:", r.json()["estado"])

    r = c.post(f"/api/fases/{fid}/partidas/{pid2}/resolver-checkin", headers=org)
    print(f"Organizador intenta resolver antes de tiempo -> HTTP {r.status_code}: {r.json()['detail']}")

    vencer_checkin(pid2)
    r = c.post(f"/api/fases/{fid}/partidas/{pid2}/resolver-checkin", headers=org)
    d = r.json()
    print("Organizador resuelve el checkin ya vencido -> estado:", d["estado"])
    for part in d["participaciones"]:
        print(f"  equipo {part['equipo']['id']} ({part['equipo']['nombre']}): "
              f"es_ganador={part['es_ganador']}")

    # ---------------------------------------------------------------
    linea("ESCENARIO 3 — Nadie confirma: vuelve a programada")
    p3 = c.post(f"/api/fases/{fid}/partidas", json={
        "equipo_ids": [equipo_a, equipo_c],
    }, headers=org).json()
    pid3 = p3["id"]
    c.post(f"/api/fases/{fid}/partidas/{pid3}/abrir-checkin", json={"minutos": 15}, headers=org)
    vencer_checkin(pid3)
    r = c.post(f"/api/fases/{fid}/partidas/{pid3}/resolver-checkin", headers=org)
    print("Nadie confirmo -> estado:", r.json()["estado"], "(vuelve a programada para reprogramar)")

    # ---------------------------------------------------------------
    linea("ESCENARIO 4 — Reportar problema (disputa), separado del reporte normal")
    p4 = c.post(f"/api/fases/{fid}/partidas", json={
        "equipo_ids": [equipo_b, equipo_d],
    }, headers=org).json()
    pid4 = p4["id"]

    r = c.post(f"/api/fases/{fid}/partidas/{pid4}/reportar-problema", json={
        "equipo_id": equipo_b,
        "motivo": "El rival no entro a la sala de espera despues de 20 minutos.",
    }, headers=cap_b)
    disputa = r.json()
    print("Disputa creada:", disputa["id"], "| estado partida:")
    p4_actualizada = c.get(f"/api/fases/{fid}/partidas/{pid4}").json()
    print(" ", p4_actualizada["estado"])

    r = c.get("/api/disputas", params={"estado": "abierta"})
    print(f"\nBandeja del organizador sin login -> HTTP {r.status_code}: {r.json()['detail']}")

    bandeja = c.get("/api/disputas", params={"estado": "abierta"}, headers=org).json()
    print(f"Bandeja del organizador: {len(bandeja)} disputa(s) abierta(s)")
    for d in bandeja:
        print(f"  #{d['id']} partida={d['partida_id']} motivo: {d['motivo'][:50]}...")

    r = c.post(f"/api/disputas/{disputa['id']}/resolver", json={
        "resolucion": "Se verifico el log: el equipo B tiene razon, el rival nunca conecto.",
        "accion": "walkover",
        "equipo_ganador_id": equipo_b,
    }, headers=org)
    print("\nDisputa resuelta con walkover:")
    print(" ", r.json())

    p4_final = c.get(f"/api/fases/{fid}/partidas/{pid4}").json()
    print("\nEstado final de la partida:", p4_final["estado"])
    for part in p4_final["participaciones"]:
        print(f"  {part['equipo']['nombre']}: es_ganador={part['es_ganador']}")

    linea("ESCENARIO 5 — Disputa resuelta con 'reprogramar'")
    p5 = c.post(f"/api/fases/{fid}/partidas", json={
        "equipo_ids": [equipo_a, equipo_d],
    }, headers=org).json()
    pid5 = p5["id"]
    r = c.post(f"/api/fases/{fid}/partidas/{pid5}/reportar-problema", json={
        "equipo_id": equipo_d,
        "motivo": "Se corto la luz a mitad de partida, hay screenshot del apagon.",
        "evidencia_url": "https://ejemplo.com/evidencia.png",
    }, headers=cap_d)
    disputa5 = r.json()
    c.post(f"/api/disputas/{disputa5['id']}/resolver", json={
        "resolucion": "Caso de fuerza mayor verificado, se rejuega.",
        "accion": "reprogramar",
    }, headers=org)
    p5_final = c.get(f"/api/fases/{fid}/partidas/{pid5}").json()
    print("Estado final tras reprogramar:", p5_final["estado"], "(vuelve a programada)")

    linea("VALIDACIONES DE ESTADO INVALIDO")
    r = c.post(f"/api/fases/{fid}/partidas/{pid5}/checkin", json={"equipo_id": equipo_a}, headers=cap_a)
    print(f"Check-in sin abrir ventana -> HTTP {r.status_code}: {r.json()['detail']}")

    r = c.post(f"/api/fases/{fid}/partidas", json={"equipo_ids": [equipo_a, equipo_b, equipo_c]}, headers=org)
    print(f"Crear partida directa con 3 equipos -> HTTP {r.status_code}: {r.json()['detail']}")

print("\nprobar_checkin.py: fin (sin asserts fallidos == OK)")
