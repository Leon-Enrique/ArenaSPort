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
