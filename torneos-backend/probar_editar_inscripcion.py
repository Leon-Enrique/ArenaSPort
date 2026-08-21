"""Prueba de editar una inscripcion (roster completo) despues de creada.

Cubre: el capitan edita mientras esta pendiente (se queda pendiente), edita
una ya aprobada (vuelve a pendiente, con aviso), un capitan de OTRO equipo
no puede editar la ajena, la elegibilidad no se dispara contra los propios
jugadores del equipo (editar sin cambios no falla), y el bloqueo total una
vez que el equipo ya fue colocado en una fase (tiene partidas generadas).
"""

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from probar_utils import headers_capitan, headers_organizador


def linea(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


def jugadores_de(nombre, cantidad=5, discord_capitan=None):
    return [
        {"identidad": {"nick": f"{nombre}{i}", "id_juego": str(hash(f"{nombre}{i}") % 10**8), "server": "2251"},
         "es_suplente": None, "es_capitan": i == 0,
         "discord_id": discord_capitan if i == 0 else None}
        for i in range(cantidad)
    ]


with TestClient(app) as c:
    db = SessionLocal()
    org = headers_organizador(db)
    db.close()

    mlbb = next(j for j in c.get("/api/juegos").json() if j["codigo"] == "mlbb")
    t = c.post("/api/torneos", json={"nombre": "Copa Editar"}, headers=org).json()
    e = c.post("/api/ediciones", json={
        "torneo_id": t["id"], "juego_id": mlbb["id"], "numero": 1, "nombre": "Ed Uno",
    }, headers=org).json()
    eid = e["id"]
    c.post(f"/api/ediciones/{eid}/estado", params={"estado": "inscripciones_abiertas"}, headers=org)

    r = c.post(f"/api/ediciones/{eid}/inscripciones", json={
        "nombre_equipo": "Halcones",
        "jugadores": jugadores_de("Halcon", discord_capitan="cap_halcones"),
    })
    insc_id = r.json()["inscripcion"]["id"]
    print("Inscripcion creada:", insc_id, "estado:", r.json()["inscripcion"]["estado"])

    db = SessionLocal()
    cap_halcones = headers_capitan(db, "cap_halcones")
    cap_otro = headers_capitan(db, "cap_otro_equipo")
    db.close()

    linea("EDITAR MIENTRAS ESTA PENDIENTE — se queda pendiente, sin aviso de re-revision")
    r = c.patch(f"/api/ediciones/{eid}/inscripciones/{insc_id}", json={
        "nombre_equipo": "Halcones FC",  # cambia el nombre
        "jugadores": jugadores_de("Halcon", discord_capitan="cap_halcones"),
    }, headers=cap_halcones)
    d = r.json()
    print(f"HTTP {r.status_code} | nombre: {d['inscripcion']['equipo']['nombre']} | "
          f"estado: {d['inscripcion']['estado']} | avisos: {d['avisos']}")
    assert r.status_code == 200
    assert d["inscripcion"]["equipo"]["nombre"] == "Halcones FC"
    assert d["inscripcion"]["estado"] == "pendiente"
    assert not any("volvió a" in a for a in d["avisos"])

    linea("UN CAPITAN DE OTRO EQUIPO NO PUEDE EDITAR ESTA INSCRIPCION")
    r = c.patch(f"/api/ediciones/{eid}/inscripciones/{insc_id}", json={
        "nombre_equipo": "Robado",
        "jugadores": jugadores_de("Halcon", discord_capitan="cap_halcones"),
    }, headers=cap_otro)
    print(f"HTTP {r.status_code}: {r.json()['detail']}")
    assert r.status_code == 403

    linea("SIN LOGIN NO SE PUEDE EDITAR")
    r = c.patch(f"/api/ediciones/{eid}/inscripciones/{insc_id}", json={
        "nombre_equipo": "Sin Login",
        "jugadores": jugadores_de("Halcon", discord_capitan="cap_halcones"),
    })
    print(f"HTTP {r.status_code}: {r.json()['detail']}")
    assert r.status_code == 401

    linea("APROBAR Y LUEGO EDITAR — vuelve a pendiente, con aviso")
    c.post(f"/api/ediciones/{eid}/inscripciones/{insc_id}/revisar", json={"estado": "aprobada"}, headers=org)
    estado_previo = c.get(f"/api/ediciones/{eid}/inscripciones/{insc_id}").json()["estado"]
    print("Estado tras aprobar:", estado_previo)
    assert estado_previo == "aprobada"

    r = c.patch(f"/api/ediciones/{eid}/inscripciones/{insc_id}", json={
        "nombre_equipo": "Halcones FC",
        "jugadores": jugadores_de("Halcon", discord_capitan="cap_halcones"),  # mismos jugadores, sin cambios reales
    }, headers=cap_halcones)
    d = r.json()
    print(f"HTTP {r.status_code} | estado: {d['inscripcion']['estado']}")
    for a in d["avisos"]:
        print("  AVISO:", a)
    assert d["inscripcion"]["estado"] == "pendiente"
    assert any("volvió a" in a for a in d["avisos"])
    print("(la elegibilidad NO se disparo contra los propios jugadores del equipo: OK)")

    linea("EDITAR CON UN CAMBIO DE ROSTER REAL — cambia un titular por otro nick")
    nuevos = jugadores_de("Halcon", discord_capitan="cap_halcones")
    nuevos[2]["identidad"]["nick"] = "SuplenteNuevo"
    nuevos[2]["identidad"]["id_juego"] = "999999"
    r = c.patch(f"/api/ediciones/{eid}/inscripciones/{insc_id}", json={
        "nombre_equipo": "Halcones FC",
        "jugadores": nuevos,
    }, headers=cap_halcones)
    d = r.json()
    nombres = [j["identidad"]["nick"] for j in d["inscripcion"]["jugadores"]]
    print(f"HTTP {r.status_code} | roster ahora: {nombres}")
    assert "SuplenteNuevo" in nombres

    linea("APROBAR DE NUEVO Y SORTEAR — el equipo queda colocado en una fase")
    c.post(f"/api/ediciones/{eid}/inscripciones/{insc_id}/revisar", json={"estado": "aprobada"}, headers=org)

    # Necesita al menos otro equipo aprobado para poder sortear una llave de 2
    r2 = c.post(f"/api/ediciones/{eid}/inscripciones", json={
        "nombre_equipo": "Serpientes",
        "jugadores": jugadores_de("Serpiente", discord_capitan="cap_serpientes"),
    })
    insc2_id = r2.json()["inscripcion"]["id"]
    c.post(f"/api/ediciones/{eid}/inscripciones/{insc2_id}/revisar", json={"estado": "aprobada"}, headers=org)

    c.post(f"/api/ediciones/{eid}/inscripciones/sembrar-automatico", params={"semilla": 1}, headers=org)
    fase = c.post(f"/api/ediciones/{eid}/fases", json={
        "orden": 1, "nombre": "Llave", "modelo_competencia": "enfrentamiento_directo",
        "formato": "eliminacion_simple",
    }, headers=org).json()
    c.post(f"/api/ediciones/{eid}/fases/{fase['id']}/sortear", headers=org)
    print("Llave sorteada — Halcones FC ya tiene una partida generada.")

    linea("YA NO SE PUEDE EDITAR — el equipo ya fue colocado en una fase")
    r = c.patch(f"/api/ediciones/{eid}/inscripciones/{insc_id}", json={
        "nombre_equipo": "Intento Tardio",
        "jugadores": jugadores_de("Halcon", discord_capitan="cap_halcones"),
    }, headers=cap_halcones)
    print(f"HTTP {r.status_code}: {r.json()['detail'][:90]}...")
    assert r.status_code == 409

    r_org = c.patch(f"/api/ediciones/{eid}/inscripciones/{insc_id}", json={
        "nombre_equipo": "Ni el organizador puede por este camino",
        "jugadores": jugadores_de("Halcon", discord_capitan="cap_halcones"),
    }, headers=org)
    print(f"Ni el organizador puede por este endpoint una vez colocado -> HTTP {r_org.status_code}")
    assert r_org.status_code == 409

print("\n" + "=" * 70)
print("TODAS LAS PRUEBAS DE EDICION DE INSCRIPCION PASARON")
print("=" * 70)
