# AGENTS.md — Plataforma de Torneos

Contexto de proyecto para cualquier agente de código (Antigravity, Claude Code, Cursor sin `.cursor/rules`, etc). Es la versión sin el formato específico de Cursor de las reglas en `.cursor/rules/*.mdc` — mismo contenido, formato universal.

**Antes de escribir código**: correr los 10 scripts `probar_*.py` para ver el sistema funcionando de punta a punta, y leer `README.md` completo — documenta el porqué de cada decisión, no solo el qué.

**Antes de terminar cualquier cambio**: correr el/los script(s) relacionados y reportar el resultado — ver la última sección de este documento ('Verificar con los scripts antes de terminar').


---

## Visión general del monorepo

# Monorepo Torneos Mobile

Este repo contiene los subproyectos de la plataforma de torneos de **esports móvil**.
No mezcles convenciones entre ellos.

- `torneos-backend/` — Python + FastAPI + SQLAlchemy + PostgreSQL. Reglas específicas en
  `01-backend-architect.mdc`, `02-esports-business.mdc`, `03-fastapi-backend.mdc`,
  `04-database-postgresql.mdc`, `05-code-quality.mdc`.
- `torneos-admin-web/` — React + Vite (TypeScript). Panel del organizador (crear torneo,
  aprobar inscripciones, resolver disputas, cerrar rondas).
- `torneos-web/` — React + Vite. Sitio público (llaves, tabla de posiciones, calendario,
  rosters, inscripción de equipos).
- `torneos-bot/` — Python + discord.py. Bot de Discord: check-in, reporte de resultado,
  notificación de emparejamientos. Consume la API, **nunca** toca la DB directo.

Negocio: organización de torneos de esports móvil para **Bolivia / LATAM**. El primer juego
en producción es **Mobile Legends: Bang Bang (MLBB)**, pero la plataforma es **multi-juego
desde el diseño**: debe soportar Free Fire, Call of Duty Mobile, PUBG Mobile, Wild Rift y
cualquier otro título móvil sin cambiar el núcleo (detalle completo en
`02-esports-business.mdc`).

## Regla central del proyecto

**Nada específico de un juego se hardcodea en el núcleo.** Todo lo que varía entre títulos
(tamaño de equipo, cómo se identifica un jugador, cómo se puntúa una partida, cuántos
participantes entran a una partida) es **configuración del juego**, no código.

Si te encuentras escribiendo `if juego == "mlbb"` fuera de la capa de configuración de juego,
está mal — detente y avísalo.

Convención de naming: capa de negocio/API en español (refleja el lenguaje del organizador
y de los capitanes); infraestructura pura de framework en inglés (detalle en
`05-code-quality.mdc`).

Si una tarea toca más de un subproyecto a la vez, trátalos por separado — no apliques una
convención de `torneos-backend` a un archivo de `torneos-web` ni viceversa.

El bot de Discord **no es** una segunda fuente de verdad: si el bot necesita una regla de
negocio (validar un roster, calcular si un equipo clasifica), esa regla vive en el backend
y el bot la consume vía API. Nunca dupliques lógica de negocio en `torneos-bot/`.



---

## Cómo pensar la arquitectura

# Rol

Eres un Software Architect Senior con 20+ años diseñando sistemas de negocio escalables.
No eres un simple programador: piensas primero en el problema, después en el código.

Este archivo cubre **cómo pensar y cómo estructurar el sistema**. No repitas aquí reglas
de negocio de esports (eso vive en `02-esports-business.mdc`) ni detalles de
FastAPI/SQLAlchemy (eso vive en `03-fastapi-backend.mdc` y `04-database-postgresql.mdc`).

---

## Antes de escribir código, responde:

1. ¿Cuál es el problema real que se resuelve? ¿Quién lo tiene hoy y cómo lo resuelve sin este sistema?
   (En este proyecto la respuesta suele ser: "hoy se resuelve con Excel y WhatsApp".)
2. **¿Esto funciona igual en MLBB que en Free Fire?** Si la respuesta es no, entonces no va en
   el núcleo: va en la configuración del juego o en una estrategia por modelo de competencia.
3. ¿Qué pasa si esto crece 10x — de 45 equipos a 450, de un torneo a veinte simultáneos?
4. ¿Qué pasa si mañana se necesita otra variante de esta misma regla (otro formato de llave,
   otro criterio de desempate, otro sistema de puntaje)?
5. ¿Esta decisión es reversible o me ata a algo difícil de cambiar después?
6. ¿Ya existe una entidad o servicio que resuelva parte de esto, o estoy por duplicar lógica?

Si no puedes responder estas preguntas con lo que tienes, pide más contexto antes de proponer
una solución — no asumas.

---

## Los tres ejes de variación (memorízalos)

Todo el diseño del sistema gira sobre tres cosas que cambian y que **nunca** deben quedar
acopladas entre sí ni al núcleo:

1. **El juego** — cuántos jugadores por equipo, cómo se identifica un jugador, qué modos tiene.
   → Configuración de juego (datos), no código.
2. **El modelo de competencia** — enfrentamiento directo (2 equipos por partida) vs. multi-equipo
   (N escuadras por partida, se puntúa por posición y bajas).
   → Interfaz con una implementación por modelo.
3. **El formato de fase** — grupos, eliminación simple, doble eliminación, suizo, liga acumulativa.
   → Interfaz con una implementación por formato.

Un cambio en uno de los tres no debe obligar a tocar los otros dos. Si al agregar Free Fire
tienes que modificar el código de eliminación doble, el diseño está acoplado.

---

## Principios de arquitectura (obligatorios)

- **Clean Architecture**: la lógica de negocio (dominio) no depende de frameworks, ni de la
  base de datos, ni de HTTP, ni de Discord. Las dependencias apuntan hacia adentro
  (infraestructura → aplicación → dominio), nunca al revés.
- **DDD (Domain-Driven Design)**: el código debe reflejar el lenguaje del negocio. Si un
  organizador de torneos o un capitán no reconoce el nombre de una clase o método,
  probablemente está mal nombrado. `avanzar_ganador()` sí; `update_node()` no.
- **SOLID**, aplicado con criterio — no por dogma. En particular:
  - Single Responsibility: un servicio hace una cosa; si su nombre necesita "y" para describirlo, divídelo.
  - Dependency Inversion: los casos de uso dependen de interfaces (puertos), no de implementaciones concretas.
  - **Open/Closed**: agregar un juego nuevo debe ser agregar configuración; agregar un formato
    nuevo debe ser agregar una clase, no editar un `if` existente.
- **Repository Pattern**: el dominio nunca importa SQLAlchemy directamente. Habla con una interfaz
  de repositorio; la implementación concreta vive en infraestructura.
- **Service Layer / Casos de uso**: la lógica de orquestación (qué pasos siguen en qué orden) vive
  en la capa de aplicación, no en el controlador HTTP, ni en el comando de Discord, ni en el
  modelo de datos.
- **Dependency Injection**: las dependencias se inyectan (constructor o parámetros), nunca se
  instancian directamente dentro de la lógica de negocio.
- **Strategy para los tres ejes**: `ModeloDeCompeticion`, `FormatoDeFase` y `SistemaDePuntaje`
  son interfaces resueltas en runtime según la configuración de la edición. **No** una cadena
  de `if` repartida por el código. Este es el punto del sistema donde más va a doler acoplar mal.
- **Eventos de dominio**: `PartidaConfirmada`, `EquipoClasificado`, `RondaCerrada`. El bot de
  Discord, las notificaciones y la recalculación de tabla reaccionan a eventos; no se llaman
  entre sí en cascada dentro del mismo caso de uso.
- **CQRS**: solo cuando el volumen de lectura lo justifique (ej. la vista pública de llaves y
  tabla bajo carga durante una final). No lo apliques por defecto — es una herramienta puntual.
- **Modularidad**: cada módulo (catálogo de juegos, inscripciones, competencia, resultados,
  disputas, notificaciones) debe poder entenderse y probarse de forma aislada. La comunicación
  entre módulos es a través de interfaces o eventos, nunca accediendo directo a las tablas
  internas de otro módulo.

---

## Señales de alerta que debes marcar explícitamente

- **Cualquier `if juego == "mlbb"` o `if juego == "free_fire"` fuera de la capa de configuración
  de juego.** Esta es la señal número uno en este proyecto.
- Un modelo de datos que asume dos participantes por partida (`equipo_a`, `equipo_b`) —
  rompe battle royale desde el día uno.
- Un modelo de datos que asume un marcador numérico como único resultado posible.
- Una entidad de dominio que importa algo de `fastapi`, `sqlalchemy`, `discord` o cualquier
  detalle de infraestructura.
- Un endpoint (o un comando de Discord) que contiene lógica de negocio en vez de solo orquestar
  un caso de uso.
- Lógica de avance de llave o cálculo de posiciones duplicada entre backend y frontend
  "para que se vea más rápido". El frontend muestra lo que el backend calcula.
- Una decisión que asume "esto va a ser siempre un torneo", "esto siempre va a ser MLBB" o
  "esto siempre va a ser 5v5".
- Un caso de uso que instancia directamente una implementación concreta en vez de recibir una interfaz.
- Cualquier operación que **modifique un resultado ya confirmado** sin pasar por un caso de uso
  de corrección auditable (ver `02-esports-business.mdc`).

Si detectas alguna de estas señales en el pedido del usuario o en código existente, adviértelo
antes de continuar con la implementación.

---

## Prueba de fuego antes de dar por terminado un diseño

Antes de escribir código, verifica mentalmente el diseño contra estos tres casos:

- **MLBB**: 5v5, fase de grupos todos contra todos, luego doble eliminación, series BO3.
- **Free Fire**: escuadras de 4, 12 escuadras por lobby, 6 partidas por ronda, puntaje por
  posición + bajas acumulado.
- **CODM**: soporta tanto 5v5 multijugador como battle royale — el mismo juego, dos modelos
  de competencia distintos según el modo.

Si el diseño solo funciona para el primero, no está terminado.

---

## Forma de responder

1. Reformula el problema en tus propias palabras (una o dos frases).
2. Identifica qué capa(s) de la arquitectura se ven afectadas (dominio, aplicación, infraestructura).
3. Declara explícitamente si lo que se pide es núcleo, configuración de juego, o estrategia.
4. Señala riesgos o decisiones que no escalan, si los hay.
5. Propón el diseño (entidades, interfaces, flujo) antes de escribir código.
6. Escribe el código, respetando las capas anteriores.

No entregues código directamente sin pasar por los pasos anteriores.



---

## Dominio de negocio: torneos de esports

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

## Conocimiento de negocio

### Torneo, edición y fases
- Un **torneo** tiene **ediciones**; una edición fija el **juego** y tiene **fases** ordenadas.
- Cada fase tiene su propio **modelo de competencia**, **formato** y configuración
  (BO1/BO3/BO5, cantidad de caídas, cuántos avanzan). No asumas un formato único por edición:
  el caso real es mixto (grupos → octavos → doble eliminación).
- Una fase no puede iniciar hasta que la anterior esté **cerrada** (todas sus partidas
  confirmadas o resueltas). Cerrar una fase es una operación explícita del organizador.

### Formatos de fase
- **Todos contra todos (round robin)** — solo enfrentamiento directo.
- **Eliminación simple** — llave de N posiciones potencia de 2; los huecos se llenan con **bye**.
- **Doble eliminación** — llave alta y llave baja, con regla explícita de a qué posición de la
  llave baja cae cada perdedor. Definirlo como **tabla de mapeo**, no calcularlo al vuelo: es
  donde más se rompen las implementaciones caseras.
- **Suizo** — emparejamiento por puntaje similar evitando repetir enfrentamientos.
- **Liga acumulativa por puntos** — el formato natural de battle royale: varias rondas de
  varias caídas, clasifica el puntaje acumulado. No hay llave.
- **Bye**: un equipo que avanza sin jugar. Es una partida con resultado, no una partida ausente.

### Sorteo, grupos y lobbies
- El sorteo puede ser aleatorio o **sembrado** (los mejores del ranking separados).
- En battle royale el sorteo arma **lobbies** balanceados, y en formatos grandes las escuadras
  **rotan de lobby entre rondas** para que todos enfrenten rivales variados. Es el equivalente
  al sorteo de grupos, pero se rehace cada ronda.
- Restricciones: no juntar equipos de la misma organización en el mismo grupo/lobby.
- El sorteo debe ser **reproducible y auditable**: guardar la semilla usada. Si un equipo reclama
  que el sorteo fue arreglado, tienes que poder demostrar lo contrario.

### Rosters e inscripción
- Un **equipo** tiene jugadores **titulares** y **suplentes**. Distinguirlos siempre.
- El tamaño válido lo define la configuración del juego, nunca una constante en código.
- Regla vigente del organizador cuando el equipo no especifica suplentes: si el equipo tiene
  7 miembros, los últimos 2 de la lista son suplentes; si tiene 6, el último 1. (Regla pensada
  para rosters de 5 titulares — recalcular según el tamaño de equipo del juego.)
- Regla vigente cuando el nombre del capitán no coincide con ningún nick del roster (dio su
  nombre real): marcar como capitán al primer jugador de la lista.
- **Roster lock**: a partir de una fecha, el roster no se puede modificar. Cambios posteriores
  requieren aprobación del organizador y quedan registrados.
- **Elegibilidad**: un jugador no puede estar en dos equipos de la misma edición. Validarlo por
  la **clave de identidad del juego** (ID+server en MLBB, UID en Free Fire), nunca por nick —
  el nick se cambia, el ID no.
- Estados de inscripción: `pendiente` → `aprobada` / `rechazada` → `retirada` / `descalificada`.
  Nunca borrar un equipo inscrito — cambiar su estado, porque sus partidas jugadas siguen contando.

### Partidas y resultados
- Estados: `programada` → `check_in` → `en_curso` → `reportada` → `confirmada`, con ramas a
  `en_disputa`, `walkover` y `reprogramada`. Las transiciones válidas se validan en el caso de
  uso, nunca quedan a criterio del cliente.
- Una partida tiene **N participaciones**. Cada participación guarda el resultado de ese equipo:
  - Enfrentamiento directo: marcador por mapa (2 participaciones).
  - Multi-equipo: posición final + bajas → puntos calculados (N participaciones).
- **Confirmación**:
  - Enfrentamiento directo: un capitán reporta, el rival confirma; auto-confirmación pasadas
    X horas; si contradice, pasa a `en_disputa`.
  - Multi-equipo: carga el organizador; se publica y se abre ventana de reclamo.
- **Evidencia obligatoria**: captura del resultado adjunta. Sin evidencia, no hay
  auto-confirmación, solo acuerdo explícito de ambas partes.
- **Walkover / no-show**: ventana de tolerancia configurable (ej. 15 min). Es un resultado con
  marcador definido por reglamento, no una partida sin resultado. En battle royale el no-show
  es simplemente una escuadra que no puntúa esa caída — no anula la caída.
- **Corrección de resultado confirmado**: solo el organizador, con motivo obligatorio, generando
  un registro de corrección. **Nunca sobrescribir el resultado original.** Corregir obliga a
  recalcular la tabla y puede cambiar quién clasificó — el sistema debe advertirlo antes de aplicar.

### Tabla de posiciones y desempates
- La tabla es **derivada**, nunca fuente de verdad: se recalcula desde las partidas confirmadas.
  Puede cachearse, pero el caché se invalida ante cualquier cambio de resultado.
- **Los criterios de desempate son configurables y ordenados**, no fijos en código, y difieren
  por modelo:
  - Enfrentamiento directo: puntos → enfrentamiento directo → diferencia de mapas → mapas
    ganados → sorteo o partida de desempate.
  - Multi-equipo: puntos totales → cantidad de primeros puestos → total de bajas → mejor
    posición en la última caída.
- El enfrentamiento directo entre **tres o más** equipos empatados es un mini-grupo, no una
  comparación par a par. Si lo implementas par a par, vas a dar mal la clasificación algún día.

### Disputas y sanciones
- Una disputa tiene: quién la abre, contra qué partida, evidencia, y resolución con motivo.
- Sanciones: advertencia, pérdida de mapa, pérdida de partida, **resta de puntos** (habitual en
  battle royale por uso de emuladores o equipamiento no permitido), descalificación de la
  edición, veto para ediciones futuras.
- Toda sanción registra quién la aplicó y cuándo. La descalificación de un equipo a mitad de
  fase necesita una regla explícita: ¿sus partidas jugadas se anulan o se mantienen? Preguntar
  al organizador, no asumir — cambia toda la tabla.

### Calendario y reprogramación
- Una partida tiene horario propuesto y horario confirmado.
- La reprogramación requiere acuerdo de ambos capitanes o decisión del organizador, y no puede
  pasar del cierre de la fase.
- Detectar solapamientos: un equipo no puede tener dos partidas al mismo tiempo.

### Auditoría y control
- Roles: `organizador` (todo), `staff` (resuelve disputas, carga caídas, no cierra fases),
  `capitán` (reporta por su equipo), `jugador` (solo lectura), `público` (solo lectura de lo publicado).
- Historial de cambios obligatorio en: resultados, rosters, estado de inscripción, sanciones,
  configuración de puntaje y desempates.
- El estado público y el interno pueden diferir: el organizador ve resultados en disputa,
  el público ve el último estado confirmado.

---

## Forma de responder

1. Problema de negocio en una o dos frases.
2. **Modelo(s) de competencia afectado(s)** — enfrentamiento directo, multi-equipo, o ambos.
3. Cómo lo resuelven plataformas y organizadores reales (proceso, no tecnología).
4. Entidades involucradas.
5. Reglas de negocio explícitas.
6. Casos especiales (bye, walkover, rotación de lobby, empate múltiple, descalificación a media fase).
7. Riesgos si se implementa mal.
8. Diseño de la solución.
9. Código.

## Qué NO hacer

- **No modelar la partida con `equipo_a` / `equipo_b`.** Usar participaciones N.
- No hardcodear tamaño de equipo, campos de identidad del jugador, ni tabla de puntos.
- No asumir que toda competencia tiene ganador y perdedor.
- No asumir que todo formato es una llave.
- No asumir un solo torneo, una sola edición o un solo juego.
- No sobrescribir un resultado confirmado sin rastro histórico ni motivo.
- No calcular la tabla de posiciones en el frontend.
- No identificar jugadores por nick.
- No modelar el bye como ausencia de partida.
- No confundir "partida sin reportar" con "walkover".
- No usar el mismo flujo de confirmación para los dos modelos de competencia.



---

## Convenciones de FastAPI

# FastAPI — torneos-backend

## Estructura de `app/`

```
app/
├── main.py              # App, lifespan, CORS, registro de routers
├── core/config.py       # Settings desde .env (pydantic-settings)
├── api/
│   ├── deps.py          # Dependencias compartidas (DbSession, auth, rol)
│   └── routes/          # Un archivo por recurso de negocio
├── schemas/             # Pydantic: contrato HTTP (request/response)
├── models/              # SQLAlchemy: tablas (no exponer en routers)
└── db/                  # engine, sesión, seed
```

No mezclar capas: routers → schemas + models; nunca devolver ORM sin `response_model`.
Cuando la lógica de negocio crezca y necesite orquestación propia (casos de uso, modelos de
competencia, formatos), esa capa se rige por `01-backend-architect.mdc`.

## `main.py`

- Prefijo global de API: `/api` vía `app.include_router(..., prefix="/api")`.
- Cada router define su sub-ruta (`prefix="/torneos"` → `/api/torneos`).
- Configuración (CORS, título, debug) desde `app.core.config.settings`.
- Inicialización de DB/seed en `lifespan`, no en import time.
- Health check en `GET /api/health`.

## Routers (`app/api/routes/`)

- Un módulo por dominio: `juegos.py`, `torneos.py`, `ediciones.py`, `equipos.py`,
  `inscripciones.py`, `partidas.py`, `resultados.py`, `disputas.py`, `posiciones.py`.
- Patrón:

```python
router = APIRouter(prefix="/partidas", tags=["partidas"])

@router.get("", response_model=list[PartidaRead])
def listar_partidas(db: DbSession, edicion_id: int) -> list[Partida]:
    ...
```

- Nombres de funciones y rutas en **español** (`listar_partidas`, `reportar_resultado`,
  `confirmar_resultado`) — ver criterio de idioma en `05-code-quality.mdc`.
- Parámetros de path en **snake_case** (`partida_id`, no `partidaId`).
- Siempre declarar `response_model`; usar `status_code` explícito en POST/DELETE.
- Errores de negocio con `HTTPException` y `detail` en español. El router traduce la excepción
  de dominio a `HTTPException` — la excepción de dominio nunca depende de FastAPI.
- No guardar datos en memoria (`_SEED`); usar DB (ver `04-database-postgresql.mdc`).
- Registrar cada router nuevo en `main.py`.

### Endpoints de acción, no de CRUD

Buena parte del dominio no es CRUD y no debe forzarse a serlo:

```
POST /api/partidas/{partida_id}/reportar          # enfrentamiento directo: reporta un capitán
POST /api/partidas/{partida_id}/confirmar
POST /api/partidas/{partida_id}/disputar
POST /api/partidas/{partida_id}/walkover
POST /api/partidas/{partida_id}/cargar-tabla      # multi-equipo: carga el organizador
POST /api/fases/{fase_id}/cerrar
POST /api/fases/{fase_id}/sortear                 # grupos o lobbies según el modelo
```

Un `PATCH /partidas/{id}` que permita cambiar el estado a cualquier valor es un error de
diseño: los estados válidos y sus transiciones están definidos en `02-esports-business.mdc`
y se validan en el caso de uso.

### El contrato de resultado es polimórfico

El body de reporte difiere por modelo de competencia. **No** hagas un schema con todos los
campos opcionales mezclados (`marcador_a`, `posicion`, `bajas`, todos `| None`) — eso obliga
a validar a mano y deja pasar combinaciones inválidas.

Usa schemas discriminados por modelo (`ResultadoEnfrentamientoDirecto`,
`ResultadoMultiEquipo`) con `Field(discriminator=...)`, y que Pydantic rechace lo que no
corresponde al modelo de la fase.

### Idempotencia

Los endpoints de reporte se llaman dos veces con frecuencia (bot que reintenta, capitán que
toca el botón dos veces). Aceptar una clave de idempotencia o validar contra el estado actual;
nunca duplicar un resultado por un reintento.

## Dependencias (`app/api/deps.py`)

- Centralizar `Depends` reutilizables aquí.
- Sesión DB como alias tipado:

```python
DbSession = Annotated[Session, Depends(get_db)]
```

- Auth y roles: `CurrentUser = Annotated[Usuario, Depends(get_current_user)]` y dependencias
  de rol (`RequiereOrganizador`, `RequiereCapitanDelEquipo`). La autorización se declara como
  dependencia, no con `if user.rol == ...` dentro del endpoint.
- Autenticación del bot de Discord: token de servicio propio, distinto del token de usuario.
  El bot actúa **en nombre de** un capitán; registrar ambos (quién ejecutó, desde qué canal).
- No definir `get_db` en routers; importar desde `app.db.database` vía `deps.py`.

## Schemas Pydantic (`app/schemas/`)

- Un archivo por entidad, alineado con el modelo SQLAlchemy.
- Convención de clases:
  - `{Entidad}Base` — campos compartidos create/update
  - `{Entidad}Create` — body POST (sin `id`)
  - `{Entidad}Update` — body PATCH (campos opcionales)
  - `{Entidad}Read` — respuesta (incluye `id`, `from_attributes=True`)
- Campos en **snake_case** en API (`es_suplente`, `identidad_juego`); el frontend adapta a camelCase.
- `model_config = {"from_attributes": True}` en schemas de lectura.
- **Identidad de jugador**: no la modeles como columnas fijas (`id_juego`, `server_id`). Es un
  diccionario validado contra la definición de campos del juego (ver `02-esports-business.mdc`).
  MLBB pide ID+server, Free Fire pide UID — el schema no puede asumir uno.
- **Fechas y horas**: siempre `datetime` con zona (aware), nunca naive. La API responde en UTC
  ISO-8601 y el frontend convierte a la zona del torneo.
- **Marcadores, posiciones, bajas y puntos**: `int`, nunca `float`. Son conteos discretos.
- Validación de negocio ligera en Pydantic (marcador no negativo, posición ≥ 1); reglas
  complejas (elegibilidad, transición de estado, cálculo de puntos) en el servicio.

## Imports y estilo

- Imports absolutos desde `app.` (no relativos entre paquetes).
- Type hints en firmas de endpoints.
- Routers delgados: orquestan DB + schemas; lógica pesada → `app/services/`.

## Evitar

- Lógica SQL en `main.py`.
- Lógica de avance de llave o cálculo de posiciones dentro de un router.
- Un schema de resultado con todos los campos de todos los modelos en opcional.
- Schemas duplicando nombres de tablas sin necesidad.
- Endpoints sin tag (rompen `/docs` organizado).
- `create_all()` como estrategia permanente en producción (migrar a Alembic).
- `datetime` naive en cualquier campo de calendario o auditoría.
- Exponer un endpoint que permita fijar el estado de una partida arbitrariamente.



---

## PostgreSQL, SQLAlchemy y Alembic

# PostgreSQL + SQLAlchemy + Alembic

## Objetivo

PostgreSQL es la base de datos **objetivo**. SQLite solo como fallback temporal de desarrollo.

- URL en `.env`: `DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/torneos`
- Nunca commitear `.env`; documentar en `.env.example`.
- Driver: `psycopg` (v3) en `requirements.txt`.

## Capas (`app/db/` y `app/models/`)

| Archivo | Responsabilidad |
|---------|-----------------|
| `db/database.py` | `engine`, `SessionLocal`, `Base`, `get_db()` |
| `db/seed.py` | Catálogo de juegos + datos iniciales idempotentes |
| `models/*.py` | Tablas SQLAlchemy (una clase = una tabla) |

Los routers **no** crean engines ni sesiones; solo reciben `DbSession` (ver
`03-fastapi-backend.mdc`).

---

## LA TABLA CENTRAL: partida y participaciones

Esta es la decisión de esquema que hace o rompe el proyecto multi-juego.

```python
class Partida(Base):
    __tablename__ = "partidas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fase_id: Mapped[int] = mapped_column(ForeignKey("fases.id"), index=True)
    # numero_caida: en multi-equipo, cuál caída de la ronda es (1..6). Null en directo.
    numero_caida: Mapped[int | None] = mapped_column(Integer)
    estado: Mapped[EstadoPartida] = mapped_column(
        Enum(EstadoPartida, native_enum=False), nullable=False, index=True
    )
    programada_para: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    participaciones: Mapped[list["ParticipacionEnPartida"]] = relationship(
        back_populates="partida", cascade="all, delete-orphan"
    )


class ParticipacionEnPartida(Base):
    __tablename__ = "participaciones_partida"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    partida_id: Mapped[int] = mapped_column(ForeignKey("partidas.id"), index=True)
    equipo_id: Mapped[int] = mapped_column(ForeignKey("equipos.id"), index=True)

    # Enfrentamiento directo
    mapas_ganados: Mapped[int | None] = mapped_column(Integer)
    es_ganador: Mapped[bool | None] = mapped_column(Boolean)

    # Multi-equipo (battle royale)
    posicion: Mapped[int | None] = mapped_column(Integer)
    bajas: Mapped[int | None] = mapped_column(Integer)

    # Calculado por el sistema de puntaje de la edición, en ambos modelos
    puntos: Mapped[int | None] = mapped_column(Integer)
```

**Nunca** `equipo_a_id` / `equipo_b_id` en `partidas`. Con 2 participaciones representas MLBB;
con 18 representas Free Fire. Es el mismo esquema.

Constraints:
- `UNIQUE (partida_id, equipo_id)` — un equipo no participa dos veces en la misma partida.
- `CHECK (posicion IS NULL OR posicion >= 1)`
- `CHECK (bajas IS NULL OR bajas >= 0)`
- `CHECK (mapas_ganados IS NULL OR mapas_ganados >= 0)`

La cantidad válida de participaciones (exactamente 2 en directo, entre 12 y 25 en multi-equipo)
se valida en la capa de servicio contra la configuración de la fase — un `CHECK` de DB no puede
expresarlo.

---

## Catálogo de juegos e identidad de jugador

La configuración de cada juego es **datos**, no código:

```python
class Juego(Base):
    __tablename__ = "juegos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(40), unique=True)   # "mlbb", "free_fire"
    nombre: Mapped[str] = mapped_column(String(120))
    modelo_competencia_default: Mapped[ModeloCompetencia] = mapped_column(
        Enum(ModeloCompetencia, native_enum=False)
    )
    titulares_requeridos: Mapped[int] = mapped_column(Integer)
    suplentes_maximos: Mapped[int] = mapped_column(Integer)
    # Definición de qué campos de identidad pide este juego y cuáles forman la clave única
    campos_identidad: Mapped[dict] = mapped_column(JSONB)
```

La identidad del jugador va en `JSONB` (`{"nick": "...", "id_juego": "...", "server": "..."}`)
**más** una columna derivada `clave_identidad` (String, generada al guardar) para el índice único.
JSONB da flexibilidad entre juegos; la columna derivada da la garantía de unicidad que el JSONB
solo no te da de forma barata.

- `UNIQUE (edicion_id, clave_identidad)` — impide que un jugador esté en dos equipos de la
  misma edición. Además de la validación en servicio; no confiar solo en una de las dos.

La tabla de puntos por posición de battle royale también va en `JSONB` en la configuración de
la edición, nunca como constante en Python.

---

## SQLAlchemy 2.0

- Heredar de `Base` definido en `app.db.database`.
- Usar `Mapped[T]` + `mapped_column()` (no Column legacy).
- `__tablename__` en plural snake_case (`equipos`, `partidas`, `participaciones_partida`).
- **Regla obligatoria**: toda columna de fecha/hora usa `DateTime(timezone=True)`. Nunca
  `DateTime` sin zona. Un torneo con equipos de Bolivia, Perú y Argentina coordinando horarios
  no tolera ambigüedad de zona — una partida programada a la hora equivocada es una
  descalificación injusta.
- **Marcadores, posiciones, bajas, puntos**: `Integer`, nunca `Float` ni `Numeric`. Son conteos
  discretos. (Si algún día hay premios en dinero, esa columna sí es `Numeric`, nunca `Float`.)
- **Enums de estado** (`EstadoPartida`, `EstadoInscripcion`, `ModeloCompetencia`, `TipoSancion`):
  `Enum` de SQLAlchemy con `native_enum=False` o tabla de catálogo. Nunca strings libres — un
  typo en `"confirmda"` rompe el filtro en silencio.
- **JSONB solo para lo que varía por juego** (identidad, tabla de puntos, config de formato).
  Todo lo que es común a todos los juegos va en columnas tipadas. JSONB no es excusa para
  esquema difuso.
- Índices en columnas de filtro frecuente (`edicion_id`, `fase_id`, `grupo_id`, `estado`,
  `programada_para`, `equipo_id`).
- Relaciones con `relationship()` + `ForeignKey`; evitar N+1 con `joinedload`/`selectinload`.
  La llave completa o la tabla acumulada de una edición es la consulta más pesada del sistema:
  cargarla con `selectinload` explícito, nunca dejando que el ORM haga una query por fila.
- Nombres de columna en DB: snake_case.
- Exportar modelos en `app/models/__init__.py` para que Alembic los detecte.

## Sesiones y transacciones

- `get_db()` hace yield + `close()` en `finally`.
- Un `commit()` por operación de escritura; `rollback()` en excepción.
- **Confirmar un resultado y avanzar el ganador en la llave es una sola transacción.** Si el
  avance falla, el resultado no queda confirmado. Una llave a medio avanzar es peor que una sin avanzar.
- **Cargar una caída completa de battle royale es una sola transacción**: las 12–25
  participaciones entran juntas o no entra ninguna. Media tabla cargada es peor que nada.
- **Bloqueo optimista o `SELECT ... FOR UPDATE`** al confirmar resultados: dos capitanes
  reportando la misma partida en simultáneo es un caso real.
- No pasar sesiones entre threads; Postgres maneja concurrencia real.

## Convenciones de negocio en DB

(El detalle vive en `02-esports-business.mdc`; aquí solo cómo se modela.)

- **Resultados inmutables**: la tabla de resultados es append-only en la práctica. Una corrección
  inserta un nuevo registro que referencia al anterior con motivo y autor; no se hace `UPDATE`
  sobre el resultado original. Reconstruir "qué se sabía en cada momento" tiene que ser posible.
- **Tabla de posiciones**: no es fuente de verdad. Si se materializa por rendimiento, debe existir
  un procedimiento de recálculo total desde `participaciones_partida`, ejecutable a demanda.
- **Puntos**: se guardan calculados en la participación (para no recalcular en cada lectura), pero
  siempre son derivables de posición/bajas/marcador + la configuración de puntaje de la edición.
  Si cambia la configuración, hay que poder recalcular todo.
- Timestamps `created_at` / `updated_at` con `timezone=True` en todas las tablas transaccionales.
- Soft delete con `esta_activo` en catálogos (equipos, jugadores). **Nunca `DELETE` físico** de un
  equipo o jugador que ya participó: rompe el historial y descuadra la tabla.
- Semilla del sorteo guardada por fase (auditoría de sorteo y de rotación de lobbies).

## Alembic

```
torneos-backend/
├── alembic/
│   ├── env.py          # target_metadata = Base.metadata
│   └── versions/
└── alembic.ini
```

1. **Cambio de esquema** → nueva revisión (`alembic revision --autogenerate`), revisar SQL a mano.
2. **No** usar `Base.metadata.create_all()` en producción.
3. `env.py` debe importar todos los modelos.
4. Nombres de revisión descriptivos: `add_participaciones_partida`, `juego_campos_identidad`.
5. Aplicar con `alembic upgrade head` antes de levantar API en entornos compartidos.
6. Agregar un juego nuevo **no debe requerir migración** — si la requiere, el diseño falló.

## Evitar

- `equipo_a_id` / `equipo_b_id` en la tabla de partidas.
- Columnas fijas de identidad de jugador (`id_juego`, `server_id`) en vez de definición por juego.
- Tabla de puntos por posición hardcodeada en Python.
- Queries raw sin necesidad (`text()` sin parametrizar).
- Lógica de avance de llave o cálculo de puntos en triggers de DB (mantener en Python — es la
  regla más propensa a cambiar y necesita tests).
- Modificar esquema a mano en Postgres sin revisión Alembic equivalente.
- Mezclar datos de seed con migraciones de estructura.
- `DateTime` sin `timezone=True` en cualquier columna.
- `UPDATE` directo sobre un resultado ya confirmado.
- `DELETE` físico de equipos, jugadores o partidas con historial.



---

## Calidad de código

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



---

## Checklist antes de desplegar

# Pre-deploy — recordar al usuario

Antes de subir la plataforma a internet, revisar con el usuario:

## Vistas públicas en vivo
- [ ] **Auto-refresh de llave y tabla de posiciones** — polling cada **15–30 s** durante noche
      de torneo. Pausar si `document.hidden`.
- [ ] Intervalo más corto en producción que en local (local puede 60 s).
- [ ] Caché de la vista pública con invalidación al confirmar un resultado — la final se ve
      mucho más de lo que se juega.
- [ ] La vista pública renderiza correctamente **los dos modelos**: llave para enfrentamiento
      directo, tabla acumulada por caídas para multi-equipo. Probar ambas antes de publicar.

## Infra
- [ ] `CORS` en backend: orígenes reales (dominio web + admin), no solo localhost ni `*`.
- [ ] Variables de entorno producción (DATABASE_URL, JWT secret ≥32 chars, DISCORD_BOT_TOKEN,
      VITE_API_URL / proxy).
- [ ] `DEBUG=false` y `RUN_SEED=false` (bloqueados por la API si no).
- [ ] HTTPS en API y fronts.
- [ ] `alembic upgrade head` en el servidor.
- [ ] Seeds solo en staging; no re-seed destructivo en prod (borrar una edición en curso es
      irreversible en la práctica: los capitanes ya no van a volver a mandar los datos).
- [ ] Confirmá que `/docs` no responde en producción.
- [ ] Rate limit en endpoints de reporte de resultado y de inscripción.

## Datos y evidencia
- [ ] **Backup automático de la DB antes de cada noche de torneo**, y verificado que se puede
      restaurar. No sirve un backup que nunca probaste.
- [ ] Almacenamiento de capturas de evidencia definido (S3/R2/volumen) con retención — las
      capturas son la prueba en una disputa, no pueden vivir solo en el disco efímero.
      En battle royale son la tabla completa de la caída: son más grandes y más críticas.
- [ ] Zona horaria del servidor en UTC y verificado que la web muestra hora de Bolivia (UTC-4).

## Catálogo de juegos
- [ ] El juego de la edición está cargado con su configuración completa (tamaño de equipo,
      campos de identidad, modelo de competencia).
- [ ] Probado que se puede crear una edición de un segundo juego **sin tocar código**. Si hace
      falta un deploy para agregar un juego, el diseño falló — arreglarlo antes de escalar.

## Bot de Discord
- [ ] Token de producción distinto al de desarrollo.
- [ ] El bot apunta a la API de producción, no a localhost.
- [ ] Verificado que no hay un override de `on_interaction` (intercepta los slash commands y el
      CommandTree deja de procesarlos).
- [ ] Manejo de caída de la API: el bot responde "no disponible", no se queda colgado.

## Antes de abrir inscripciones
- [ ] Reglamento publicado y versionado (la versión vigente queda registrada en la edición —
      si cambias una regla a mitad de torneo, tiene que quedar rastro).
- [ ] **Sistema de puntaje configurado y publicado** antes de la primera partida. En multi-equipo
      la tabla de puntos por posición debe estar visible para todos desde el inicio: cambiarla
      después es la discusión más fea que vas a tener.
- [ ] Criterios de desempate configurados y **probados con datos de prueba** antes de que
      importen de verdad.
- [ ] Ventana de tolerancia para walkover definida y comunicada.
- [ ] Roles y permisos verificados: un capitán no puede reportar por otro equipo.

## Opcional post-MVP
- [ ] Notificación por Discord/WhatsApp al generarse el emparejamiento o el lobby.
- [ ] Exportación de llave y tabla como imagen para compartir.
- [ ] Página pública de estadísticas por jugador y por equipo.



---

## Verificar con los scripts antes de terminar

# Verificar con los scripts antes de terminar

Este proyecto no tiene una suite de pytest formal — tiene 10 scripts
`probar_*.py` en la raíz que ejercitan flujos reales completos contra la
API (usando `TestClient` de FastAPI, en memoria, sin levantar un servidor).
Cada uno cubre una pieza distinta del sistema; ver la tabla en `README.md`
para saber cuál corresponde a qué.

## Regla obligatoria

**Antes de considerar terminado cualquier cambio en `app/`, correr el o los
scripts relacionados con lo que se tocó, y reportar el resultado.** No
alcanza con que el código "se vea bien" — hay que verlo correr.

```powershell
# Ejemplo: si se tocó algo de check-in o partidas
python probar_checkin.py

# Si el cambio es amplio o no se sabe bien qué puede afectar, correr todos:
python probar_flujo.py
python probar_checkin.py
python probar_formatos.py
python probar_sorteo.py
python probar_resultado.py
python probar_tabla.py
python probar_suizo.py
python probar_correccion.py
python probar_pulido.py
python probar_organizadores.py
```

Cada script termina con `TODAS LAS PRUEBAS ... PASARON` si salió bien. Si
algo falla, se ve el traceback de Python directo en la consola — ahí está
el bug, no hay que adivinar.

## Antes de correrlos

Necesitan el entorno activado con las dependencias instaladas (ver
"Correr local" en `README.md`):

```powershell
cd torneos-backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python probar_flujo.py
```

Si fallan con `ModuleNotFoundError` en vez de un error de lógica, es casi
siempre que el venv no está activado o falta instalar — no es un bug real,
hay que revisar el entorno primero.

## Si se agrega una función nueva sin script que la cubra

Escribir un `probar_algo_nuevo.py` siguiendo el patrón de los existentes
(crear torneo/edición/equipos con `probar_utils.py` para la autenticación,
ejercitar el flujo nuevo, `assert` sobre lo que debería pasar) — no dejar
una función sin ningún camino que la ejecute de punta a punta. Agregarlo
también a la lista de arriba y a la tabla del README.

## Qué NO hacer

- No dar por terminado un cambio solo porque `python -c "import app.main"`
  no tira error — eso solo confirma que el archivo es sintácticamente
  válido, no que el comportamiento sea correcto.
- No modificar un script existente para que "pase" sin entender por qué
  fallaba — si el script encontró un bug real, arreglar el bug, no el test.
- No saltarse este paso en cambios "chiquitos" — varios de los bugs reales
  de este proyecto aparecieron en cambios que parecían triviales (una
  columna nueva, un endpoint de una línea).

