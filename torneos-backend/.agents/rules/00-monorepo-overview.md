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
