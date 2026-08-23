"""Catálogo de juegos: qué se ofrece y qué está en pausa.

La plataforma se enfoca hoy solo en Mobile Legends. Los otros juegos quedan
definidos pero apagados — en particular los de battle royale, que estaban
ofrecidos en el catálogo cuando el motor no sabe correrlos: no hay generador
de caídas multi-equipo, `calcular_tabla` solo entiende cruces de a dos, y
ningún endpoint escribe `posicion` ni `bajas`. Un organizador llegaba a
sortear y recién ahí se encontraba con que no podía cargar un resultado.
"""

import pytest
from fastapi.testclient import TestClient

from app.db.seed import JUEGOS, JUEGOS_EN_PAUSA, sembrar_juegos
from app.domain.enums import ModeloCompetencia
from app.main import app
from app.models import Edicion, Juego, Torneo


@pytest.fixture
def cliente(db):
    from app.db.database import get_db

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestQueSeSiembra:
    def test_solo_se_siembra_mobile_legends(self, db):
        sembrar_juegos(db)
        codigos = [j.codigo for j in db.query(Juego).all()]
        assert codigos == ["mlbb"]

    def test_es_idempotente(self, db):
        assert sembrar_juegos(db) == 1
        assert sembrar_juegos(db) == 0
        assert db.query(Juego).count() == 1

    def test_ningun_juego_activo_es_multi_equipo(self, db):
        """El motor no sabe correr battle royale: ofrecer un juego así en el
        catálogo es prometer algo que después no se puede cumplir."""
        sembrar_juegos(db)
        activos = db.query(Juego).filter(Juego.esta_activo.is_(True)).all()
        assert all(
            j.modelo_competencia_default == ModeloCompetencia.ENFRENTAMIENTO_DIRECTO
            for j in activos
        )

    def test_las_dos_listas_no_se_pisan(self):
        activos = {j["codigo"] for j in JUEGOS}
        pausados = {j["codigo"] for j in JUEGOS_EN_PAUSA}
        assert activos & pausados == set()


class TestPausar:
    def test_un_juego_ya_cargado_queda_desactivado(self, db):
        """El caso real de esta base: los juegos ya existían activos de antes,
        así que no alcanza con dejar de sembrarlos."""
        db.add(Juego(**JUEGOS_EN_PAUSA[0]))
        db.commit()

        sembrar_juegos(db)

        pausado = db.query(Juego).filter(Juego.codigo == JUEGOS_EN_PAUSA[0]["codigo"]).one()
        assert pausado.esta_activo is False

    def test_pausar_no_borra_el_juego_ni_su_historia(self, db):
        """Sacarlo del catálogo no puede llevarse por delante los torneos que
        ya se jugaron con él."""
        juego = Juego(**JUEGOS_EN_PAUSA[0])
        db.add(juego)
        db.flush()
        torneo = Torneo(nombre="Copa Vieja", slug="copa-vieja")
        db.add(torneo)
        db.flush()
        db.add(Edicion(
            torneo_id=torneo.id, juego_id=juego.id, numero=1,
            nombre="Edicion Vieja", slug="copa-vieja-1",
        ))
        db.commit()

        sembrar_juegos(db)

        assert db.query(Juego).filter(Juego.codigo == JUEGOS_EN_PAUSA[0]["codigo"]).count() == 1
        assert db.query(Edicion).count() == 1

    def test_mlbb_se_reactiva_si_estaba_apagado(self, db):
        from app.db.seed import MLBB

        db.add(Juego(**{**MLBB, "esta_activo": False}))
        db.commit()

        sembrar_juegos(db)

        assert db.query(Juego).filter(Juego.codigo == "mlbb").one().esta_activo is True


class TestCatalogoPublico:
    def test_el_endpoint_solo_ofrece_mlbb(self, cliente, db):
        for datos in JUEGOS_EN_PAUSA:
            db.add(Juego(**datos))
        db.flush()
        sembrar_juegos(db)

        r = cliente.get("/api/juegos")
        assert r.status_code == 200
        assert [j["codigo"] for j in r.json()] == ["mlbb"]

    def test_no_se_puede_crear_una_edicion_de_un_juego_pausado(self, cliente, db):
        """Que no aparezca en el selector no alcanza: el id sigue existiendo y
        alguien podría mandarlo a mano."""
        pausado = Juego(**JUEGOS_EN_PAUSA[0])
        db.add(pausado)
        db.flush()
        sembrar_juegos(db)
        db.commit()

        torneo = Torneo(nombre="Copa X", slug="copa-x")
        db.add(torneo)
        db.commit()

        from app.core.security import crear_access_token
        from app.models import Usuario

        org = Usuario(discord_id="org", discord_username="Org", es_organizador=True)
        db.add(org)
        db.commit()
        headers = {"Authorization": f"Bearer {crear_access_token(org.id, org.discord_id, True)}"}

        r = cliente.post(
            "/api/ediciones",
            json={"torneo_id": torneo.id, "juego_id": pausado.id, "numero": 1, "nombre": "Prueba"},
            headers=headers,
        )
        assert r.status_code == 422, r.text
