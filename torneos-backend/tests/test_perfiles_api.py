"""Perfiles públicos de equipo y jugador, sobre los endpoints reales.

Dos cosas se vigilan acá con especial cuidado:

  - Que el récord acumulado cruce ediciones de verdad. Es el punto de la
    funcionalidad: hasta ahora cada inscripción vivía aislada en su torneo.
  - Que el `discord_id` no salga nunca. El endpoint es público y sin
    autenticación, y ese campo identifica a una persona real. Es el tipo de
    filtración que no rompe nada visible y por eso nadie nota.
"""

import pytest
from fastapi.testclient import TestClient

from app.domain.enums import (
    EstadoInscripcion,
    EstadoPartida,
    FormatoFase,
    ModeloCompetencia,
)
from app.main import app
from app.models import (
    Edicion,
    Equipo,
    Fase,
    Inscripcion,
    Jugador,
    Juego,
    Partida,
    ParticipacionEnPartida,
    Torneo,
)


@pytest.fixture
def cliente(db):
    from app.db.database import get_db

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def historia(db):
    """Un equipo con dos torneos jugados: campeón en el primero, eliminado
    en semifinales del segundo. Es lo mínimo para que 'historial entre
    torneos' signifique algo."""
    juego = Juego(
        codigo="mlbb",
        nombre="Mobile Legends",
        modelo_competencia_default=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
        titulares_requeridos=1,
        suplentes_maximos=0,
        campos_identidad={
            "campos": [{"nombre": "nick", "etiqueta": "Nick", "requerido": True}],
            "clave_unica": ["nick"],
        },
    )
    db.add(juego)
    db.flush()

    torneo = Torneo(nombre="Copa Anual", slug="copa-anual")
    db.add(torneo)
    db.flush()

    dragons = Equipo(nombre="Dragons", tag="DRG")
    rival = Equipo(nombre="Wolves", tag="WLV")
    db.add_all([dragons, rival])
    db.flush()

    ediciones = {}
    for numero, nombre in ((1, "Temporada 1"), (2, "Temporada 2")):
        edicion = Edicion(
            torneo_id=torneo.id, juego_id=juego.id, numero=numero,
            nombre=nombre, slug=f"copa-anual-t{numero}",
        )
        db.add(edicion)
        db.flush()
        fase = Fase(
            edicion_id=edicion.id, orden=1, nombre="Llave",
            modelo_competencia=ModeloCompetencia.ENFRENTAMIENTO_DIRECTO,
            formato=FormatoFase.ELIMINACION_SIMPLE, config={"bo": 3},
        )
        db.add(fase)
        db.flush()

        for equipo, discord in ((dragons, "discord-capitan-dragons"), (rival, None)):
            inscripcion = Inscripcion(
                edicion_id=edicion.id, equipo_id=equipo.id,
                estado=EstadoInscripcion.APROBADA,
            )
            db.add(inscripcion)
            db.flush()
            db.add(Jugador(
                inscripcion_id=inscripcion.id, edicion_id=edicion.id,
                identidad={"nick": f"cap_{equipo.tag}"},
                clave_identidad=f"cap_{equipo.tag}".lower(),
                es_capitan=True, discord_id=discord,
            ))
        ediciones[numero] = (edicion, fase)

    def jugar(fase, ronda, ganador, perdedor, mapas_g, mapas_p, estado=EstadoPartida.CONFIRMADA):
        partida = Partida(fase_id=fase.id, ronda=ronda, estado=estado)
        db.add(partida)
        db.flush()
        db.add_all([
            ParticipacionEnPartida(
                partida_id=partida.id, equipo_id=ganador.id, slot=0,
                es_ganador=True, mapas_ganados=mapas_g,
            ),
            ParticipacionEnPartida(
                partida_id=partida.id, equipo_id=perdedor.id, slot=1,
                es_ganador=False, mapas_ganados=mapas_p,
            ),
        ])
        return partida

    # Temporada 1: Dragons gana la final (ronda 2) -> campeón.
    ed1, fase1 = ediciones[1]
    jugar(fase1, 1, dragons, rival, 2, 0)
    jugar(fase1, 2, dragons, rival, 2, 1)

    # Temporada 2: gana la semi (ronda 1) y pierde la final (ronda 2).
    ed2, fase2 = ediciones[2]
    jugar(fase2, 1, dragons, rival, 2, 0)
    jugar(fase2, 2, rival, dragons, 2, 1)

    db.commit()
    return {
        "juego": juego,
        "dragons": dragons,
        "rival": rival,
        "edicion_1": ed1,
        "edicion_2": ed2,
        "fase_2": fase2,
    }


class TestPerfilDeEquipo:
    def test_un_equipo_inexistente_da_404(self, cliente):
        assert cliente.get("/api/equipos/9999").status_code == 404

    def test_es_publico(self, cliente, historia):
        """Sin token: es la vitrina del torneo."""
        assert cliente.get(f"/api/equipos/{historia['dragons'].id}").status_code == 200

    def test_el_record_acumula_entre_torneos(self, cliente, historia):
        """El punto de la funcionalidad: 4 partidas repartidas en dos
        ediciones distintas tienen que sumar en un solo récord."""
        r = cliente.get(f"/api/equipos/{historia['dragons'].id}").json()
        assert r["record_global"]["jugadas"] == 4
        assert r["record_global"]["ganadas"] == 3
        assert r["record_global"]["perdidas"] == 1
        assert r["record_global"]["porcentaje_victorias"] == 75.0

    def test_suma_los_mapas_de_todas_las_ediciones(self, cliente, historia):
        r = cliente.get(f"/api/equipos/{historia['dragons'].id}").json()
        # ganadas 2+2+2, perdida 1 -> 7 a favor; en contra 0+1+0+2 = 3
        assert r["record_global"]["mapas_favor"] == 7
        assert r["record_global"]["mapas_contra"] == 3
        assert r["record_global"]["diferencia_mapas"] == 4

    def test_cuenta_los_torneos_jugados(self, cliente, historia):
        r = cliente.get(f"/api/equipos/{historia['dragons'].id}").json()
        assert r["torneos_jugados"] == 2
        assert len(r["historial"]) == 2

    def test_reconoce_el_titulo(self, cliente, historia):
        r = cliente.get(f"/api/equipos/{historia['dragons'].id}").json()
        assert r["titulos"] == 1
        por_edicion = {h["edicion_id"]: h for h in r["historial"]}
        assert por_edicion[historia["edicion_1"].id]["campeon"] is True
        assert por_edicion[historia["edicion_2"].id]["campeon"] is False

    def test_perder_la_final_no_cuenta_como_titulo(self, cliente, historia):
        """El finalista llegó igual de lejos que el campeón: si no se
        distinguiera por haber ganado la última partida, los dos figurarían
        como campeones."""
        r = cliente.get(f"/api/equipos/{historia['rival'].id}").json()
        assert r["titulos"] == 1  # gano la final de la temporada 2
        por_edicion = {h["edicion_id"]: h for h in r["historial"]}
        assert por_edicion[historia["edicion_1"].id]["campeon"] is False

    def test_el_historial_arranca_por_lo_mas_reciente(self, cliente, historia):
        r = cliente.get(f"/api/equipos/{historia['dragons'].id}").json()
        assert r["historial"][0]["edicion_id"] == historia["edicion_2"].id

    def test_cada_torneo_trae_su_propio_record(self, cliente, historia):
        r = cliente.get(f"/api/equipos/{historia['dragons'].id}").json()
        por_edicion = {h["edicion_id"]: h for h in r["historial"]}
        assert por_edicion[historia["edicion_1"].id]["record"]["ganadas"] == 2
        assert por_edicion[historia["edicion_2"].id]["record"]["ganadas"] == 1
        assert por_edicion[historia["edicion_2"].id]["record"]["perdidas"] == 1

    def test_trae_el_nombre_del_torneo_y_del_juego(self, cliente, historia):
        r = cliente.get(f"/api/equipos/{historia['dragons'].id}").json()
        assert r["historial"][0]["torneo_nombre"] == "Copa Anual"
        assert r["historial"][0]["juego_nombre"] == "Mobile Legends"

    def test_un_equipo_sin_partidas_no_rompe(self, cliente, db, historia):
        """Recién inscrito, todavía sin jugar: tiene que responder con el
        récord en cero, no fallar."""
        nuevo = Equipo(nombre="Novatos")
        db.add(nuevo)
        db.commit()

        r = cliente.get(f"/api/equipos/{nuevo.id}")
        assert r.status_code == 200
        assert r.json()["record_global"]["jugadas"] == 0
        assert r.json()["record_global"]["porcentaje_victorias"] is None
        assert r.json()["historial"] == []


class TestPrivacidad:
    def test_el_roster_no_expone_el_discord_id(self, cliente, historia):
        """Este endpoint es público y sin token. El discord_id identifica a
        una persona real, a veces menor de edad."""
        r = cliente.get(f"/api/equipos/{historia['dragons'].id}")
        assert "discord-capitan-dragons" not in r.text
        assert "discord_id" not in r.text

    def test_el_perfil_de_jugador_tampoco(self, cliente, historia):
        r = cliente.get(f"/api/jugadores/mlbb/cap_drg")
        assert r.status_code == 200
        assert "discord" not in r.text.lower()

    def test_el_roster_si_muestra_los_nicks(self, cliente, historia):
        """Lo que sí es público: el nick de juego, que es el nombre con el
        que compite."""
        r = cliente.get(f"/api/equipos/{historia['dragons'].id}").json()
        roster = r["historial"][0]["roster"]
        assert roster and roster[0]["nick"] == "cap_DRG"
        assert roster[0]["es_capitan"] is True


class TestListadoDeEquipos:
    def test_lista_los_equipos_con_inscripcion_aprobada(self, cliente, historia):
        r = cliente.get("/api/equipos").json()
        nombres = {e["nombre"] for e in r}
        assert {"Dragons", "Wolves"} <= nombres

    def test_no_lista_equipos_sin_inscripcion_aprobada(self, cliente, db, historia):
        """Un equipo rechazado no es parte de la vitrina."""
        fantasma = Equipo(nombre="Rechazados FC")
        db.add(fantasma)
        db.flush()
        db.add(Inscripcion(
            edicion_id=historia["edicion_1"].id, equipo_id=fantasma.id,
            estado=EstadoInscripcion.RECHAZADA,
        ))
        db.commit()

        nombres = {e["nombre"] for e in cliente.get("/api/equipos").json()}
        assert "Rechazados FC" not in nombres

    def test_busca_por_nombre(self, cliente, historia):
        r = cliente.get("/api/equipos", params={"buscar": "drag"}).json()
        assert [e["nombre"] for e in r] == ["Dragons"]

    def test_busca_por_tag(self, cliente, historia):
        r = cliente.get("/api/equipos", params={"buscar": "WLV"}).json()
        assert [e["nombre"] for e in r] == ["Wolves"]

    def test_una_busqueda_sin_resultados_devuelve_vacio(self, cliente, historia):
        assert cliente.get("/api/equipos", params={"buscar": "zzzz"}).json() == []

    def test_cada_equipo_aparece_una_sola_vez(self, cliente, historia):
        """Dragons tiene dos inscripciones aprobadas: el join no puede
        duplicarlo en el listado."""
        r = cliente.get("/api/equipos").json()
        ids = [e["id"] for e in r]
        assert len(ids) == len(set(ids))

    def test_informa_torneos_y_victorias(self, cliente, historia):
        r = cliente.get("/api/equipos", params={"buscar": "Dragons"}).json()
        assert r[0]["torneos_jugados"] == 2
        assert r[0]["partidas_ganadas"] == 3


class TestPerfilDeJugador:
    def test_un_juego_inexistente_da_404(self, cliente, historia):
        assert cliente.get("/api/jugadores/inventado/cap_drg").status_code == 404

    def test_una_identidad_inexistente_da_404(self, cliente, historia):
        assert cliente.get("/api/jugadores/mlbb/nadie").status_code == 404

    def test_devuelve_la_carrera_del_jugador(self, cliente, historia):
        r = cliente.get("/api/jugadores/mlbb/cap_drg").json()
        assert r["torneos_jugados"] == 2
        assert len(r["equipos"]) == 2
        assert all(e["equipo_nombre"] == "Dragons" for e in r["equipos"])

    def test_informa_los_nicks_usados(self, cliente, historia):
        r = cliente.get("/api/jugadores/mlbb/cap_drg").json()
        assert r["nicks_usados"] == ["cap_DRG"]

    def test_marca_al_capitan(self, cliente, historia):
        r = cliente.get("/api/jugadores/mlbb/cap_drg").json()
        assert all(e["es_capitan"] for e in r["equipos"])
