# Operación de torneos — parte 2 de 2

Continuación de `02a-modelos-competencia.md` (los dos modelos de competencia,
el catálogo de juegos, el sistema de puntaje, y el contexto LATAM viven ahí —
léelo primero). Esta parte es el detalle operativo día a día.

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
