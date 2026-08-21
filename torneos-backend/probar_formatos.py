"""Valida los generadores de formato SIN tocar la base de datos.

Simula un torneo completo resolviendo cada cruce con un "ganador aleatorio
determinista" y verifica que la estructura converge a exactamente un
campeón, sin cruces huérfanos ni referencias rotas.
"""

import random

from app.domain.formatos import eliminacion_doble, eliminacion_simple, round_robin, suizo
from app.domain.formatos.base import TipoFuente


def simular_bracket(nombre: str, equipos: list[int], generador) -> None:
    resultado = generador(equipos)
    por_indice = {c.indice: c for c in resultado.cruces}

    # Resolver ganador/perdedor de cada cruce en orden (las fuentes solo
    # apuntan hacia atrás, así que resolver en orden de índice alcanza).
    ganador_de: dict[int, int] = {}
    perdedor_de: dict[int, int] = {}

    def resolver_fuente(f) -> int:
        if f.tipo == TipoFuente.EQUIPO:
            return f.valor
        if f.tipo == TipoFuente.GANADOR_DE:
            return ganador_de[f.valor]
        if f.tipo == TipoFuente.PERDEDOR_DE:
            return perdedor_de[f.valor]
        raise AssertionError(f"Fuente VACIO no debería resolverse: {f}")

    rng = random.Random(42)
    for c in sorted(resultado.cruces, key=lambda c: c.indice):
        if c.es_bye:
            # Bye: el lado no-VACIO gana automaticamente.
            if c.fuente_a.tipo != TipoFuente.VACIO:
                ganador_de[c.indice] = resolver_fuente(c.fuente_a)
            else:
                ganador_de[c.indice] = resolver_fuente(c.fuente_b)
            continue
        a = resolver_fuente(c.fuente_a)
        b = resolver_fuente(c.fuente_b)
        assert a != b, f"Cruce {c.indice} enfrenta al mismo equipo consigo mismo: {a}"
        gana = rng.choice([a, b])
        pierde = b if gana == a else a
        ganador_de[c.indice] = gana
        perdedor_de[c.indice] = pierde

    ultimo = max(resultado.cruces, key=lambda c: c.indice)
    campeon = ganador_de[ultimo.indice]

    n = len(equipos)
    reales = [c for c in resultado.cruces if not c.es_bye]
    print(f"[{nombre}] n={n:3}  cruces_totales={len(resultado.cruces):3}  "
          f"reales={len(reales):3}  rondas={resultado.total_rondas}  "
          f"campeon=equipo_{campeon}  OK")


print("=" * 70)
print("ELIMINACION SIMPLE")
print("=" * 70)
for n in [2, 3, 4, 5, 6, 7, 8, 11, 16, 17, 45]:
    equipos = list(range(1, n + 1))
    simular_bracket("simple", equipos, eliminacion_simple.generar)
    resultado = eliminacion_simple.generar(equipos)
    assert len([c for c in resultado.cruces if not c.es_bye]) == n - 1, \
        f"n={n}: se esperaban {n-1} partidas reales"

print()
print("=" * 70)
print("ELIMINACION DOBLE")
print("=" * 70)
for n in [3, 4, 5, 6, 7, 8, 9, 11, 13, 16, 17, 24, 32, 45, 48, 64]:
    equipos = list(range(1, n + 1))
    simular_bracket("doble", equipos, eliminacion_doble.generar)
    resultado = eliminacion_doble.generar(equipos)
    reales = len([c for c in resultado.cruces if not c.es_bye])
    esperado = 2 * n - 2
    assert reales == esperado, f"n={n}: se esperaban {esperado} partidas reales, hubo {reales}"

print()
print("=" * 70)
print("ROUND ROBIN Y GRUPOS")
print("=" * 70)
equipos = list(range(1, 13))
grupos = round_robin.dividir_en_grupos(equipos, 4)
for i, g in enumerate(grupos):
    print(f"Grupo {chr(65+i)}: {g}")
total_partidos = 0
for g in grupos:
    partidos = round_robin.generar_partidos_grupo(g)
    total_partidos += len(partidos)
    print(f"  {len(g)} equipos -> {len(partidos)} partidos: {partidos}")
print(f"Total partidos en los 4 grupos: {total_partidos}")

print()
print("=" * 70)
print("SUIZO")
print("=" * 70)
equipos = list(range(1, 9))
r1, bye = suizo.generar_ronda_1(equipos)
print("Ronda 1 (siembra mitad sup vs mitad inf):", r1, "| bye:", bye)

equipos_impar = list(range(1, 8))  # 7 equipos
r1_impar, bye_impar = suizo.generar_ronda_1(equipos_impar)
print("Ronda 1 con 7 equipos (impar):", r1_impar, "| bye:", bye_impar)
assert bye_impar == 7, "El bye deberia ser el peor sembrado (ultimo de la lista)"
assert len(r1_impar) == 3, "Deberian quedar 3 pares con los 6 equipos restantes"

tabla = [
    suizo.EquipoConPuntaje(equipo_id=1, puntos=3),
    suizo.EquipoConPuntaje(equipo_id=5, puntos=3),
    suizo.EquipoConPuntaje(equipo_id=2, puntos=0),
    suizo.EquipoConPuntaje(equipo_id=6, puntos=0),
    suizo.EquipoConPuntaje(equipo_id=3, puntos=3),
    suizo.EquipoConPuntaje(equipo_id=7, puntos=3),
    suizo.EquipoConPuntaje(equipo_id=4, puntos=0),
    suizo.EquipoConPuntaje(equipo_id=8, puntos=0),
]
previos = {(1, 5), (2, 6), (3, 7), (4, 8)}
r2 = suizo.generar_siguiente_ronda(tabla, previos)
print("Ronda 2 (por puntaje, evitando repetir ronda 1):", r2)
for a, b in r2:
    clave = (min(a, b), max(a, b))
    assert clave not in previos, f"Se repitio un enfrentamiento: {clave}"
print("Sin rivales repetidos: OK")

print("\nTodas las validaciones pasaron.")
