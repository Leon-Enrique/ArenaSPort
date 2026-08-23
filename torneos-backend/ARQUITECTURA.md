# Arquitectura — Plataforma de Torneos de Esports Móvil

Documento de decisiones técnicas. Primer juego en producción: MLBB. Diseñado para soportar
Free Fire, CODM y otros títulos móviles sin cambios en el núcleo.

---

## 1. Stack

| Capa | Elección | Por qué |
|------|----------|---------|
| Backend | Python 3.12 + FastAPI | Stack que ya dominás y ya desplegaste |
| ORM | SQLAlchemy 2.0 + Alembic | Tipado con `Mapped[T]`, migraciones versionadas |
| Base de datos | PostgreSQL en Railway | Sin cold start, misma red que la API |
| Frontend | Next.js 15 (App Router) + TypeScript | Server-side rendering para previews de WhatsApp y SEO |
| Estilos | Tailwind CSS | Rapidez de iteración |
| Auth | Discord OAuth2 | Todos los jugadores ya tienen Discord |
| Archivos | Cloudflare R2 | Egress gratis, disco de Railway es efímero |
| Deploy API/DB | Railway | Ya lo usás, plan Hobby |
| Deploy web | Vercel | Integración nativa con Next.js |
| Tests | pytest | Exigido por las reglas del proyecto |

### Decisiones que suelen discutirse

**Por qué Next.js y no React + Vite.** El producto se distribuye por WhatsApp. Una SPA de Vite
pegada en un grupo muestra un cuadro gris; Next.js muestra la tarjeta con logo, nombre del
torneo y fase. En LATAM ese preview es el canal de distribución, no un detalle estético.
Sumado a que Google indexa "torneo MLBB Bolivia" y te encuentra.

**Por qué Railway Postgres y no Neon.** Neon tiene cold start de ~20s y techo de 100 horas de
cómputo mensuales. Una web de torneos tiene picos brutales (noche de final) y valles de días.
El cold start pega justo cuando más gente mira.

**Por qué polling y no WebSockets.** Polling de 15–30s cubre el caso de uso. WebSockets agregan
reconexión, estado de conexión y complejidad de escalado horizontal, y nadie percibe la
diferencia mirando un bracket. Se puede agregar después si hace falta.

**Por qué Discord OAuth y no email/contraseña.** No manejás contraseñas ni recuperación de
cuenta (menos código y menos superficie de ataque), el registro es un click, y la comunidad
ya vive en Discord: no le pedís al capitán que cree una cuenta más. De paso queda guardado el
Discord ID, que es lo que necesitarías si algún día sumás un bot — pero la decisión se sostiene
sola aunque el bot nunca exista.

---

## 2. Vista de componentes

```
                        ┌──────────────────┐
                        │     Usuario      │
                        └────────┬─────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
             ┌──────▼───────┐        ┌────────▼────────┐
             │ Sitio público│        │  Panel admin    │
             │   (Next.js)  │        │ (rutas /admin)  │
             │    Vercel    │        │     Vercel      │
             └──────┬───────┘        └────────┬────────┘
                    │                         │
                    └────────────┬────────────┘
                                 │ HTTPS / JSON
                        ┌────────▼─────────┐
                        │  torneos-backend │
                        │    (FastAPI)     │
                        │     Railway      │
                        └────┬────────┬────┘
                             │        │
                  ┌──────────▼──┐  ┌──▼──────────────┐
                  │ PostgreSQL  │  │ Cloudflare R2   │
                  │  Railway    │  │  (evidencias)   │
                  └─────────────┘  └─────────────────┘
```

Una sola app Next.js sirve el sitio público y el panel de administración, con rutas protegidas.
No hacer dos frontends separados.

### Preparado para clientes futuros

El backend es la **única sede de la lógica de negocio**. El frontend no calcula tablas, no
decide quién clasifica, no valida transiciones de estado — solo muestra lo que la API devuelve.

Esto no es purismo: es lo que permite agregar después un bot de Discord, una app móvil o un
panel de streaming **sin rediseñar nada**. Cualquier cliente nuevo se conecta a la misma API
con un token de servicio y hereda todas las reglas. Si en cambio metés lógica en el frontend
"para que se vea más rápido", cada cliente nuevo la tiene que reimplementar y se desincronizan.

Mantener esta disciplina ahora es lo que hace que el bot sea trabajo de días más adelante en
vez de un rediseño.

---

## 3. Capas del backend

```
app/
├── main.py                    # App, lifespan, CORS, routers
├── core/
│   ├── config.py              # Settings desde .env
│   └── security.py            # JWT, verificación OAuth
│
├── domain/                    # ← Sin dependencias externas. Puro Python.
│   ├── entidades/             # Torneo, Edicion, Fase, Equipo, Partida, Participacion
│   ├── enums.py               # EstadoPartida, ModeloCompetencia, TipoSancion
│   ├── excepciones.py         # RosterBloqueadoError, TransicionInvalidaError...
│   ├── competencia/           # ← EJE 2: modelo de competencia
│   │   ├── base.py            #   interfaz ModeloDeCompetencia
│   │   ├── enfrentamiento_directo.py
│   │   └── multi_equipo.py
│   ├── formatos/              # ← EJE 3: formato de fase
│   │   ├── base.py            #   interfaz FormatoDeFase
│   │   ├── round_robin.py
│   │   ├── eliminacion_simple.py
│   │   ├── eliminacion_doble.py
│   │   └── suizo.py
│   │       # liga_acumulativa.py (battle royale) NO existe: se planificó,
│   │       # nunca se escribió, y el formato salió del enum. Vuelve cuando
│   │       # haya motor multi-equipo.
│   └── puntaje/
│       ├── base.py            #   interfaz SistemaDePuntaje
│       ├── victoria_derrota.py
│       └── posicion_y_bajas.py
│
├── application/               # Casos de uso. Orquesta dominio + puertos.
│   ├── puertos/               # Interfaces de repositorio
│   └── casos_uso/
│       ├── inscribir_equipo.py
│       ├── reportar_resultado.py
│       ├── confirmar_resultado.py
│       ├── cargar_tabla_caida.py
│       ├── calcular_tabla_posiciones.py
│       ├── cerrar_fase.py
│       └── sortear_fase.py
│
├── infrastructure/            # Detalles. Depende de todo lo de arriba.
│   ├── db/
│   │   ├── database.py        # engine, SessionLocal, Base, get_db
│   │   ├── modelos/           # SQLAlchemy (≠ entidades de dominio)
│   │   ├── repositorios/      # Implementación de los puertos
│   │   └── seed.py            # Catálogo de juegos
│   ├── almacenamiento/        # Cliente R2
│   └── eventos/               # Publicación de eventos de dominio (consumidores futuros)
│
└── api/
    ├── deps.py                # DbSession, CurrentUser, RequiereOrganizador
    ├── schemas/               # Pydantic (contrato HTTP)
    └── routes/                # juegos, torneos, ediciones, equipos,
                               # inscripciones, partidas, disputas, posiciones
```

**Regla de dependencias**: `api` → `application` → `domain`. `infrastructure` implementa
interfaces de `application`. `domain` no importa nada de las otras capas.

---

## 4. Los tres ejes de variación

Todo el diseño gira sobre tres cosas que cambian y que nunca deben acoplarse entre sí.

### Eje 1 — El juego (configuración, no código)

Fila en la tabla `juegos`. Declara tamaño de equipo, campos de identidad del jugador, modelo de
competencia por defecto, si tiene draft/ban.

```
MLBB        5+2   identidad: nick + id_juego + server     enfrentamiento_directo
Free Fire   4+1   identidad: nick + uid                   multi_equipo
CODM MP     5+2   identidad: nick + uid                   enfrentamiento_directo
CODM BR     4+1   identidad: nick + uid                   multi_equipo
Wild Rift   5+2   identidad: riot_id + tag                enfrentamiento_directo
```

Agregar un juego = insertar una fila. Si requiere migración o deploy, el diseño falló.

### Eje 2 — Modelo de competencia (interfaz)

```python
class ModeloDeCompetencia(Protocol):
    def participantes_por_partida(self, config) -> tuple[int, int]: ...
    def validar_resultado(self, partida, resultado) -> None: ...
    def calcular_puntos(self, participacion, sistema_puntaje) -> int: ...
    def flujo_de_confirmacion(self) -> FlujoConfirmacion: ...
```

- `EnfrentamientoDirecto` — 2 participantes, resultado = marcador, confirma el rival.
- `MultiEquipo` — 12 a 25 participantes, resultado = posición + bajas, carga el organizador.

### Eje 3 — Formato de fase (interfaz)

```python
class FormatoDeFase(Protocol):
    def generar_partidas(self, equipos, config) -> list[Partida]: ...
    def procesar_resultado(self, partida, estado_fase) -> list[EventoDominio]: ...
    def clasificados(self, estado_fase, cupos) -> list[Equipo]: ...
    def esta_completa(self, estado_fase) -> bool: ...
```

Un cambio en un eje no debe obligar a tocar los otros dos. Si al agregar Free Fire hay que
modificar `eliminacion_doble.py`, hay acoplamiento.

---

## 5. Modelo de datos (núcleo)

```
juegos
  id, codigo, nombre, titulares_requeridos, suplentes_maximos,
  modelo_competencia_default, campos_identidad (JSONB)

torneos
  id, nombre, slug, organizador_id

ediciones
  id, torneo_id, juego_id, numero, nombre, estado,
  sistema_puntaje (JSONB), criterios_desempate (JSONB),
  zona_horaria, version_reglamento
  # fecha_roster_lock estuvo como `roster_lock` y se eliminó: existió desde
  # el esquema inicial sin que ningún código la leyera nunca.

fases
  id, edicion_id, orden, nombre, modelo_competencia, formato,
  config (JSONB: bo, caidas_por_ronda, cupos_avance), estado, semilla_sorteo

grupos                      -- grupos (directo) o lobbies (multi-equipo)
  id, fase_id, nombre, ronda

equipos
  id, nombre, tag, logo_url, esta_activo

jugadores
  id, equipo_id, identidad (JSONB), clave_identidad, es_suplente, es_capitan,
  discord_id, esta_activo

inscripciones
  id, edicion_id, equipo_id, estado, estado_pago, created_at
  UNIQUE (edicion_id, equipo_id)

partidas                    ← SIN equipo_a / equipo_b
  id, fase_id, grupo_id, numero_caida, estado,
  programada_para (tz), confirmada_at (tz)

participaciones_partida     ← LA TABLA CLAVE
  id, partida_id, equipo_id,
  mapas_ganados, es_ganador,        -- enfrentamiento directo
  posicion, bajas,                  -- multi-equipo
  puntos                            -- calculado
  UNIQUE (partida_id, equipo_id)

resultados_reportes         -- append-only, nunca UPDATE
  id, partida_id, reportado_por, datos (JSONB), evidencia_url,
  es_correccion_de, motivo, created_at

disputas
  id, partida_id, abierta_por, motivo, evidencia_url,
  estado, resuelta_por, resolucion, resuelta_at

sanciones
  id, edicion_id, equipo_id, tipo, puntos_restados, motivo,
  aplicada_por, created_at

auditoria
  id, entidad, entidad_id, accion, usuario_id, datos_antes, datos_despues, created_at
```

**Dos participaciones = MLBB. Dieciocho participaciones = Free Fire. Mismo esquema.**

La elegibilidad se garantiza con `UNIQUE (edicion_id, clave_identidad)` sobre jugadores
inscritos: un jugador no puede estar en dos equipos de la misma edición.

---

## 6. Flujos críticos

### Reporte en enfrentamiento directo (MLBB)

```
Capitán A → POST /partidas/{id}/reportar {marcador, evidencia}
          → estado: reportada
          → evento PartidaReportada → notificación a capitán B
Capitán B → POST /partidas/{id}/confirmar
          → TRANSACCIÓN: confirmar + avanzar ganador en llave + invalidar caché tabla
          → estado: confirmada
```

Si B no responde en X horas → auto-confirmación (solo si hay evidencia).
Si B contradice → `en_disputa`, decide el organizador.

### Carga en multi-equipo (Free Fire)

```
Organizador → POST /partidas/{id}/cargar-tabla {[{equipo, posicion, bajas}, ...]}
            → TRANSACCIÓN: las 12–25 participaciones entran juntas o ninguna
            → calcular puntos con SistemaDePuntaje de la edición
            → estado: confirmada, se abre ventana de reclamo
```

Media tabla cargada es peor que nada. Por eso una sola transacción.

### Corrección de un resultado confirmado

```
Organizador → POST /partidas/{id}/corregir {datos, motivo}
            → NUEVA fila en resultados_reportes (es_correccion_de = anterior)
            → recalcular tabla de la fase
            → si cambia quién clasificó: ADVERTIR antes de aplicar
            → registrar en auditoria
```

Nunca `UPDATE` sobre el resultado original.

---

## 7. Seguridad y roles

| Rol | Permisos |
|-----|----------|
| `organizador` | Todo dentro de sus torneos |
| `staff` | Resuelve disputas, carga caídas. No cierra fases ni cambia config |
| `capitan` | Reporta y confirma solo por su equipo |
| `jugador` | Lectura |
| `publico` | Lectura de lo publicado |

- Autorización como dependencia de FastAPI (`RequiereOrganizador`), nunca `if user.rol ==`
  dentro del endpoint.
- Rate limit en reporte de resultados e inscripción.
- Idempotencia en reportes: los capitanes tocan el botón dos veces y la conexión se corta a
  mitad de request más seguido de lo que uno espera.
- Prever desde ya un tipo de credencial de **servicio** (distinto del token de usuario) para
  clientes automatizados futuros. No hace falta implementarlo ahora, sí dejar el espacio en
  el modelo de usuarios para no migrarlo después.

---

## 8. Orden de construcción

Cada etapa se prueba con el torneo real antes de pasar a la siguiente.

1. **Catálogo de juegos + equipos + inscripciones.** Sin partidas. Meta: reemplazar el Excel
   de rosters.
2. **Partidas con participaciones N + carga manual por el admin.** Sin llaves ni automatismo.
   Meta: reemplazar el Excel de seguimiento.
3. **Cálculo de tabla y desempates, con tests.** Acá ganás confianza real.
4. **Generación de grupos y llave** (formatos).
5. **Reporte por capitanes con doble confirmación.**
6. **Free Fire** — el segundo juego es el que dice si la abstracción funcionó.

La 2ª edición del torneo de MLBB debería correr sobre los pasos 1–3. No esperar a tener todo.

**Alcance del MVP: solo torneos.** Sin bot, sin chat, sin recargas. Cada una de esas cosas es
un producto aparte que se conecta a esta API cuando el núcleo esté probado en producción.

---

## 9. Tests obligatorios

Cuatro áreas donde un bug es visible ante 45 capitanes:

- Cálculo de tabla y desempates (incluido empate de 3+ equipos, en ambos modelos)
- Avance de llave (byes en simple, mapeo de perdedores en doble eliminación)
- Cálculo de puntos multi-equipo (posición + bajas, no-show, multiplicador de caída final)
- Transiciones de estado de partida (que las inválidas fallen)

Además: todo servicio del núcleo con un test parametrizado que corra el mismo caso con
configuración de MLBB y de Free Fire. Es lo único que detecta acoplamiento a un juego antes
de producción.

---

## 10. Evolución futura (fuera del alcance actual)

Nada de esto se construye ahora. Se documenta solo para no tomar hoy decisiones que lo
imposibiliten mañana.

### Lo único que hay que preservar desde el inicio

**La identidad del jugador.** Cuando un capitán inscribe su equipo, el sistema ya guarda el
ID de juego + server de MLBB o el UID de Free Fire de cada jugador, verificado contra un torneo
real. Ese dato es exactamente el que necesita una recarga para entregar diamantes.

Es la sinergia real entre torneos y recargas, y es la razón por la que el orden importa: el
torneo genera la base de usuarios verificados que la recarga necesita. Al revés no funciona.

Por eso: **modelar `usuario` como entidad propia desde el paso 1**, no como un campo dentro de
`jugador`. Un usuario tiene identidades de juego (una por título) y participa en equipos. Si
lo aplanás ahora, migrarlo después con datos reales en producción es doloroso.

### Módulos posibles, cada uno independiente

| Módulo | Se conecta a | Complejidad real |
|--------|--------------|------------------|
| Bot de Discord | API vía token de servicio | Baja — ya tenés la experiencia |
| Recargas / créditos de juego | Módulo aparte, comparte `usuario` | **Alta** — pagos y entrega |
| Predicciones sin dinero | API, lee partidas | Media |
| App móvil | Misma API | Media |

**Sobre recargas, sin adornos**: el código es la parte fácil (ya lo hiciste en el bot de
Arkade). Lo difícil es lo otro — integrar pagos locales (QR Simple, Tigo Money, transferencia),
manejar el desfase entre "el cliente dice que pagó" y "el pago se acreditó", conseguir y
sostener el margen con el proveedor de créditos, y responder cuando una entrega falla y el
cliente ya pagó. Eso es operación y capital de trabajo, no arquitectura.

Cuando llegue el momento, va como **módulo separado con su propia base de datos o su propio
esquema**, compartiendo solo la identidad del usuario. Nunca mezclado con las tablas de torneo:
un problema de facturación no puede tumbar un torneo en vivo.

---

## 11. Riesgos conocidos

| Riesgo | Mitigación |
|--------|-----------|
| Pico de tráfico en la final | Caché de vista pública con invalidación por evento |
| Resultado mal cargado en vivo | Corrección auditable + advertencia si cambia clasificación |
| Pérdida de evidencias | R2 con retención, nunca disco efímero |
| Acoplamiento a MLBB | Tests parametrizados con dos juegos desde el inicio |
| Operación en vivo sin rollback | Backup verificado antes de cada noche de torneo |
| Proyecto largo en solitario | Orden de construcción incremental, cada etapa usable |
