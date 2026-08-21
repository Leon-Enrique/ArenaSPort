"""Prueba manual del flujo de inscripción. Ejecutar: python probar_flujo.py"""

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from probar_utils import headers_organizador


def jugador(nick, id_juego="", server="2251", suplente=None, capitan=False, discord_id=None):
    return {
        "identidad": {"nick": nick, "id_juego": id_juego or str(abs(hash(nick)) % 10**9), "server": server},
        "es_suplente": suplente,
        "es_capitan": capitan,
        "discord_id": discord_id,
    }


def linea(titulo):
    print(f"\n{'=' * 70}\n{titulo}\n{'=' * 70}")


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db)
    db.close()

    linea("SETUP")
    juegos = {j["codigo"]: j for j in c.get("/api/juegos").json()}
    mlbb = juegos["mlbb"]

    t = c.post("/api/torneos", json={"nombre": "Copa Santa Cruz MLBB"}, headers=org).json()
    print("Torneo:", t["nombre"], "| slug:", t["slug"])

    e = c.post(
        "/api/ediciones",
        json={
            "torneo_id": t["id"],
            "juego_id": mlbb["id"],
            "numero": 2,
            "nombre": "2da Edicion",
            "max_equipos": 48,
        },
        headers=org,
    ).json()
    eid = e["id"]
    print("Edicion:", e["nombre"], "| estado:", e["estado"])

    r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
        "nombre_equipo": "Test", "jugadores": [jugador(f"j{i}") for i in range(5)]
    })
    print(f"\nInscribir con inscripciones cerradas -> {r.status_code}: {r.json()['detail']}")

    c.post(f"/api/ediciones/{eid}/estado", params={"estado": "inscripciones_abiertas"}, headers=org)
    print("Inscripciones abiertas.")

    linea("Inscribir NO requiere login (registro publico)")
    print("(las llamadas de abajo a /inscripciones van sin headers a proposito)")

    linea("CASO 1 — Equipo de 7 sin marcar suplentes (regla: ultimos 2)")
    r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
        "nombre_equipo": "Dragones FC",
        "tag": "DRG",
        "contacto_whatsapp": "+591 70000001",
        "capitan_declarado": "Lyon",
        "jugadores": [jugador(n, discord_id=f"discord_{n}" if n == "Lyon" else None)
                      for n in ["Lyon", "Kaze", "Nova", "Rex", "Zed", "Milo", "Puck"]],
    })
    print("HTTP", r.status_code)
    d = r.json()
    for j in d["inscripcion"]["jugadores"]:
        rol = "SUPLENTE" if j["es_suplente"] else "titular"
        cap = " (C)" if j["es_capitan"] else ""
        disc = f" discord={j['discord_id']}" if j["discord_id"] else ""
        print(f"  {j['orden']}. {j['identidad']['nick']:8} {rol}{cap}{disc}")
    for a in d["avisos"]:
        print("  AVISO:", a)

    linea("CASO 2 — Capitan con nombre real que no coincide con ningun nick")
    r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
        "nombre_equipo": "Titanes",
        "capitan_declarado": "Juan Perez",
        "jugadores": [jugador(n) for n in ["Sombra", "Blitz", "Iron", "Vex", "Kai", "Neo"]],
    })
    print("HTTP", r.status_code)
    d = r.json()
    for j in d["inscripcion"]["jugadores"]:
        rol = "SUPLENTE" if j["es_suplente"] else "titular"
        cap = " (C)" if j["es_capitan"] else ""
        print(f"  {j['orden']}. {j['identidad']['nick']:8} {rol}{cap}")
    for a in d["avisos"]:
        print("  AVISO:", a)

    linea("CASO 3 — Jugador ya inscrito en otro equipo (elegibilidad)")
    repetido = jugador("Lyon")
    repetido["identidad"] = c.get(f"/api/ediciones/{eid}/inscripciones").json()[0]["jugadores"][0]["identidad"]
    r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
        "nombre_equipo": "Los Tramposos",
        "jugadores": [repetido] + [jugador(f"x{i}") for i in range(4)],
    })
    print(f"HTTP {r.status_code}: {r.json()['detail']}")

    linea("CASO 4 — Roster incompleto (4 jugadores para MLBB)")
    r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
        "nombre_equipo": "Incompletos",
        "jugadores": [jugador(f"y{i}") for i in range(4)],
    })
    print(f"HTTP {r.status_code}: {r.json()['detail']}")

    linea("CASO 5 — Falta el server ID")
    malo = {"identidad": {"nick": "SinServer", "id_juego": "999"}, "es_suplente": None,
            "es_capitan": False, "discord_id": None}
    r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
        "nombre_equipo": "Sin Datos",
        "jugadores": [malo] + [jugador(f"z{i}") for i in range(4)],
    })
    print(f"HTTP {r.status_code}: {r.json()['detail']}")

    linea("CASO 6 — Nombre de equipo duplicado")
    r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
        "nombre_equipo": "  dragones fc  ",
        "jugadores": [jugador(f"w{i}") for i in range(5)],
    })
    print(f"HTTP {r.status_code}: {r.json()['detail']}")

    linea("CASO 7 — Free Fire: 4 titulares, identidad por UID")
    ff = juegos["free_fire"]
    e2 = c.post("/api/ediciones", json={
        "torneo_id": t["id"], "juego_id": ff["id"], "numero": 3, "nombre": "Copa FF",
    }, headers=org).json()
    c.post(f"/api/ediciones/{e2['id']}/estado", params={"estado": "inscripciones_abiertas"}, headers=org)
    r = c.post(f"/api/ediciones/{e2['id']}/inscripciones", json={
        "nombre_equipo": "Escuadra Fenix",
        "jugadores": [
            {"identidad": {"nick": n, "uid": str(1000 + i)}, "es_suplente": None,
             "es_capitan": False, "discord_id": None}
            for i, n in enumerate(["Ash", "Kelly", "Alok", "Chrono", "Hayato"])
        ],
    })
    print("HTTP", r.status_code)
    d = r.json()
    for j in d["inscripcion"]["jugadores"]:
        rol = "SUPLENTE" if j["es_suplente"] else "titular"
        cap = " (C)" if j["es_capitan"] else ""
        print(f"  {j['orden']}. {j['identidad']['nick']:8} uid={j['identidad']['uid']} {rol}{cap}")
    for a in d["avisos"]:
        print("  AVISO:", a)

    linea("PANEL DEL ORGANIZADOR")
    ins = c.get(f"/api/ediciones/{eid}/inscripciones").json()
    print(f"Inscripciones en la edicion MLBB: {len(ins)}")
    for i in ins:
        print(f"  #{i['id']} {i['equipo']['nombre']:14} {i['estado']:10} "
              f"({len(i['jugadores'])} jugadores)")

    linea("REVISAR SIN LOGIN vs CON LOGIN DE ORGANIZADOR")
    r = c.post(f"/api/ediciones/{eid}/inscripciones/{ins[0]['id']}/revisar",
               json={"estado": "aprobada"})
    print(f"Aprobar sin token -> HTTP {r.status_code}: {r.json()['detail']}")

    c.post(f"/api/ediciones/{eid}/inscripciones/{ins[0]['id']}/revisar",
           json={"estado": "aprobada"}, headers=org)
    r = c.post(f"/api/ediciones/{eid}/inscripciones/{ins[1]['id']}/revisar",
               json={"estado": "rechazada"}, headers=org)
    print(f"\nRechazar sin motivo -> {r.status_code}: {r.json()['detail']}")

    c.post(f"/api/ediciones/{eid}/inscripciones/{ins[1]['id']}/revisar",
           json={"estado": "rechazada", "motivo_rechazo": "Roster incompleto al cierre"},
           headers=org)

    print("\nDespues de revisar:")
    for i in c.get(f"/api/ediciones/{eid}/inscripciones").json():
        print(f"  #{i['id']} {i['equipo']['nombre']:14} {i['estado']}")

    aprobadas = c.get(f"/api/ediciones/{eid}/inscripciones",
                      params={"estado": "aprobada"}).json()
    print(f"\nFiltrando solo aprobadas: {len(aprobadas)}")

    linea("VINCULAR DISCORD DESPUES DE LA INSCRIPCION")
    jugador_lyon = ins[0]["jugadores"][0]
    r = c.patch(
        f"/api/ediciones/{eid}/inscripciones/{ins[0]['id']}/jugadores/{jugador_lyon['id']}/vincular-discord",
        params={"discord_id": "discord_lyon_real"},
        headers=org,
    )
    print(f"Vincular discord al capitan -> HTTP {r.status_code}")
    if r.status_code == 200:
        cap = next(j for j in r.json()["jugadores"] if j["es_capitan"])
        print(f"  Capitan {cap['identidad']['nick']} ahora vinculado a discord_id={cap['discord_id']}")

print("\nprobar_flujo.py: fin (sin asserts fallidos == OK)")
