"""Crea varios torneos de DEMOSTRACION, jugados de punta a punta con
resultados reales (no walkovers) y equipos/jugadores simulados, para que
se pueda ver publicamente como queda cada formato de fase ya terminado:
eliminacion simple, eliminacion doble, grupos (round robin) y suizo.

Usa la API real end-to-end (igual que un capitan/organizador de verdad),
no inserta filas a mano. Ejecutar: python sembrar_torneos_demo.py
"""

import random
import time

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from probar_utils import headers_organizador

EQUIPOS = [
    "Alpha Wolves", "Cyber Titans", "Nova Squad", "Phoenix Gaming",
    "Viper Warriors", "Ghost Legion", "Kraken Esports", "Iron Dragons",
    "Shadow Reapers", "Storm Riders", "Blaze Kings", "Frost Giants",
]


def slugish_tag(nombre: str) -> str:
    palabras = nombre.split()
    return (palabras[0][:2] + palabras[1][:2]).upper()


def crear_torneo_y_edicion(c, org, nombre_torneo, mlbb, max_equipos, bolsa, fecha_inicio):
    t = c.post("/api/torneos", json={
        "nombre": f"{nombre_torneo} {int(time.time()) % 100000}",
        "descripcion": "Torneo de demostracion con resultados reales.",
    }, headers=org).json()
    e = c.post("/api/ediciones", json={
        "torneo_id": t["id"], "juego_id": mlbb["id"], "numero": 1,
        "nombre": nombre_torneo, "max_equipos": max_equipos,
        "fecha_inicio": fecha_inicio, "bolsa_premios": bolsa,
    }, headers=org).json()
    c.post(f"/api/ediciones/{e['id']}/estado", params={"estado": "inscripciones_abiertas"}, headers=org)
    return t, e


def inscribir_equipos(c, edicion_id, cantidad, offset=0):
    ids = []
    for i in range(cantidad):
        nombre = EQUIPOS[(offset + i) % len(EQUIPOS)]
        tag = slugish_tag(nombre)
        r = c.post(f"/api/ediciones/{edicion_id}/inscripciones", json={
            "nombre_equipo": nombre,
            "tag": tag,
            "contacto_nombre": f"Capitan de {nombre}",
            "jugadores": [
                {
                    "identidad": {
                        "nick": f"{tag}{j+1}",
                        "id_juego": str(random.randint(100_000_000, 999_999_999)),
                        "server": "2251",
                    },
                    "es_capitan": j == 0,
                }
                for j in range(5)
            ],
        })
        ids.append(r.json()["inscripcion"]["id"])
    return ids


def aprobar_todas(c, org, edicion_id, inscripcion_ids):
    for iid in inscripcion_ids:
        c.post(f"/api/ediciones/{edicion_id}/inscripciones/{iid}/revisar",
               json={"estado": "aprobada"}, headers=org)


def jugar_partida_real(c, org, fase_id, partida, bo):
    parts = partida["participaciones"]
    if len(parts) != 2:
        return
    eq_a, eq_b = parts[0]["equipo"]["id"], parts[1]["equipo"]["id"]

    c.post(f"/api/fases/{fase_id}/partidas/{partida['id']}/abrir-checkin",
           json={"minutos": 30}, headers=org)
    c.post(f"/api/fases/{fase_id}/partidas/{partida['id']}/checkin",
           json={"equipo_id": eq_a}, headers=org)
    c.post(f"/api/fases/{fase_id}/partidas/{partida['id']}/checkin",
           json={"equipo_id": eq_b}, headers=org)

    ganados_para_ganar = bo // 2 + 1
    marcador_perdedor = random.randint(0, ganados_para_ganar - 1)
    if random.random() < 0.5:
        m_a, m_b = ganados_para_ganar, marcador_perdedor
    else:
        m_a, m_b = marcador_perdedor, ganados_para_ganar

    r1 = c.post(f"/api/fases/{fase_id}/partidas/{partida['id']}/reportar",
                json={"equipo_id": eq_a, "marcador_propio": m_a, "marcador_rival": m_b},
                headers=org)
    if r1.status_code != 200:
        print(f"    ! reportar fallo partida {partida['id']}: {r1.text[:150]}")
        return
    r2 = c.post(f"/api/fases/{fase_id}/partidas/{partida['id']}/confirmar",
                json={"equipo_id": eq_b}, headers=org)
    if r2.status_code != 200:
        print(f"    ! confirmar fallo partida {partida['id']}: {r2.text[:150]}")


def jugar_fase_hasta_el_final(c, org, fase_id, bo=3, max_vueltas=30):
    vueltas = 0
    while True:
        vueltas += 1
        if vueltas > max_vueltas:
            raise RuntimeError(f"Fase {fase_id}: no converge despues de {max_vueltas} vueltas.")
        partidas = c.get(f"/api/fases/{fase_id}/partidas").json()
        pendientes = [p for p in partidas if p["estado"] == "programada" and len(p["participaciones"]) == 2]
        if not pendientes:
            return
        for p in pendientes:
            jugar_partida_real(c, org, fase_id, p, bo)


def finalizar_edicion(c, org, edicion_id):
    c.post(f"/api/ediciones/{edicion_id}/estado", params={"estado": "finalizada"}, headers=org)


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db, discord_id="org-demo-seed")
    db.close()

    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")

    # ------------------------------------------------------------------
    print("== Eliminacion Simple (8 equipos) ==")
    _, e1 = crear_torneo_y_edicion(c, org, "Copa Elite MLBB", mlbb, 8, "$1,000 USD", "2026-07-15")
    ids1 = inscribir_equipos(c, e1["id"], 8, offset=0)
    aprobar_todas(c, org, e1["id"], ids1)
    c.post(f"/api/ediciones/{e1['id']}/inscripciones/sembrar-automatico", headers=org)
    fase1 = c.post(f"/api/ediciones/{e1['id']}/fases", json={
        "orden": 1, "nombre": "Cuadro Principal", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_simple", "config": {"bo": 3},
    }, headers=org).json()
    c.post(f"/api/ediciones/{e1['id']}/fases/{fase1['id']}/sortear", headers=org)
    jugar_fase_hasta_el_final(c, org, fase1["id"], bo=3)
    finalizar_edicion(c, org, e1["id"])
    print(f"   listo: torneo edicion {e1['id']}")

    # ------------------------------------------------------------------
    print("== Eliminacion Doble (8 equipos) ==")
    _, e2 = crear_torneo_y_edicion(c, org, "Liga Doble Impacto", mlbb, 8, "$1,500 USD", "2026-07-20")
    ids2 = inscribir_equipos(c, e2["id"], 8, offset=2)
    aprobar_todas(c, org, e2["id"], ids2)
    c.post(f"/api/ediciones/{e2['id']}/inscripciones/sembrar-automatico", headers=org)
    fase2 = c.post(f"/api/ediciones/{e2['id']}/fases", json={
        "orden": 1, "nombre": "Llave Doble Eliminacion", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_doble", "config": {"bo": 3},
    }, headers=org).json()
    c.post(f"/api/ediciones/{e2['id']}/fases/{fase2['id']}/sortear", headers=org)
    jugar_fase_hasta_el_final(c, org, fase2["id"], bo=3, max_vueltas=40)
    finalizar_edicion(c, org, e2["id"])
    print(f"   listo: torneo edicion {e2['id']}")

    # ------------------------------------------------------------------
    print("== Fase de Grupos / Round Robin (8 equipos, 2 grupos) ==")
    _, e3 = crear_torneo_y_edicion(c, org, "Copa de Grupos LATAM", mlbb, 8, "$800 USD", "2026-07-10")
    ids3 = inscribir_equipos(c, e3["id"], 8, offset=4)
    aprobar_todas(c, org, e3["id"], ids3)
    c.post(f"/api/ediciones/{e3['id']}/inscripciones/sembrar-automatico", headers=org)
    fase3 = c.post(f"/api/ediciones/{e3['id']}/fases", json={
        "orden": 1, "nombre": "Fase de Grupos", "modelo_competencia": "enfrentamiento_directo",
        "formato": "round_robin", "config": {"bo": 1, "grupos": 2},
    }, headers=org).json()
    c.post(f"/api/ediciones/{e3['id']}/fases/{fase3['id']}/sortear", headers=org)
    jugar_fase_hasta_el_final(c, org, fase3["id"], bo=1)
    c.post(f"/api/ediciones/{e3['id']}/fases/{fase3['id']}/cerrar", headers=org)
    finalizar_edicion(c, org, e3["id"])
    print(f"   listo: torneo edicion {e3['id']}")

    # ------------------------------------------------------------------
    print("== Sistema Suizo (8 equipos, 3 rondas) ==")
    _, e4 = crear_torneo_y_edicion(c, org, "Mundial Suizo MLBB", mlbb, 8, "$2,000 USD", "2026-07-25")
    ids4 = inscribir_equipos(c, e4["id"], 8, offset=6)
    aprobar_todas(c, org, e4["id"], ids4)
    c.post(f"/api/ediciones/{e4['id']}/inscripciones/sembrar-automatico", headers=org)
    fase4 = c.post(f"/api/ediciones/{e4['id']}/fases", json={
        "orden": 1, "nombre": "Ronda Suiza", "modelo_competencia": "enfrentamiento_directo",
        "formato": "suizo", "config": {"bo": 1},
    }, headers=org).json()
    c.post(f"/api/ediciones/{e4['id']}/fases/{fase4['id']}/sortear", headers=org)
    jugar_fase_hasta_el_final(c, org, fase4["id"], bo=1)
    for ronda in range(2, 4):
        r = c.post(f"/api/ediciones/{e4['id']}/fases/{fase4['id']}/siguiente-ronda-suiza", headers=org)
        if r.status_code != 200:
            print(f"   ronda {ronda}: {r.text[:150]}")
            break
        jugar_fase_hasta_el_final(c, org, fase4["id"], bo=1)
    c.post(f"/api/ediciones/{e4['id']}/fases/{fase4['id']}/cerrar", headers=org)
    finalizar_edicion(c, org, e4["id"])
    print(f"   listo: torneo edicion {e4['id']}")

print("\nTodos los torneos de demo quedaron creados y finalizados.")
