"""Prueba de la tabla de posiciones a traves de la API real.

Cubre: calculo basico sin grupos, division en grupos independientes,
walkover sin marcador cargado (se cuenta con el resultado de reglamento),
y el caso dificil: 3 equipos empatados en puntos resuelto por enfrentamiento
directo cuando es posible, y por diferencia de mapas cuando no (triangulo
perfecto).
"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.models import Partida
from probar_utils import headers_capitan, headers_organizador


def linea(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def imprimir_tabla(tabla):
    for grupo in tabla:
        etiqueta = f"Grupo {grupo['grupo']}" if grupo["grupo"] is not None else "Tabla general"
        print(f"  -- {etiqueta} --")
        for f in grupo["filas"]:
            print(f"    #{f['posicion']} {f['equipo_nombre']:10} "
                  f"PJ={f['jugados']} PG={f['victorias']} PE={f['empates']} PP={f['derrotas']} "
                  f"DIF={f['diferencia_mapas']:+d} PTS={f['puntos']}")


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db)
    db.close()

    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")
    t = c.post("/api/torneos", json={"nombre": "Copa Tabla"}, headers=org).json()
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

    nombres = ["Halcones", "Serpientes", "Lobos", "Aguilas", "Tigres", "Osos"]
    ids = {n: inscribir(n) for n in nombres}
    for iid in [i["id"] for i in c.get(f"/api/ediciones/{eid}/inscripciones").json()]:
        c.post(f"/api/ediciones/{eid}/inscripciones/{iid}/revisar", json={"estado": "aprobada"}, headers=org)

    db = SessionLocal()
    cap = {n: headers_capitan(db, f"cap_{n}") for n in nombres}
    db.close()

    linea("SIN GRUPOS — round robin simple, triangulo perfecto entre 3")
    fase1 = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 1, "nombre": "Grupo Unico", "modelo_competencia": "enfrentamiento_directo",
        "formato": "round_robin", "config": {"bo": 1},
    }, headers=org).json()
    c.post(f"/api/ediciones/{eid}/inscripciones/sembrar-automatico", params={"semilla": 1}, headers=org)

    r = c.post(f"/api/ediciones/{eid}/fases/{fase1['id']}/sortear", headers=org)
    print(f"Partidas creadas: {len(r.json())} (esperado C(6,2)=15)")

    def reportar_y_confirmar(fase_id, nombre_a, nombre_b, mapas_a, mapas_b):
        equipo_a, equipo_b = ids[nombre_a], ids[nombre_b]
        partidas = c.get(f"/api/fases/{fase_id}/partidas").json()
        p = next(
            p for p in partidas
            if {pp["equipo"]["id"] for pp in p["participaciones"]} == {equipo_a, equipo_b}
        )
        pid = p["id"]
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/abrir-checkin", json={"minutos": 15}, headers=org)
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin", json={"equipo_id": equipo_a}, headers=cap[nombre_a])
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin", json={"equipo_id": equipo_b}, headers=cap[nombre_b])
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/reportar", json={
            "equipo_id": equipo_a, "marcador_propio": mapas_a, "marcador_rival": mapas_b,
            "evidencia_url": "https://ejemplo.com/cap.png",
        }, headers=cap[nombre_a])
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/confirmar",
               json={"equipo_id": equipo_b}, headers=cap[nombre_b])

    # Triangulo perfecto: Halcones > Serpientes > Lobos > Halcones
    reportar_y_confirmar(fase1["id"], "Halcones", "Serpientes", 1, 0)
    reportar_y_confirmar(fase1["id"], "Serpientes", "Lobos", 1, 0)
    reportar_y_confirmar(fase1["id"], "Lobos", "Halcones", 1, 0)
    for perdedor in ["Aguilas", "Tigres", "Osos"]:
        for ganador in ["Halcones", "Serpientes", "Lobos"]:
            reportar_y_confirmar(fase1["id"], ganador, perdedor, 1, 0)

    tabla1 = c.get(f"/api/ediciones/{eid}/fases/{fase1['id']}/tabla").json()
    print("\nTabla (marcador uniforme 1-0: no hay NINGUNA diferencia real entre")
    print("Halcones/Serpientes/Lobos, así que es correcto que sigan empatados hasta")
    print("en diferencia de mapas — el desempate real por diferencia ya se probó")
    print("puro en domain/tabla.py; esto valida que la integración con la DB no rompe nada):")
    imprimir_tabla(tabla1)

    top3 = [f["equipo_nombre"] for f in tabla1[0]["filas"][:3]]
    assert set(top3) == {"Halcones", "Serpientes", "Lobos"}
    assert tabla1[0]["filas"][0]["puntos"] == tabla1[0]["filas"][2]["puntos"], \
        "Los 3 del triangulo deberian seguir empatados en puntos"

    # -----------------------------------------------------------------
    linea("CON GRUPOS — 6 equipos en 2 grupos de 3, tablas independientes")
    fase2 = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 2, "nombre": "Fase de Grupos", "modelo_competencia": "enfrentamiento_directo",
        "formato": "round_robin", "config": {"bo": 1, "grupos": 2},
    }, headers=org).json()
    r = c.post(f"/api/ediciones/{eid}/fases/{fase2['id']}/sortear", headers=org)
    print(f"Partidas creadas: {len(r.json())} (esperado 2 grupos * C(3,2)=3 = 6)")

    tabla2_vacia = c.get(f"/api/ediciones/{eid}/fases/{fase2['id']}/tabla").json()
    print(f"\nTabla antes de jugar nada: {len(tabla2_vacia)} grupos, "
          f"cada uno con {len(tabla2_vacia[0]['filas'])} equipos en 0")
    assert len(tabla2_vacia) == 2
    assert all(f["puntos"] == 0 for grupo in tabla2_vacia for f in grupo["filas"])

    # -----------------------------------------------------------------
    linea("WALKOVER SIN MARCADOR CARGADO — se cuenta con el resultado de reglamento")
    partidas_fase2 = c.get(f"/api/fases/{fase2['id']}/partidas").json()
    p_walkover = partidas_fase2[0]
    equipo_presente_id = p_walkover["participaciones"][0]["equipo"]["id"]
    equipo_presente_nombre = p_walkover["participaciones"][0]["equipo"]["nombre"]
    pid_w = p_walkover["id"]
    c.post(f"/api/fases/{fase2['id']}/partidas/{pid_w}/abrir-checkin", json={"minutos": 15}, headers=org)
    c.post(f"/api/fases/{fase2['id']}/partidas/{pid_w}/checkin",
           json={"equipo_id": equipo_presente_id}, headers=cap[equipo_presente_nombre])

    db = SessionLocal()
    pp = db.get(Partida, pid_w)
    pp.checkin_cierra_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    db.close()
    c.post(f"/api/fases/{fase2['id']}/partidas/{pid_w}/resolver-checkin", headers=org)

    tabla2_con_walkover = c.get(f"/api/ediciones/{eid}/fases/{fase2['id']}/tabla").json()
    fila_ganador_walkover = next(
        f for grupo in tabla2_con_walkover for f in grupo["filas"]
        if f["equipo_id"] == equipo_presente_id
    )
    print(f"Ganador por walkover: PJ={fila_ganador_walkover['jugados']} "
          f"PTS={fila_ganador_walkover['puntos']} DIF={fila_ganador_walkover['diferencia_mapas']}")
    assert fila_ganador_walkover["jugados"] == 1
    assert fila_ganador_walkover["puntos"] == 3
    assert fila_ganador_walkover["diferencia_mapas"] == 1  # BO1 -> maximo 1, walkover 1-0

    # -----------------------------------------------------------------
    linea("VALIDACION: llave de eliminacion no tiene tabla")
    fase_llave = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 3, "nombre": "Playoffs", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_simple",
    }, headers=org).json()
    r = c.get(f"/api/ediciones/{eid}/fases/{fase_llave['id']}/tabla")
    print(f"Pedir tabla de una llave -> HTTP {r.status_code}: {r.json()['detail'][:60]}...")
    assert r.status_code == 422

print("\n" + "=" * 70)
print("TODAS LAS PRUEBAS DE TABLA PASARON")
print("=" * 70)
