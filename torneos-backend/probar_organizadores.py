"""Prueba de la gestion de organizadores en dos niveles: es_organizador
(opera el torneo) y puede_gestionar_organizadores (toca la lista en si).

Cubre: promover a un segundo organizador, que ese organizador NUEVO no
puede tocar la lista de organizadores (solo quien tiene el segundo nivel
puede), las dos invariantes de seguridad (no quedarse sin organizadores
activos, no quedarse sin nadie que pueda gestionar organizadores), y que
un organizador promovido si puede hacer todo lo operativo del torneo.
"""

from fastapi.testclient import TestClient

from app.db.database import SessionLocal
from app.main import app
from app.core.security_dev import token_de_prueba, usuario_de_prueba
from probar_utils import headers_capitan, headers_organizador, headers_organizador_limitado


def linea(t):
    print(f"\n{'=' * 70}\n{t}\n{'=' * 70}")


with TestClient(app) as c:
    db = SessionLocal()
    # org1 = el fundador: tiene los dos niveles, como si hubiera arrancado
    # la plataforma via DISCORD_IDS_ORGANIZADORES_INICIALES.
    org1 = headers_organizador(db, discord_id="org_uno")

    # un usuario que ya inicio sesion pero todavia no es organizador de nada
    usuario_de_prueba(db, discord_id="futuro_org", es_organizador=False, username="FuturoOrganizador")
    token_futuro = token_de_prueba(db, discord_id="futuro_org", es_organizador=False)
    headers_futuro = {"Authorization": f"Bearer {token_futuro}"}

    cap = headers_capitan(db, "capitan_cualquiera")
    db.close()

    linea("LISTAR USUARIOS — exige puede_gestionar_organizadores, no solo es_organizador")
    r = c.get("/api/usuarios")
    print(f"Sin login -> HTTP {r.status_code}: {r.json()['detail']}")

    r = c.get("/api/usuarios", headers=cap)
    print(f"Con capitan (no organizador) -> HTTP {r.status_code}: {r.json()['detail']}")

    r = c.get("/api/usuarios", headers=org1)
    usuarios = r.json()
    print(f"Con el fundador (org1) -> HTTP {r.status_code}, {len(usuarios)} usuarios")
    for u in usuarios:
        print(f"  {u['discord_username']:20} organizador={u['es_organizador']} "
              f"gestiona_organizadores={u['puede_gestionar_organizadores']}")

    linea("PROMOVER A UN SEGUNDO ORGANIZADOR — sin el segundo nivel por defecto")
    futuro = next(u for u in usuarios if u["discord_id"] == "futuro_org")

    r = c.patch(f"/api/usuarios/{futuro['id']}/rol", json={"es_organizador": True}, headers=org1)
    d = r.json()
    print(f"El fundador promueve -> HTTP {r.status_code}, es_organizador={d['es_organizador']}, "
          f"gestiona_organizadores={d['puede_gestionar_organizadores']}")
    assert d["es_organizador"] is True
    assert d["puede_gestionar_organizadores"] is False, \
        "Un organizador recien promovido NO deberia tener el segundo nivel por defecto"

    linea("EL ORGANIZADOR NUEVO PUEDE OPERAR EL TORNEO...")
    r = c.post("/api/torneos", json={"nombre": "Torneo del organizador nuevo"}, headers=headers_futuro)
    print(f"Crear torneo -> HTTP {r.status_code}")
    assert r.status_code == 201

    linea("...PERO NO PUEDE TOCAR LA LISTA DE ORGANIZADORES")
    r = c.get("/api/usuarios", headers=headers_futuro)
    print(f"Listar usuarios -> HTTP {r.status_code}: {r.json()['detail']}")
    assert r.status_code == 403

    r = c.patch(f"/api/usuarios/{futuro['id']}/rol", json={"es_organizador": False}, headers=headers_futuro)
    print(f"Intentar sacarse el rol a si mismo -> HTTP {r.status_code}: {r.json()['detail']}")
    assert r.status_code == 403

    linea("EL FUNDADOR PUEDE DARLE EL SEGUNDO NIVEL A ALGUIEN MAS")
    r = c.patch(
        f"/api/usuarios/{futuro['id']}/rol",
        json={"es_organizador": True, "puede_gestionar_organizadores": True},
        headers=org1,
    )
    d = r.json()
    print(f"Otorgar gestion de organizadores -> HTTP {r.status_code}, "
          f"gestiona_organizadores={d['puede_gestionar_organizadores']}")
    assert d["puede_gestionar_organizadores"] is True

    print("Ahora el organizador nuevo SI puede listar usuarios:")
    r = c.get("/api/usuarios", headers=headers_futuro)
    print(f"  -> HTTP {r.status_code}, {len(r.json())} usuarios")
    assert r.status_code == 200

    linea("INVARIANTES DE SEGURIDAD — como 'gestionar organizadores' implica")
    print("'ser organizador' (la cascada lo garantiza), la protección de 'no quedarse")
    print("sin ningún gestor' es siempre al menos tan estricta como 'no quedarse sin")
    print("ningún organizador' — por eso es la que dispara primero en la práctica.")
    print()
    # Sacarle es_organizador al segundo (que ya tiene el segundo nivel tambien)
    r = c.patch(f"/api/usuarios/{futuro['id']}/rol", json={"es_organizador": False}, headers=org1)
    print(f"Sacarle el rol al segundo -> HTTP {r.status_code}")
    assert r.status_code == 200

    usuarios_ahora = c.get("/api/usuarios", headers=org1).json()
    org1_id = next(u["id"] for u in usuarios_ahora if u["discord_id"] == "org_uno")

    r = c.patch(f"/api/usuarios/{org1_id}/rol", json={"es_organizador": False}, headers=org1)
    print(f"org1 intenta sacarse el rol a si mismo (quedaria en 0 organizadores Y 0 gestores) -> "
          f"HTTP {r.status_code}: {r.json()['detail'][:60]}...")
    assert r.status_code == 409

    linea("MISMA INVARIANTE, ahora tocando directamente el segundo nivel")
    # Le devolvemos ambos niveles al segundo para poder probar esta invariante con org1 como unico
    c.patch(f"/api/usuarios/{futuro['id']}/rol",
            json={"es_organizador": True, "puede_gestionar_organizadores": False}, headers=org1)

    r = c.patch(f"/api/usuarios/{org1_id}/rol",
                json={"es_organizador": True, "puede_gestionar_organizadores": False}, headers=org1)
    print(f"org1 intenta sacarse el segundo nivel a si mismo (quedaria en 0 gestores) -> "
          f"HTTP {r.status_code}: {r.json()['detail'][:60]}...")
    assert r.status_code == 409

    linea("VALIDACION: no se puede dar el segundo nivel a alguien que deja de ser organizador")
    r = c.patch(
        f"/api/usuarios/{futuro['id']}/rol",
        json={"es_organizador": False, "puede_gestionar_organizadores": True},
        headers=org1,
    )
    print(f"HTTP {r.status_code}: {r.json()['detail']}")
    assert r.status_code == 422

    linea("USUARIO INEXISTENTE")
    r = c.patch("/api/usuarios/99999/rol", json={"es_organizador": True}, headers=org1)
    print(f"HTTP {r.status_code}: {r.json()['detail']}")
    assert r.status_code == 404

print("\n" + "=" * 70)
print("TODAS LAS PRUEBAS DE ORGANIZADORES PASARON")
print("=" * 70)
