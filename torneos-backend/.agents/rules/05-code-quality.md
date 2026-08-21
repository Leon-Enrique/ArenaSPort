# Calidad de código

Este archivo cubre **cómo se escribe el código**, no qué arquitectura usar (eso vive en
`01-backend-architect.mdc`) ni qué reglas de negocio implementar (eso vive en
`02-esports-business.mdc`). Si una instrucción aquí choca con una decisión de arquitectura,
gana la arquitectura.

---

## Naming

- **Capa de negocio y API (routers, servicios, casos de uso, nombres de rutas)**: en
  **español**, reflejando el lenguaje del organizador y de los capitanes
  (`listar_partidas`, `confirmar_resultado`, `verificar_elegibilidad_jugador`,
  `calcular_tabla_posiciones`, `cargar_tabla_de_caida`). No la rompas por seguir una
  convención genérica de otro proyecto.
- **Infraestructura pura** (clases base de framework, engine, sesión, settings): en inglés,
  porque es la convención del framework (`Base`, `engine`, `get_db`, `Settings`).
- No mezcles ambos idiomas dentro de la misma capa sin razón.
- Nombres que reflejan el lenguaje del negocio, no detalles técnicos:
  `avanzar_ganador_en_llave()`, no `update_bracket_node()`.
- **Nombres agnósticos del juego en el núcleo.** Un servicio del núcleo no se llama
  `calcular_puntos_free_fire()` — se llama `calcular_puntos()` y recibe el sistema de puntaje.
  Si un nombre menciona un juego, ese código no pertenece al núcleo.
- Sin abreviaturas ambiguas: `equipo`, no `eq`; `suplente`, no `sup` (salvo estándar aceptado
  del dominio: `bo3`, `mvp`, `uid`, `br`).
- Booleanos con prefijo que deje clara la pregunta: `es_suplente`, `tiene_disputa_abierta`,
  `esta_confirmada`. Sé consistente dentro del mismo archivo.
- Funciones con verbo en infinitivo o imperativo (`calcular_desempate`, `reportar_resultado`);
  nunca solo un sustantivo para una función que hace algo.

### Vocabulario del dominio fijo — usar siempre el mismo término

- `partida` — el enfrentamiento o la caída. Nunca "match" ni "juego".
- `caída` — una partida de battle royale dentro de una ronda (término LATAM, se usa en el
  lenguaje del organizador). En código: `numero_caida`.
- `mapa` — cada juego individual dentro de un BO3/BO5 de enfrentamiento directo.
- `participación` — la fila que vincula un equipo a una partida con su resultado.
- `edición` — no "temporada". `fase` — no "etapa". `llave` — no "bracket" en código de negocio.
- `walkover` — término estándar, se deja en inglés.
- `enfrentamiento_directo` / `multi_equipo` — los dos modelos de competencia. Nunca "1v1"
  ni "battle royale" como nombre técnico: BR es un género de juego, `multi_equipo` es el
  modelo de competencia, y no siempre coinciden.

## Manejo de errores

- Nunca capturar `except Exception:` genérico sin re-lanzar o loguear con contexto suficiente
  (qué operación, qué partida, qué equipos — nunca tokens ni credenciales).
- Excepciones de dominio explícitas y tipadas, no `ValueError` genérico:
  `JugadorYaInscritoError`, `RosterBloqueadoError`, `TransicionDeEstadoInvalidaError`,
  `FaseNoCerradaError`, `ResultadoYaConfirmadoError`, `EvidenciaRequeridaError`,
  `ModeloDeCompetenciaIncompatibleError`, `CantidadDeParticipantesInvalidaError`.
  El llamador (router o bot) necesita distinguir el tipo para decidir cómo responder.
- Un error de negocio ("el roster está bloqueado") no es lo mismo que un error técnico
  ("no se pudo conectar a la base de datos") — no los mezcles en la misma jerarquía ni los
  traduzcas al mismo código HTTP.
- Nunca silenciar un error para que el flujo "no se rompa". Un reporte de resultado que falla
  en silencio es un equipo que reclama tres días después sin evidencia de qué pasó.

## Logging

- Log estructurado (no strings concatenados) para poder filtrar por campo en producción.
  Incluir siempre `edicion_id` y `partida_id` cuando apliquen — durante una noche de torneo
  vas a necesitar filtrar por partida, no leer un chorro de texto.
- Nivel correcto: `debug` para detalle de desarrollo, `info` para eventos de negocio
  (resultado confirmado, caída cargada, fase cerrada, sorteo ejecutado), `warning` para algo
  inesperado no fatal (reporte duplicado ignorado), `error` para fallas que requieren atención.
- Nunca loguear información sensible completa (tokens de bot, credenciales).

## Docstrings y comentarios

- Docstring obligatorio en toda función pública de un servicio o caso de uso: qué hace, qué
  reglas de negocio aplica (referencia corta, el detalle vive en `02-esports-business.mdc`),
  qué excepciones puede lanzar.
- Comentarios solo para el "por qué" de una decisión no obvia. La tabla de mapeo de perdedores
  en doble eliminación **sí** merece un comentario explicando de dónde sale.
- Si una función necesita un comentario para explicar qué hace paso a paso, probablemente
  debería dividirse.

## Tests (no negociable en este dominio)

Cuatro áreas donde un bug es visible públicamente y cuesta credibilidad ante 45 capitanes:

- **Cálculo de tabla y desempates** — un test por criterio, incluyendo empate de tres o más
  equipos, y cubriendo los dos modelos de competencia.
- **Avance de llave** — eliminación simple con byes, y doble eliminación verificando a qué
  posición de la llave baja cae cada perdedor.
- **Cálculo de puntos de multi-equipo** — tabla de posición + bajas, incluyendo el caso de
  escuadra que no se presenta y el de multiplicador en la caída final si está configurado.
- **Transiciones de estado de partida** — que las transiciones inválidas fallen, no solo que
  las válidas funcionen.

**Además**: todo servicio del núcleo debe tener al menos un test parametrizado que corra el
mismo caso con configuración de MLBB y con configuración de Free Fire. Es la única forma de
detectar que algo se acopló a un juego antes de que lo descubras en producción.

## Criterios de un PR aceptable

- **Sin `if juego == "..."` fuera de la capa de configuración de juego.**
- Sin lógica de negocio duplicada respecto a un módulo existente.
- Sin lógica de negocio replicada en `torneos-bot/` que ya exista en el backend.
- Sin código muerto ni comentado dejado "por si acaso".
- Funciones cortas y con una sola responsabilidad clara.
- Todo cambio en una operación sensible (resultado, roster, sanción, cierre de fase, config de
  puntaje) debe venir acompañado de su registro auditable correspondiente.
- Sin `print()` en código de producción — usar el logger configurado.

## Qué NO hacer

- No repetir aquí decisiones de arquitectura (capas, patrones) — esas van en 01.
- No repetir aquí reglas de negocio de esports — esas van en 02.
- No aprobar código que "funciona" pero esconde el error en vez de manejarlo.
- No dar por terminada una función de desempate, puntaje o avance de llave sin sus tests.
- No nombrar nada del núcleo con el nombre de un juego.
