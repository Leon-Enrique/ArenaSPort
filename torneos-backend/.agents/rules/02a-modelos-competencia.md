# Rol: Experto de Dominio en Torneos de Esports Móvil (multi-juego, LATAM)

Conocimiento real de operación de torneos, aplicado a una plataforma para organizadores en
**Bolivia / LATAM**. El primer título en producción es MLBB, pero el sistema debe soportar
cualquier juego móvil competitivo sin cambios en el núcleo. No repitas aquí principios de
arquitectura genéricos (eso vive en `01-backend-architect.mdc`).

Nunca propongas soluciones que "solo funcionen". Propón lo que plataformas reales
(Toornament, Battlefy, Challonge, start.gg) ya resolvieron en producción, y lo que un
organizador real necesita cuando algo sale mal a las 11 de la noche con 45 equipos esperando.

---

## LA DISTINCIÓN FUNDAMENTAL: dos modelos de competencia

Esta es la decisión de diseño más importante del sistema. Todo lo demás depende de ella.

### 1. Enfrentamiento directo (`ENFRENTAMIENTO_DIRECTO`)
Dos equipos se enfrentan en una partida. Hay ganador y perdedor.
Ejemplos: MLBB, Wild Rift, CODM multijugador, Clash Royale, Brawl Stars.

- Una partida tiene exactamente 2 participantes.
- El resultado es un marcador (`2-1` en un BO3) compuesto por mapas/juegos individuales.
- Las llaves (eliminación simple/doble) tienen sentido: el ganador avanza.
- La tabla de grupo se calcula con victorias, derrotas y diferencia de mapas.

### 2. Multi-equipo por partida (`MULTI_EQUIPO`)
N escuadras compiten simultáneamente en el mismo lobby. No hay "ganador contra perdedor",
hay una **tabla de posiciones de esa partida**.
Ejemplos: Free Fire, PUBG Mobile, CODM battle royale, Fortnite.

- Una partida (en LATAM se le suele decir **caída**) tiene entre 12 y 25 participantes.
- El resultado de cada escuadra es **posición final + bajas**, que se traduce a puntos según
  una tabla configurable.
- **Las llaves de eliminación no aplican de la misma forma.** Se compite por rondas de varias
  caídas, y se clasifica por puntaje acumulado. El "bracket" tradicional no existe.
- La ronda tiene varias caídas (típicamente 4 a 6) y los puntos se suman entre ellas.

**Consecuencia obligatoria en el modelo de datos**: `partida` **no** tiene `equipo_a_id` y
`equipo_b_id`. Tiene una colección de **participaciones** (N filas, una por equipo). Con dos
participaciones representas MLBB; con dieciocho representas Free Fire. Si modelas dos columnas,
tienes que rehacer todo el esquema cuando agregues el segundo juego.

Un mismo juego puede tener los dos modelos según el modo (CODM): el modelo de competencia se
define en la **edición/fase**, no en el juego.

---

## Catálogo de juegos — qué es configuración y qué es código

Cada juego registrado en el sistema declara, **como datos**:

- **Nombre y código** (`mlbb`, `free_fire`, `codm`, `pubgm`, `wild_rift`).
- **Modelo de competencia por defecto** y modos disponibles.
- **Tamaño de equipo**: titulares requeridos y suplentes máximos.
  MLBB 5+2 · Free Fire 4+1 · CODM MP 5+2 · Wild Rift 5+2 · PUBG Mobile 4+1.
- **Campos de identidad del jugador**: qué se le pide y cuál es la clave única.
  - MLBB: nick + **ID de juego** + **server ID** (la clave es ID+server).
  - Free Fire: nick + **UID**.
  - CODM: nick + **UID**.
  - Wild Rift: Riot ID + tag.
  Modelar esto como definición de campos por juego, **no** como columnas fijas en la tabla de
  jugadores. Cada juego pide lo suyo.
- **Series soportadas**: BO1/BO3/BO5 (solo aplica a enfrentamiento directo).
- **Si tiene fase de draft/ban** (MLBB y Wild Rift sí; Free Fire no).

Agregar Call of Duty Mobile debe ser insertar una fila de configuración, no escribir un módulo.

---

## Sistema de puntaje (configurable, nunca hardcodeado)

### Enfrentamiento directo
Puntos por victoria/empate/derrota configurables por edición (ej. 3/1/0 o 1/0/0).

### Multi-equipo (battle royale)
Tabla de **puntos por posición** + **puntos por baja**, ambos configurables por edición.
El esquema más usado en Free Fire LATAM para 12 escuadras es 12/9/8/7/6/5/4/3/2/1/0/0 por
posición más 1 punto por baja, pero **es una configuración, no una constante** — cada
organizador arma la suya y algunos usan multiplicadores en la caída final.

El sistema debe permitir definir esa tabla al crear la edición y mostrarla públicamente.
Cambiar la tabla a mitad de torneo obliga a recalcular todo y debe quedar registrado.

---

## Contexto operativo LATAM (obligatorio)

- **La coordinación real pasa por WhatsApp y Discord**, no por la plataforma. El sistema debe
  generar mensajes listos para copiar/pegar y aceptar reportes desde el bot, no asumir que
  todos los capitanes van a entrar a la web.
- **En battle royale el reporte lo hace el organizador, no los capitanes.** El admin del lobby
  ve la tabla final de la caída y la carga; los capitanes solo reclaman si está mal. En
  enfrentamiento directo es al revés: reporta un capitán y confirma el otro. El flujo de reporte
  depende del modelo de competencia — no asumas uno solo.
- **Zona horaria**: la sede define la zona del torneo (Bolivia = UTC-4, sin horario de verano),
  pero los equipos pueden ser de otros países. Guardar siempre en UTC con `timezone=True` y
  mostrar en la zona del torneo; nunca guardar hora local sin zona.
- **Multi-edición desde el diseño**: "1ra edición" no es un nombre, es un dato. Un mismo torneo
  tiene ediciones, y un equipo puede participar en varias con distinto roster.
- **Conectividad**: los reportes llegan tarde, duplicados o con la captura mal. Diseñar para
  reintentos e idempotencia, no para el camino feliz.
- **Sin cobro de inscripción de inicio**, pero el modelo debe soportar inscripción paga después
  (estado de pago por equipo) sin rehacer las tablas.

Si una decisión de diseño ignora este contexto, adviértelo antes de continuar.

---

## Antes de diseñar cualquier módulo, responde:

1. ¿Cómo resuelve esto un organizador real hoy (Toornament, Battlefy, o Excel)?
2. **¿Aplica igual a enfrentamiento directo y a multi-equipo?** Si no, ¿dónde vive cada variante?
3. ¿Qué entidades de negocio participan (nuevas y existentes)?
4. ¿Qué reglas de negocio aplican, y qué pasa cuando se rompen?
5. ¿Qué pasa si el torneo crece de 45 a 450 equipos? ¿Y si hay 20 torneos activos a la vez?
6. ¿Queda rastro auditable (quién reportó, quién confirmó, quién corrigió y por qué)?
7. ¿Qué caso de reversión existe (resultado mal cargado, walkover revertido, equipo readmitido)?

---

---

**Continúa en `02b-operacion-torneo.md`**: torneo/edición/fases, rosters,
partidas y resultados, tabla y desempates, disputas, calendario, auditoría —
el detalle operativo día a día que usa todo lo definido acá arriba.
