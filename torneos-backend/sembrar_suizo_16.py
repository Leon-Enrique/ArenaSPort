"""Crea un torneo suizo de 16 equipos CON CORTE real (3 victorias
clasifica, 3 derrotas elimina) — el mismo formato que usa el M7 World
Championship de MLBB. Juega todas las rondas necesarias (hasta 5) con
resultados reales via la API, hasta que los 16 equipos terminan con 3V o
3D.

Ejecutar: python sembrar_suizo_16.py
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
    "Crimson Hawks", "Obsidian Wolves", "Solar Flare", "Void Runners",
]


def slugish_tag(nombre: str) -> str:
    palabras = nombre.split()
    return (palabras[0][:2] + palabras[1][:2]).upper()


def inscribir_equipos(c, edicion_id, nombres):
    ids = []
    for nombre in nombres:
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
    c.post(f"/api/fases/{fase_id}/partidas/{partida['id']}/confirmar",
           json={"equipo_id": eq_b}, headers=org)


def jugar_ronda_actual(c, org, fase_id, bo):
    partidas = c.get(f"/api/fases/{fase_id}/partidas").json()
    ronda_actual = max(p["ronda"] for p in partidas if p["ronda"] is not None)
    pendientes = [
        p for p in partidas
        if p["ronda"] == ronda_actual and p["estado"] == "programada" and len(p["participaciones"]) == 2
    ]
    for p in pendientes:
        jugar_partida_real(c, org, fase_id, p, bo)


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db, discord_id="org-demo-suizo16")
    db.close()

    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")

    print("== Suizo con corte (16 equipos, 3V clasifica / 3D elimina) ==")
    t = c.post("/api/torneos", json={
        "nombre": f"M7 Style Swiss {int(time.time()) % 100000}",
        "descripcion": "Formato suizo con corte de 3 victorias / 3 derrotas, igual al M7 World Championship.",
    }, headers=org).json()
    e = c.post("/api/ediciones", json={
        "torneo_id": t["id"], "juego_id": mlbb["id"], "numero": 1,
        "nombre": "Fase Suiza - Road to Worlds", "max_equipos": 16,
        "fecha_inicio": "2026-08-01", "bolsa_premios": "$5,000 USD",
    }, headers=org).json()
    c.post(f"/api/ediciones/{e['id']}/estado", params={"estado": "inscripciones_abiertas"}, headers=org)

    ids = inscribir_equipos(c, e["id"], EQUIPOS)
    for iid in ids:
        c.post(f"/api/ediciones/{e['id']}/inscripciones/{iid}/revisar",
               json={"estado": "aprobada"}, headers=org)
    c.post(f"/api/ediciones/{e['id']}/inscripciones/sembrar-automatico", headers=org)

    fase = c.post(f"/api/ediciones/{e['id']}/fases", json={
        "orden": 1, "nombre": "Fase Suiza",
        "modelo_competencia": "enfrentamiento_directo", "formato": "suizo",
        "config": {"bo": 1, "meta_victorias": 3, "meta_derrotas": 3},
    }, headers=org).json()

    r = c.post(f"/api/ediciones/{e['id']}/fases/{fase['id']}/sortear", headers=org)
    print(f"Ronda 1 sorteada: {len(r.json())} partidas")
    jugar_ronda_actual(c, org, fase["id"], bo=1)

    for ronda in range(2, 6):
        r = c.post(f"/api/ediciones/{e['id']}/fases/{fase['id']}/siguiente-ronda-suiza", headers=org)
        if r.status_code != 200:
            print(f"Ronda {ronda}: {r.json().get('detail', r.text)[:200]}")
            break
        creadas = r.json()
        print(f"Ronda {ronda} generada: {len(creadas)} partidas")
        jugar_ronda_actual(c, org, fase["id"], bo=1)

    c.post(f"/api/ediciones/{e['id']}/fases/{fase['id']}/cerrar", headers=org)
    c.post(f"/api/ediciones/{e['id']}/estado", params={"estado": "finalizada"}, headers=org)

    tabla = c.get(f"/api/ediciones/{e['id']}/fases/{fase['id']}/tabla").json()
    print("\nResultado final:")
    for fila in tabla[0]["filas"]:
        estado = "CLASIFICADO" if fila["victorias"] >= 3 else ("ELIMINADO" if fila["derrotas"] >= 3 else "?")
        print(f"  {fila['equipo_nombre']:20s} {fila['victorias']}-{fila['derrotas']}  {estado}")

    print(f"\nListo: torneo edicion {e['id']}")
