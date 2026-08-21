"""Prueba del formato suizo completo: ronda 1, resolver resultados, generar
ronda 2 evitando repetir rivales, y el caso de cantidad impar (error claro).
"""

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from probar_utils import headers_capitan, headers_organizador


def linea(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def crear_torneo(c, org, nombre, mlbb, nombres_equipos):
    t = c.post("/api/torneos", json={"nombre": nombre}, headers=org).json()
    e = c.post("/api/ediciones", json={
        "torneo_id": t["id"], "juego_id": mlbb["id"], "numero": 1, "nombre": "Ed 1",
    }, headers=org).json()
    eid = e["id"]
    c.post(f"/api/ediciones/{eid}/estado", params={"estado": "inscripciones_abiertas"}, headers=org)

    ids = {}
    for nombre_equipo in nombres_equipos:
        r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
            "nombre_equipo": nombre_equipo,
            "jugadores": [
                {"identidad": {"nick": f"{nombre_equipo}{i}",
                               "id_juego": str(hash(f'{nombre_equipo}{i}') % 10**8), "server": "2251"},
                 "es_suplente": None, "es_capitan": i == 0,
                 "discord_id": f"cap_{nombre_equipo}" if i == 0 else None}
                for i in range(5)
            ],
        })
        ids[nombre_equipo] = r.json()["inscripcion"]["equipo"]["id"]

    for iid in [i["id"] for i in c.get(f"/api/ediciones/{eid}/inscripciones").json()]:
        c.post(f"/api/ediciones/{eid}/inscripciones/{iid}/revisar", json={"estado": "aprobada"}, headers=org)

    c.post(f"/api/ediciones/{eid}/inscripciones/sembrar-automatico", params={"semilla": 1}, headers=org)
    return eid, ids


def resolver_ronda_actual(c, org, cap, fase_id, bo=1):
    """Resuelve todas las partidas de la ULTIMA ronda generada, dejando
    ganar siempre al primer participante de cada partida — no hace falta
    saber de antemano quién quedó emparejado con quién, el suizo lo decide
    el algoritmo de emparejamiento, no el test.
    """
    partidas = c.get(f"/api/fases/{fase_id}/partidas").json()
    ultima_ronda = max(p["ronda"] for p in partidas)
    de_esta_ronda = [p for p in partidas if p["ronda"] == ultima_ronda and len(p["participaciones"]) == 2]

    maximo = bo // 2 + 1
    resultados = []
    for p in de_esta_ronda:
        nombre_a = p["participaciones"][0]["equipo"]["nombre"]
        nombre_b = p["participaciones"][1]["equipo"]["nombre"]
        equipo_a = p["participaciones"][0]["equipo"]["id"]
        equipo_b = p["participaciones"][1]["equipo"]["id"]

        pid = p["id"]
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/abrir-checkin", json={"minutos": 15}, headers=org)
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin", json={"equipo_id": equipo_a}, headers=cap[nombre_a])
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/checkin", json={"equipo_id": equipo_b}, headers=cap[nombre_b])
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/reportar", json={
            "equipo_id": equipo_a, "marcador_propio": maximo, "marcador_rival": 0,
            "evidencia_url": "https://ejemplo.com/cap.png",
        }, headers=cap[nombre_a])
        c.post(f"/api/fases/{fase_id}/partidas/{pid}/confirmar", json={"equipo_id": equipo_b}, headers=cap[nombre_b])
        resultados.append((nombre_a, nombre_b))  # nombre_a siempre gana

    return resultados


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db)
    db.close()

    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")

    linea("SUIZO CON 8 EQUIPOS (cantidad par, sin bye)")
    nombres = [f"Equipo{i}" for i in range(1, 9)]
    eid, ids = crear_torneo(c, org, "Copa Suiza 8", mlbb, nombres)

    db = SessionLocal()
    cap = {n: headers_capitan(db, f"cap_{n}") for n in nombres}
    db.close()

    fase = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 1, "nombre": "Suizo", "modelo_competencia": "enfrentamiento_directo",
        "formato": "suizo", "config": {"bo": 1},
    }, headers=org).json()
    fid = fase["id"]

    r = c.post(f"/api/ediciones/{eid}/fases/{fid}/sortear", headers=org)
    ronda1 = r.json()
    print(f"Ronda 1: {len(ronda1)} partidas (esperado 4)")
    for p in ronda1:
        nombres_p = [pp["equipo"]["nombre"] for pp in p["participaciones"]]
        print(" ", nombres_p)

    r = c.post(f"/api/ediciones/{eid}/fases/{fid}/siguiente-ronda-suiza", headers=org)
    print(f"\nGenerar ronda 2 sin resolver ronda 1 -> HTTP {r.status_code}: {r.json()['detail'][:60]}...")

    ganadores_r1 = resolver_ronda_actual(c, org, cap, fid, bo=1)
    enfrentamientos_r1 = {tuple(sorted(par)) for par in ganadores_r1}
    print("\nRonda 1 resuelta. Ganadores:", [g for g, _ in ganadores_r1])

    tabla = c.get(f"/api/ediciones/{eid}/fases/{fid}/tabla").json()
    print("\nTabla tras ronda 1:")
    for f in tabla[0]["filas"]:
        print(f"  {f['equipo_nombre']}: {f['puntos']} pts, dif={f['diferencia_mapas']:+d}")

    r = c.post(f"/api/ediciones/{eid}/fases/{fid}/siguiente-ronda-suiza", headers=org)
    ronda2 = r.json()
    print(f"\nRonda 2 generada: {len(ronda2)} partidas")
    parejas_r2 = []
    for p in ronda2:
        nombres_p = tuple(sorted(pp["equipo"]["nombre"] for pp in p["participaciones"]))
        parejas_r2.append(nombres_p)
        print(" ", nombres_p)

    repetidos = [par for par in parejas_r2 if par in enfrentamientos_r1]
    print(f"\nRivales repetidos de ronda 1 en ronda 2: {len(repetidos)} (esperado 0)")
    assert not repetidos, f"Se repitieron rivales: {repetidos}"

    r = c.post(f"/api/ediciones/{eid}/fases/{fid}/siguiente-ronda-suiza", headers=org)
    print(f"\nGenerar ronda 3 sin resolver ronda 2 -> HTTP {r.status_code}: {r.json()['detail'][:60]}...")

    ganadores_r2 = resolver_ronda_actual(c, org, cap, fid, bo=1)
    r = c.post(f"/api/ediciones/{eid}/fases/{fid}/siguiente-ronda-suiza", headers=org)
    ronda3 = r.json()
    print(f"\nRonda 3 generada tras resolver ronda 2: {len(ronda3)} partidas")
    todos_enfrentamientos_previos = enfrentamientos_r1 | {tuple(sorted(par)) for par in ganadores_r2}
    parejas_r3 = [tuple(sorted(pp["equipo"]["nombre"] for pp in p["participaciones"])) for p in ronda3]
    repetidos3 = [par for par in parejas_r3 if par in todos_enfrentamientos_previos]
    print(f"Rivales repetidos de rondas anteriores en ronda 3: {len(repetidos3)} (esperado 0 o casi 0)")
    for par in parejas_r3:
        print(" ", par)

    tabla_final = c.get(f"/api/ediciones/{eid}/fases/{fid}/tabla").json()
    print("\nTabla tras 2 rondas completas:")
    for f in tabla_final[0]["filas"]:
        print(f"  #{f['posicion']} {f['equipo_nombre']}: {f['puntos']} pts")

    # -----------------------------------------------------------------
    linea("SUIZO CON 7 EQUIPOS (cantidad impar -> bye automatico al peor sembrado)")
    nombres7 = [f"Team{i}" for i in range(1, 8)]
    eid7, ids7 = crear_torneo(c, org, "Copa Suiza 7", mlbb, nombres7)

    db = SessionLocal()
    cap7 = {n: headers_capitan(db, f"cap_{n}") for n in nombres7}
    db.close()

    fase7 = c.post(f"/api/ediciones/{eid7}/fases", json={
        "orden": 1, "nombre": "Suizo Impar", "modelo_competencia": "enfrentamiento_directo",
        "formato": "suizo", "config": {"bo": 1},
    }, headers=org).json()

    r = c.post(f"/api/ediciones/{eid7}/fases/{fase7['id']}/sortear", headers=org)
    ronda1_7 = r.json()
    print(f"Sortear ronda 1 con 7 equipos -> HTTP {r.status_code}, {len(ronda1_7)} partidas")
    byes = [p for p in ronda1_7 if p["estado"] == "bye"]
    programadas = [p for p in ronda1_7 if p["estado"] == "programada"]
    print(f"  {len(programadas)} partidas normales + {len(byes)} bye automático")
    assert len(byes) == 1 and len(programadas) == 3

    equipo_bye = byes[0]["participaciones"][0]["equipo"]["nombre"]
    print(f"  Equipo con bye en ronda 1: {equipo_bye}")

    tabla7 = c.get(f"/api/ediciones/{eid7}/fases/{fase7['id']}/tabla").json()
    fila_bye = next(f for f in tabla7[0]["filas"] if f["equipo_nombre"] == equipo_bye)
    print(f"  Puntos del equipo con bye (antes de jugar nada más): {fila_bye['puntos']} "
          f"(debería tener 3 solo por el bye)")
    assert fila_bye["puntos"] == 3
    assert fila_bye["jugados"] == 1

    # -----------------------------------------------------------------
    linea("SUIZO CON 45 EQUIPOS (el tamano real del torneo de MLBB)")
    nombres45 = [f"E{i:02d}" for i in range(1, 46)]
    eid45, ids45 = crear_torneo(c, org, "Copa Suiza 45", mlbb, nombres45)

    db = SessionLocal()
    cap45 = {n: headers_capitan(db, f"cap_{n}") for n in nombres45}
    db.close()

    fase45 = c.post(f"/api/ediciones/{eid45}/fases", json={
        "orden": 1, "nombre": "Suizo 45", "modelo_competencia": "enfrentamiento_directo",
        "formato": "suizo", "config": {"bo": 1},
    }, headers=org).json()

    r = c.post(f"/api/ediciones/{eid45}/fases/{fase45['id']}/sortear", headers=org)
    ronda1_45 = r.json()
    programadas45 = [p for p in ronda1_45 if p["estado"] == "programada"]
    byes45 = [p for p in ronda1_45 if p["estado"] == "bye"]
    print(f"45 equipos -> {len(ronda1_45)} partidas: {len(programadas45)} normales + "
          f"{len(byes45)} bye (esperado 22 normales + 1 bye)")
    assert len(programadas45) == 22
    assert len(byes45) == 1

    resolver_ronda_actual(c, org, cap45, fase45["id"], bo=1)
    r = c.post(f"/api/ediciones/{eid45}/fases/{fase45['id']}/siguiente-ronda-suiza", headers=org)
    ronda2_45 = r.json()
    print(f"Ronda 2 generada sobre 45 equipos: {len(ronda2_45)} partidas "
          f"(esperado 22 normales + 1 bye para quien no jugó la ronda 1... o distinto")
    print("  segun a quien le toque el bye esta vez)")

print("\n" + "=" * 70)
print("TODAS LAS PRUEBAS DE SUIZO PASARON")
print("=" * 70)
