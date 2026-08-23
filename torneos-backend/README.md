# Plataforma de Torneos — Backend

Paso 1: catálogo de juegos, torneos, ediciones e inscripción autónoma de equipos.

## Correr local (Windows / PowerShell)

> **Si estás abriendo esto en Cursor o Antigravity**: el proyecto trae
> reglas de contexto ya armadas — `.cursor/rules/*.mdc` para Cursor,
> `.agents/rules/*.md` + `AGENTS.md` en la raíz para Antigravity (o
> cualquier otra herramienta que lea ese formato). Incluyen, entre otras
> cosas, la regla `07-verificar-con-scripts`: **el agente tiene que correr
> el script `probar_*.py` correspondiente antes de dar por terminado
> cualquier cambio**, no alcanza con que el código compile.

```powershell
cd torneos-backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

Copy-Item .env.example .env

uvicorn app.main:app --reload
```

Abrí http://localhost:8000/docs — ahí podés probar todo sin escribir código.

Arranca con **SQLite** (archivo `torneos.db`) y crea las tablas solo
(`create_all`), no hace falta instalar Postgres ni correr Alembic para
desarrollar local. Cuando quieras pasar a Postgres, cambiás `DATABASE_URL`
en el `.env` — ahí Alembic pasa a ser obligatorio, ver la sección
[Migraciones (Alembic)](#migraciones-alembic) más abajo.

Si `Activate.ps1` da error de permisos:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Probar login sin credenciales reales de Discord

No hace falta crear una app en Discord para desarrollar local. `probar_utils.py`
emite tokens válidos directamente (ver [Autenticación](#autenticación-discord-oauth2)),
así que los 7 scripts `probar_*.py` corren sin ninguna configuración extra.

### Probar el flujo completo

```powershell
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
python probar_editar_inscripcion.py
python probar_fases_encadenadas.py
python probar_triple_fase.py
```

`probar_flujo.py` corre 7 casos de inscripción: equipo de 7 sin marcar suplentes,
capitán con nombre real, jugador repetido en dos equipos, roster incompleto, datos
faltantes, nombre duplicado, y un equipo de Free Fire.

`probar_checkin.py` corre 5 escenarios de partidas: check-in exitoso que arranca la
partida sola, walkover automático cuando un equipo no se presenta, partida que vuelve
a programada cuando nadie confirma, y dos disputas resueltas de las dos formas
posibles (walkover directo y reprogramar).

`probar_formatos.py` valida los **generadores de llave puros** (sin base de datos):
eliminación simple y doble para n=2 hasta 64 equipos incluyendo casos irregulares
(5, 7, 11, 17, 45...), verificando que cada uno converge a un único campeón sin
partidas huérfanas. También valida grupos de round robin y emparejamiento suizo.

`probar_sorteo.py` es la prueba end-to-end **con el tamaño real del torneo (45
equipos)**, a través de la API completa: sortea una llave de eliminación simple y
otra de eliminación doble, simula TODOS los resultados vía walkover, y verifica que
la llave completa (alta + baja + gran final) converge sola a un campeón sin ninguna
partida sin resolver.

`probar_resultado.py` cubre el **reporte de resultado normal con doble
confirmación**: reportar+confirmar, reportar+impugnar+resolver por el organizador,
auto-confirmación por vencimiento (con y sin evidencia), validaciones de marcador
contra el BO configurado, y — el caso que más importa — confirma que un resultado
real (no un walkover) también dispara el avance automático de la llave.

`probar_tabla.py` cubre la **tabla de posiciones**: sin grupos, dividida en grupos
independientes (cada uno con su propia tabla), walkover sin marcador cargado a mano
(se cuenta con el resultado "de reglamento" del BO configurado), y valida que pedir
la tabla de una llave de eliminación devuelve un error claro en vez de un resultado
sin sentido.

`probar_suizo.py` cubre el **formato suizo completo**: ronda 1 sembrada, bloqueo de
generar la ronda siguiente si la anterior no está resuelta, emparejamiento por
puntaje sin repetir rivales durante 3 rondas seguidas, y el caso de cantidad impar
(incluidos los 45 equipos reales del torneo) con bye automático al peor sembrado en
ronda 1 y al de menor puntaje en las rondas siguientes.

`probar_correccion.py` cubre la **corrección de un resultado ya confirmado**:
validaciones (empate, motivo muy corto, equipo que no corresponde), corrección
que no cambia el ganador, corrección que sí lo cambia antes de que la llave
avance (se corrige sola), y — el caso que más importa — corrección que cambia
el ganador *después* de que ya avanzó a la siguiente ronda, verificando que la
respuesta trae la advertencia explícita y que la partida siguiente no se toca
sola.

`probar_pulido.py` cubre los tres afinamientos de esta sesión: que el
`discord_id` esté oculto sin login y visible para el organizador, el endpoint
de resumen con últimos resultados y próximas partidas ordenados correctamente,
y el filtro de partidas por estado.

`probar_organizadores.py` cubre la **gestión de organizadores**: solo un
organizador puede listar usuarios o promover, un organizador promueve a un
segundo que de inmediato puede crear torneos, y la regla que impide dejar
la plataforma sin ningún organizador activo.

## Autenticación (Discord OAuth2)

No hay contraseñas — la identidad la garantiza Discord, el backend solo
emite su propio JWT después.

**Flujo real (con una app de Discord configurada):**
1. `GET /api/auth/discord/login` devuelve la URL de Discord.
2. El frontend redirige al usuario ahí; Discord le pide aprobar.
3. Discord redirige a `/api/auth/discord/callback?code=...`, que crea o
   actualiza el `Usuario` y devuelve `{access_token, usuario}`.
4. El frontend manda ese token en cada request:
   `Authorization: Bearer <token>`.

Para tener esto andando hace falta crear una app en
[discord.com/developers/applications](https://discord.com/developers/applications),
copiar `Client ID` y `Client Secret` al `.env`, y agregar el redirect URI
exacto (`http://localhost:8000/api/auth/discord/callback` en local) en la
sección OAuth2 de la app de Discord.

**Para desarrollar sin esa configuración:** `app/core/security_dev.py`
emite tokens válidos directamente, sin tocar Discord. Nunca se expone como
endpoint HTTP — solo se importa desde los scripts `probar_*.py`. Mirá
`probar_utils.py` para el patrón (`headers_organizador`, `headers_capitan`).

**Quién es organizador.** `Usuario.es_organizador` es una bandera global.
Al primer login, se activa sola si el `discord_id` está en
`DISCORD_IDS_ORGANIZADORES_INICIALES` (variable de entorno, separada por
comas) — sin esto, nadie podría promoverse a organizador nunca. Ese es solo
el arranque en frío; promover a alguien más después es
`PATCH /api/usuarios/{id}/rol` (ver más abajo).

**Cómo se verifica que sos el capitán de un equipo.** El body de
`/reportar`, `/confirmar`, `/impugnar` y `/checkin` sigue llevando
`equipo_id` explícito — eso solo no alcanza como autorización, así que el
backend compara el `discord_id` del token contra la tabla `Jugador`
(`es_capitan=True` para reportar/confirmar/impugnar; cualquier jugador del
equipo alcanza para check-in y para "reportar problema"). El organizador
puede actuar en nombre de cualquier equipo. Si el capitán nunca vinculó su
Discord (caso normal: el equipo se inscribió sin loguearse), estas acciones
devuelven 403 con un mensaje explicando que hay que pedirle al organizador
que lo vincule (`PATCH .../jugadores/{jid}/vincular-discord`).

## Gestión de organizadores — dos niveles, no uno

Al principio esto era un booleano plano (`es_organizador`), lo que significaba
que **cualquier organizador promovido tenía el mismo poder que quien lo
promovió** — incluido sacarle el rol a esa persona. Se corrigió agregando un
segundo nivel:

- **`es_organizador`** — opera el torneo entero: crea torneos y ediciones,
  aprueba inscripciones, sortea fases, resuelve disputas, corrige resultados.
- **`puede_gestionar_organizadores`** — el único que puede tocar *quién más*
  es organizador. Sin este permiso específico, ni siquiera podés sacarte el
  rol a vos mismo.

Alguien recién promovido con `PATCH .../rol {"es_organizador": true}` **no**
recibe el segundo nivel por defecto — puede operar el torneo entero, pero no
puede tocar la lista de organizadores, ni la suya propia. Solo quien ya tiene
`puede_gestionar_organizadores` puede otorgárselo a alguien más, con
`{"es_organizador": true, "puede_gestionar_organizadores": true}` en el mismo
pedido.

**Dos invariantes que no se pueden romper con un click de más:**
1. No se puede dejar la plataforma con cero organizadores activos.
2. No se puede dejar la plataforma con cero personas que puedan gestionar
   organizadores — si eso pasara, nadie podría corregirlo nunca más sin tocar
   la base de datos a mano.

En la práctica, la segunda invariante es siempre al menos tan estricta como
la primera (gestionar organizadores implica ser organizador, por construcción
— la cascada se lo saca a cualquiera al que se le saca `es_organizador`), así
que es la que dispara primero cuando ambas aplicarían.

`GET /api/usuarios` — exige `puede_gestionar_organizadores`, no alcanza con
ser organizador a secas. Lista a todos los que ya iniciaron sesión alguna vez
— **la persona tiene que haber hecho login al menos una vez antes** de poder
promoverla, porque hasta que no se loguea no existe la fila de `Usuario` a la
que asignarle el rol. Admite `?discord_id=` para buscar puntual.

`PATCH /api/usuarios/{id}/rol` — mismo requisito. Body:
`{"es_organizador": bool, "puede_gestionar_organizadores": bool | null}` — si
se omite el segundo campo, se hereda el valor actual (salvo que se esté
sacando `es_organizador`, ahí cae en cascada solo).

**Quién arranca con el permiso completo.** El primer login de cada
`discord_id` en `DISCORD_IDS_ORGANIZADORES_INICIALES` recibe **ambos**
niveles de una — es el/los fundador(es) de la plataforma. Cuando se
despliega esta migración sobre una base que ya tenía organizadores de antes
(de cuando el sistema era un booleano plano), la migración les preserva el
permiso completo a todos — si no, un despliegue de esto hubiera dejado a la
plataforma sin nadie que pueda gestionar nada, ni siquiera vos.

Probado en `probar_organizadores.py`: un capitán no puede tocar nada de
esto (403), el fundador promueve a un segundo organizador que de inmediato
puede operar el torneo pero no puede ver ni tocar la lista de organizadores
(403 en ambos), el fundador le otorga el segundo nivel explícitamente y ahí
sí puede, las dos invariantes de seguridad, y la validación de que no se
puede dar el segundo nivel a alguien que al mismo tiempo deja de ser
organizador.

## Evidencia

Las capturas de resultados y disputas se suben con
`POST /api/evidencias/subir` (multipart, campo `archivo`) y devuelven la
URL para usar en `evidencia_url`. Máximo 8 MB, solo `.png/.jpg/.jpeg/.webp`
— es una captura de pantalla, no un archivo cualquiera.

**En desarrollo** (`ALMACENAMIENTO_LOCAL=true`, el default): se guarda en
disco bajo `ALMACENAMIENTO_LOCAL_DIR` y se sirve por
`GET /api/evidencias/archivo/{clave}` — no hace falta cuenta de Cloudflare
para probar el flujo completo.

**En producción** (`ALMACENAMIENTO_LOCAL=false`): sube a Cloudflare R2 via
el mismo cliente S3 (`boto3`) que usarías para AWS — R2 es compatible con
esa API. Hace falta `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`,
`R2_SECRET_ACCESS_KEY`, `R2_BUCKET` y `R2_PUBLIC_BASE_URL` en el `.env`. El
resto del código nunca sabe cuál de los dos modos está activo — solo llama
a `subir_evidencia()` y usa la URL que le devuelve.

## Endpoints

Columna **Quién**: `público` = sin login; `logueado` = cualquier usuario con
sesión; `capitán` = verificado contra el equipo del body (el organizador
también puede); `organizador` = requiere `es_organizador=true`; `gestor de
organizadores` = requiere además `puede_gestionar_organizadores=true` (ver
[Gestión de organizadores](#gestión-de-organizadores--dos-niveles-no-uno)).

| Método | Ruta | Quién | Qué hace |
|--------|------|-------|----------|
| GET | `/api/auth/discord/login` | público | URL de Discord a la que redirigir |
| GET | `/api/auth/discord/callback` | público | Discord vuelve acá con el código; devuelve el token |
| GET | `/api/auth/discord/yo` | logueado | Quién soy según mi token |
| **GET** | **`/api/usuarios`** | **gestor de organizadores** | **Quiénes ya iniciaron sesión — de acá se elige a quién promover** |
| **PATCH** | **`/api/usuarios/{id}/rol`** | **gestor de organizadores** | **Promover, sacar el rol, u otorgar/sacar el permiso de gestión en sí** |
| **POST** | **`/api/evidencias/subir`** | **logueado** | **Sube una captura, devuelve la URL para `evidencia_url`** |
| GET | `/api/juegos` | público | Catálogo con los campos de identidad de cada juego |
| POST | `/api/torneos` | organizador | Crear torneo |
| GET | `/api/torneos` | público | Listar torneos |
| POST | `/api/ediciones` | organizador | Crear edición (fija el juego) |
| GET | `/api/ediciones/{id}` | público | Detalle de edición |
| **GET** | **`/api/ediciones/{id}/resumen`** | **público** | **"Vista general": últimos resultados + próximas + info, en un solo pedido** |
| POST | `/api/ediciones/{id}/estado` | organizador | Abrir/cerrar inscripciones |
| **POST** | **`/api/ediciones/{id}/inscripciones`** | **público** | **Registro de equipo, sin login** |
| **PATCH** | **`/api/ediciones/{id}/inscripciones/{id}`** | **capitán** | **Editar equipo/roster — bloqueado si ya está en una fase** |
| GET | `/api/ediciones/{id}/inscripciones` | público | Listar (filtro por `?estado=`) |
| POST | `/api/ediciones/{id}/inscripciones/{ins}/revisar` | organizador | Aprobar / rechazar |
| PATCH | `.../jugadores/{jid}/vincular-discord` | organizador | Vincula el Discord real de un jugador tras la inscripción |
| POST | `/api/ediciones/{id}/inscripciones/sembrar-automatico` | organizador | Asigna seed 1..N a los equipos aprobados |
| PATCH | `/api/ediciones/{id}/inscripciones/{ins}/seed` | organizador | Ajustar un seed puntual a mano |
| POST | `/api/ediciones/{id}/fases` | organizador | Crear fase |
| GET | `/api/ediciones/{id}/fases` | público | Listar fases |
| **POST** | **`.../fases/{fid}/sortear`** | **organizador** | **Genera toda la llave/grupos/ronda 1 de una vez** |
| **POST** | **`.../fases/{fid}/cerrar`** | **organizador** | **Cierra la fase (exige todas sus partidas resueltas)** |
| **POST** | **`.../fases/{fid}/sortear-desde-fase-anterior`** | **organizador** | **Clasificados de otra fase — de grupos (tabla) o de una ronda de bracket** |
| **POST** | **`.../fases/{fid}/siguiente-ronda-suiza`** | **organizador** | **Genera la próxima ronda suiza (solo si la anterior está resuelta)** |
| GET | `.../fases/{fid}/tabla` | público | Tabla de posiciones (round robin/suizo), con desempates |
| GET | `/api/fases/{id}/partidas` | público | Todas las partidas (`?estado=` o `?resueltas=true/false` para filtrar) |
| POST | `/api/fases/{id}/partidas` | organizador | Crear partida (manual) |
| GET | `/api/fases/{id}/partidas/{pid}` | público | Detalle de partida con participaciones |
| POST | `.../{pid}/abrir-checkin` | organizador | Abre la ventana de check-in |
| **POST** | **`.../{pid}/checkin`** | **capitán** | **Un jugador del equipo confirma presencia** |
| POST | `.../{pid}/resolver-checkin` | organizador | Cierra la ventana vencida y aplica walkover si corresponde |
| **POST** | **`.../{pid}/reportar`** | **capitán** | **Reporta el marcador de la partida** |
| **POST** | **`.../{pid}/confirmar`** | **capitán** | **El rival confirma — avanza la llave** |
| **POST** | **`.../{pid}/impugnar`** | **capitán** | **El rival no está de acuerdo — abre disputa** |
| POST | `.../{pid}/resolver-reporte-vencido` | organizador | Auto-confirma si venció el plazo (solo con evidencia) |
| **POST** | **`.../{pid}/corregir-resultado`** | **organizador** | **Corrige un resultado ya `confirmada`, sin disputa activa** |
| GET | `.../{pid}/historial-resultado` | público | Todos los reportes/correcciones de esa partida, en orden |
| **POST** | **`.../{pid}/reportar-problema`** | **jugador del equipo** | **"Reportar problema" — abre una disputa** |
| GET | `/api/fases/{id}/partidas/{pid}/disputas` | público | Disputas de una partida |
| GET | `/api/disputas` | organizador | Bandeja del organizador (filtro `?estado=abierta`) |
| POST | `/api/disputas/{id}/resolver` | organizador | Resolver: `reprogramar`, `walkover` o `confirmar_resultado` |

## Reporte de resultado con doble confirmación

Esta es la pieza que faltaba para que la plataforma sirva más allá de simular
walkovers: el camino normal de una partida que sí se jugó.

**Flujo**: `en_curso` → un capitán **reporta** → el rival **confirma** (avanza la
llave) o **impugna** (abre una disputa) → si el rival no reacciona, se puede
**auto-confirmar** una vez vencido el plazo, pero **solo si el reporte tiene
evidencia adjunta**. Sin evidencia, queda trabado a propósito hasta que alguien
confirme a mano o el organizador lo resuelva por disputa — es la regla de negocio
documentada desde el principio, no un descuido.

**El marcador se valida contra el BO de la fase** (`fase.config["bo"]`, default 1):
no se acepta un empate, no se acepta un marcador que no alcanza para ganar (ej. 1-0
en un BO3), y no se acepta una suma que supere el formato (ej. 2-2 en un BO3).

**Quien reportó no puede confirmar su propio reporte** — tiene que ser el rival.

**Resolver una impugnación** reutiliza la misma bandeja de disputas que ya existía:
`POST /disputas/{id}/resolver` ahora acepta una tercera acción,
`confirmar_resultado`, donde el organizador carga el marcador que corresponde en
vez de forzar un walkover sobre una partida que sí se jugó.

**Un resultado confirmado normalmente avanza la llave igual que un walkover** —
ambos caminos llaman al mismo `avanzar_ganador`, probado en `probar_resultado.py`
con un caso de punta a punta: se reporta, se confirma, y la partida siguiente de la
llave queda con el ganador ya cargado, solo.

## Afinamientos a partir de referencias reales

Después de mirar capturas de un torneo real de MLBB corriendo en Toornament,
aparecieron tres cosas — una de privacidad real, dos de conveniencia.

**Privacidad: `discord_id` ya no es público.** `GET /ediciones/{id}/inscripciones`
no tenía ningún control de acceso, y devolvía el `discord_id` de cada jugador a
cualquiera — un identificador real de una persona, a veces menor de edad, sin
ninguna razón de negocio para ser público solo porque el roster del equipo sí lo
es. Ahora se redacta (`None`) para cualquiera que no esté logueado como
organizador — vía una dependencia de auth opcional
(`get_current_user_opcional` en `app/api/deps.py`) que no exige token, pero
si hay uno válido y es de un organizador, muestra el dato completo. El resto
del roster (nicks, si es titular/suplente) sigue público, que es lo que
necesita una pestaña de "Participantes".

**`GET /ediciones/{id}/resumen`** — la pantalla de "Vista general" que se ve en
la captura (últimos resultados + próximas partidas + info del juego + fases)
armada en un solo pedido, en vez de que el frontend combine media docena de
llamadas. Devuelve las 6 partidas confirmadas más recientes (de cualquier fase
de la edición, ordenadas por cuándo se confirmaron) y las 6 próximas sin
resolver (ordenadas por horario programado).

**Filtro de partidas por estado.** `GET /fases/{id}/partidas` ahora acepta
`?estado=confirmada` para un estado puntual, o el atajo `?resueltas=true` /
`?resueltas=false` — el mismo par de pestañas "Resultados" / "A continuación"
que tiene Toornament en su vista de Encuentros.

## Corregir un resultado ya confirmado

Distinto de todo lo anterior: esto es para cuando **nadie impugnó nada**, pero el
organizador nota días después que un resultado está mal cargado. Si en cambio hay
una disputa activa (`en_disputa`), eso ya lo resuelve `POST /disputas/{id}/resolver`
con `accion: "confirmar_resultado"` — la corrección es específicamente para una
partida en estado `confirmada` sin ningún reclamo pendiente.

`POST /fases/{id}/partidas/{pid}/corregir-resultado` — solo organizador, motivo
obligatorio (mínimo 10 caracteres, queda auditado).

**Nunca se sobrescribe el registro anterior.** Cada corrección crea un
`ReporteResultado` nuevo con `es_correccion=True`, mientras que el reporte y la
confirmación originales quedan intactos. `GET .../historial-resultado` devuelve
la secuencia completa — se puede reconstruir "qué se sabía en cada momento".

**Si la corrección no cambia quién ganó** (solo ajusta el marcador de mapas), se
aplica directo, sin avisos — no afecta el avance de la llave ni cambia nada más
que la diferencia de mapas en la tabla (que se recalcula sola al pedirla, no hay
que tocar nada aparte).

**Si la corrección SÍ cambia el ganador**, hay dos casos:
- Si esa partida **todavía no había propagado** su resultado a la siguiente ronda
  (por ejemplo, era la única jugada de la fase), el sistema llama a
  `avanzar_ganador` de nuevo y el equipo correcto queda colocado solo, sin avisos.
- Si **ya se había propagado** (la partida siguiente ya tiene al ganador anterior
  cargado), la corrección se aplica igual en esta partida, pero la respuesta trae
  una `advertencia` explícita diciendo exactamente qué partida revisar a mano.
  **A propósito no se deshace la cascada sola** — es la decisión más segura:
  reescribir automáticamente una llave que ya avanzó (que puede tener check-ins,
  reportes, o hasta otra partida ya jugada colgando de esa rama) es mucho más
  riesgoso que pedirle al organizador un paso manual con el contexto completo
  delante.

Probado en `probar_correccion.py`, incluido ese caso exacto: una llave de 4
equipos donde se corrige el resultado de una semifinal después de que la final ya
tenía al ganador (incorrecto) cargado — la corrección no toca la final sola, y el
mensaje de advertencia dice cuál hay que arreglar.

## Encadenar fases — grupos → playoffs → doble eliminación

Este era un hueco grande, encontrado buscando específicamente en la documentación
real de Toornament (no inventado): antes, `sortear` **siempre** usaba el `seed`
global de la edición para armar una fase — no había forma de decirle "tomá los
clasificados de la fase anterior". Eso bloqueaba el formato real de este torneo:
grupos → ronda de 16 → los que quedan arrancan una llave doble.

`POST /fases/{id}/sortear-desde-fase-anterior` tiene **dos fuentes posibles**,
según qué tipo de fase sea la de origen — cubre tanto "vengo de una fase con tabla"
como "vengo de una fase con bracket":

**Desde grupos o suizo** (`cupos_por_grupo` en el body) — el patrón de Toornament
("Outgoing Participants" ordenados por rango). Exige que la fase de origen esté
`cerrada` (`POST /fases/{id}/cerrar`, que a su vez exige que **todas** sus partidas
estén en un estado terminal — `confirmada`, `walkover` o `bye`). Calcula la tabla de
cada grupo, toma los primeros `cupos_por_grupo` de cada uno, y arma el orden
intercalando: todos los 1ros de cada grupo primero, después todos los 2dos — así el
1° y el 2° del mismo grupo no se cruzan en la primera ronda de la llave nueva.

**Desde una eliminación simple** (`ronda_origen` en el body) — toma los ganadores de
**esa ronda puntual**, sin exigir que el resto de la llave se juegue ni se cierre
nunca. Es el caso real de "grupos → ronda de 16 (16 equipos, un solo round) → los 8
ganadores arrancan una llave doble completamente nueva" — las rondas 2, 3 y la final
de esa llave de 16 original quedan huérfanas para siempre, y eso está bien: nunca
hicieron falta.

Cerrar una fase, de paso, resolvió otro campo fantasma: `EstadoFase.CERRADA` y
`EN_CURSO` existían en el enum desde el principio, pero nunca los seteaba nada —
igual que pasaba con `roster_lock`, que era la otra promesa vacía del esquema y
que terminó eliminado por eso mismo.

Probado en dos escenarios reales:

- `probar_fases_encadenadas.py`: **24 equipos, 4 grupos de 6**, resueltas con
  reporte y confirmación real, cierre de la fase, y verificación de que los 8
  equipos que entran a playoffs son exactamente el top 2 de cada grupo — ni uno
  de más, ni uno de menos.
- `probar_triple_fase.py`: la cadena completa de tres fases, con el tamaño real
  del torneo — **40 equipos → 8 grupos de 5 → 16 clasificados → eliminación
  simple (solo la ronda de 16, sin jugar el resto de esa llave) → los 8 ganadores
  arman una llave doble (alta + baja + gran final) nueva** — verificando que los
  equipos de la llave doble coinciden exactamente con los ganadores de esa ronda.

## Generación de llaves

Cuatro formatos, todos con la misma cantidad de equipos que quieras:

**Eliminación simple.** Se calcula la potencia de 2 más chica ≥ N (para 45 equipos,
64) y el resto se llena con byes que avanzan solos. El orden de siembra separa a los
mejores puestos lo más posible (1 vs el último, 2 vs el anteúltimo, etc.) — el mismo
criterio que usan Toornament y Challonge.

**Eliminación doble.** Reutiliza la llave alta de eliminación simple. La llave baja se
construye simulando ronda por ronda: cada perdedor de la llave alta cae en el momento
que le corresponde, alternando rondas donde los sobrevivientes de la baja juegan entre
sí con rondas donde absorben la nueva caída de la alta. Cuando un bye de la llave alta
hace que sobre un equipo sin pareja en la baja, ese equipo **no genera una partida
fantasma** — pasa directo a la ronda siguiente. Validado matemáticamente para 2 a 64
equipos (incluidos números irregulares: 5, 7, 11, 17, 45, 48) contra la invariante de
que el total de partidas jugadas siempre es `2N-2`.

**Round robin.** Todos contra todos. Si `config.grupos` está seteado, reparte los
equipos en esa cantidad de grupos con siembra en serpentina (el 1° al grupo A, el 2°
al B... y vuelve en sentido inverso) para que los mejores puestos no queden todos
juntos.

**Suizo.** La ronda 1 se genera con `/sortear` (mitad superior contra mitad
inferior); las rondas siguientes se piden una por vez con
`POST .../fases/{id}/siguiente-ronda-suiza`, que **bloquea si la ronda
anterior no está completamente resuelta** — el formato no permite
precalcular todo de una, cada ronda depende de los resultados de la
anterior. Empareja por puntaje evitando repetir rivales cuando es posible
(si no queda ningún rival nuevo disponible, prefiere repetir antes que
dejar a alguien sin partida). **Cantidad impar de equipos**: el peor
sembrado recibe el bye en la ronda 1 (no hay tabla de puntos todavía para
elegir de otra forma); en las rondas siguientes, el bye va para el equipo
de menor puntaje que todavía no lo recibió. Un bye suma los puntos de una
victoria en la tabla, sin afectar la diferencia de mapas — no hay rival
real. Probado con el caso real del torneo: 45 equipos, 3 rondas seguidas
sin un solo rival repetido.

**Cómo avanza un ganador.** Cada partida guarda a dónde va su ganador
(`siguiente_partida_ganador_id` + `siguiente_slot_ganador`) y, en la llave alta de
eliminación doble, a dónde cae su perdedor (`siguiente_partida_perdedor_id`). Un
walkover, una disputa resuelta, o una confirmación normal de resultado —
cualquiera de los tres caminos llama a `app/domain/sorteo.avanzar_ganador`, que
coloca automáticamente al equipo en la partida siguiente, en cascada si esa
partida también resulta ser un bye.

## Tabla de posiciones

La tabla **nunca se guarda como fuente de verdad** — se recalcula desde cero en
cada pedido, a partir de las partidas en estado `confirmada` o `walkover` de la
fase. Si corregís un resultado, la tabla del siguiente pedido ya refleja el
cambio solo, sin ningún paso extra.

**Puntaje configurable por edición.** `edicion.sistema_puntaje` define
`{"victoria": 3, "empate": 1, "derrota": 0}` (esos son los valores por
defecto si no se configura nada). No está hardcodeado en ningún lado.

**Desempates configurables y en orden.** `edicion.criterios_desempate` es una
lista; si no se define, usa el orden por defecto:
`puntos → enfrentamiento_directo → diferencia_mapas → mapas_ganados`.

**El enfrentamiento directo entre 3+ equipos empatados se resuelve como
mini-grupo**, no comparación par a par — es la regla que más se rompe en
implementaciones caseras. Si los resultados dentro del mini-grupo también
empatan (matemáticamente inevitable en un "triángulo perfecto": A le gana a
B, B le gana a C, C le gana a A), cae solo al siguiente criterio de la lista.
`app/domain/tabla.py` no tiene dependencias de la base de datos, así que se
puede probar con datos inventados sin levantar nada — ver el módulo para
ejemplos de este caso resuelto.

**Walkover sin marcador cargado a mano.** Si nunca se cargó `mapas_ganados`
en la participación (lo típico: la partida se resolvió por `resolver-checkin`
o por una disputa con acción `walkover`), la tabla no lo cuenta como 0-0 —
usa el resultado "de reglamento" (el máximo del BO configurado para el
ganador, 0 para el ausente), para no perjudicar la diferencia de mapas de
quien sí se presentó.

**Con grupos, cada grupo tiene su propia tabla independiente** —
`GET /fases/{id}/tabla` devuelve una lista, una entrada por grupo (o una sola
con `grupo: null` si la fase no está dividida).

**Solo aplica a round robin y suizo.** Pedir la tabla de una llave de
eliminación devuelve un 422 explícito — ahí no hay tabla, hay bracket
(`GET /fases/{id}/partidas`).

## Reglas implementadas — inscripciones

**Suplentes automáticos.** Si el equipo no marca quién es suplente, se asignan los
últimos de la lista según el tamaño del juego. MLBB con 7 jugadores → últimos 2.
Free Fire con 5 → último 1.

**Capitán.** Si el nombre declarado no coincide con ningún nick del roster (dieron el
nombre real), se marca al primero de la lista.

**Elegibilidad.** Un jugador no puede estar en dos equipos de la misma edición. Se
valida por la clave del juego — ID+server en MLBB, UID en Free Fire — nunca por nick,
porque el nick se cambia y el ID no.

**Avisos.** El endpoint devuelve `avisos` con todo lo que el sistema asumió, para que
el equipo pueda corregir antes de que el organizador apruebe.

**Nada se borra.** Las inscripciones cambian de estado (pendiente → aprobada /
rechazada / retirada / descalificada). Rechazar exige motivo. **No hay DELETE**, a
propósito — si un equipo ya jugó partidas, borrarlo rompería el historial y
descuadraría la tabla. Para "sacar" a un equipo del torneo, el organizador lo pasa a
`retirada` o `descalificada` vía `POST .../revisar` — deja de contar como participante
activo, pero lo que ya jugó queda intacto.

## Editar una inscripción (roster, nombre, contacto)

**`PATCH /ediciones/{id}/inscripciones/{id}`** — el capitán (verificado por
`discord_id`, igual que en partidas) o el organizador, puede editar el equipo entero:
nombre, tag, logo, contacto, y el roster completo (se reemplaza entero, no hay un
"parche" campo por campo — con equipos de 5 a 7 personas no vale la pena la
complejidad de un diff).

El comportamiento calca el de Toornament, verificado contra su documentación real
antes de construirlo (no es una interpretación mía):

- **Mientras está `pendiente`**: se edita libremente, cuantas veces haga falta.
- **Si ya estaba `aprobada`**: al editar, **vuelve a `pendiente`** — a propósito. El
  organizador tiene que revisarla de nuevo antes de que vuelva a contar como
  aprobada; sin esto, un cambio de roster después de aprobado pasaría colado sin que
  nadie lo note. La respuesta incluye un aviso explícito de que esto pasó.
- **Una vez que el equipo ya fue colocado en una fase** (tiene al menos una
  `ParticipacionEnPartida` — el sorteo ya lo usó), **no se puede editar más, ni
  siquiera el organizador por este endpoint**. A partir de ahí, un cambio de roster
  se hace directo en la base — no hay todavía un camino de "forzar edición" para el
  organizador que salte este candado. Si hace falta, es un endpoint aparte a
  construir cuando surja el caso real, no algo que valga la pena adelantar sin uso.

**Elegibilidad, pero sin falsos positivos contra uno mismo.** Editar sin cambiar
nada no dispara "este jugador ya está inscrito" — el chequeo de duplicados excluye a
los propios jugadores de la inscripción que se está editando.

Probado en `probar_editar_inscripcion.py`: edición mientras pendiente, un capitán de
otro equipo no puede tocar una inscripción ajena (403), sin login no se puede (401),
aprobar y editar vuelve a pendiente con el aviso, cambio real de roster (reemplazar
un titular por otro nick), y el bloqueo total una vez sorteada la llave — para el
capitán y para el organizador por igual.

## Reglas implementadas — check-in y disputas

**Ventana de check-in.** El organizador la abre con `minutos` configurables (default
15). Cada equipo confirma con su `equipo_id`. Cuando confirman todos, la partida pasa
a `en_curso` **sola**, sin que el organizador intervenga.

**Walkover automático.** Si vence el tiempo y uno de dos equipos no confirmó, el
presente gana por walkover — lo resuelve `resolver-checkin`, que evalúa el estado real
sin asumir nada (por eso rechaza si todavía no venció el tiempo). Si nadie confirmó,
la partida vuelve a `programada` para reprogramarla, porque no hay ganador que declarar.

**"Reportar problema" es un canal aparte del reporte normal de resultado.** Sirve para
escalar directo al organizador — el rival no aparece, hay lag, sospecha de trampa — sin
pasar por el flujo de marcador. Abre una `Disputa`, la partida pasa a `en_disputa`, y
queda en la bandeja `/api/disputas` hasta que el organizador la resuelve con motivo.

**Resolver una disputa** tiene dos acciones por ahora: `walkover` (declara ganador
directo) o `reprogramar` (vuelve a `programada`, se juega de nuevo). Cargar un
resultado real y confirmarlo es el flujo normal de reporte, que todavía no existe —
es el próximo paso pendiente, junto con el generador de llaves.

## Nota técnica: fechas y SQLite

SQLite no preserva la zona horaria al guardar un `datetime` — lo devuelve "naive" al
leerlo, lo que rompe cualquier comparación de fechas (`>`, `<`) con un valor recién
creado. `app/db/database.py` define `DateTimeUTC`, un tipo de columna que reatacha la
zona horaria al leer. Se usa en **todas** las columnas de fecha del proyecto en vez de
`DateTime(timezone=True)` directo. En Postgres no cambia nada — el valor ya vuelve con
zona — pero mantiene el comportamiento idéntico entre desarrollo local y producción.

## Agregar un juego

Editar `app/db/seed.py`, agregar una entrada, reiniciar. No requiere migración ni
tocar el núcleo. Ya vienen MLBB, Free Fire, CODM (MP y BR) y Wild Rift.

## Migraciones (Alembic)

**En SQLite (desarrollo local) no hace falta tocar esto.** El `lifespan` de
`main.py` corre `create_all()` solo, cada vez que arrancás con `uvicorn
--reload`. Podés ignorar Alembic por completo mientras desarrollás.

**En Postgres (producción), Alembic es la única fuente de verdad del
esquema.** `create_all()` está deliberadamente desactivado ahí (ver
`es_sqlite` en `app/main.py`) — si corriera igual, crearía tablas por fuera
del control de versiones y Alembic dejaría de saber qué existe realmente.

```powershell
# Antes de levantar la app por primera vez contra una DB Postgres vacía:
alembic upgrade head

# Después de cambiar un modelo (agregar columna, tabla, etc.):
alembic revision --autogenerate -m "descripcion del cambio"
# revisar el archivo generado en alembic/versions/ ANTES de aplicarlo —
# autogenerate es una ayuda, no un oráculo. En particular, revisar SIEMPRE
# que el import de app.db.database esté presente si el diff toca una
# columna DateTimeUTC (autogenerate no lo agrega solo).
alembic upgrade head
```

La migración inicial (`alembic/versions/..._esquema_inicial.py`) ya está
generada y probada — creé las 12 tablas de negocio desde cero, apliqué
`upgrade head` y `downgrade base` sobre SQLite, y corrí la batería completa
de `probar_*.py` sobre la base resultante para confirmar que el esquema que
arma Alembic es funcionalmente idéntico al de `create_all()`.

`env.py` lee `DATABASE_URL` directo de `app.core.config.settings` (el mismo
`.env` que usa la API) — la URL que aparece en `alembic.ini` es un
placeholder que nunca se usa, no hay que tocarlo.

## Estructura

```
torneos-backend/
├── alembic/
│   ├── env.py                 Lee DATABASE_URL de settings, no del .ini
│   └── versions/               ..._esquema_inicial.py (probada: upgrade + downgrade)
├── alembic.ini
├── app/
│   ├── main.py                 App, lifespan, CORS, routers
│   ├── core/
│   │   ├── config.py            Settings desde .env (DB, JWT, Discord, R2)
│   │   ├── security.py          JWT propio + cliente de Discord OAuth2
│   │   ├── security_dev.py      SOLO pruebas: tokens sin pasar por Discord
│   │   └── almacenamiento.py    Subida de evidencia (R2 o disco local)
│   ├── domain/
│   │   ├── enums.py             Estados y formatos
│   │   ├── roster.py            Reglas de roster (puro Python)
│   │   ├── partidas.py          Check-in y validación de marcador (puro Python)
│   │   ├── sorteo.py            Persiste la llave y avanza ganadores (toca DB)
│   │   ├── tabla.py             Cálculo de tabla de posiciones (puro Python)
│   │   └── formatos/            Generadores puros — no tocan la DB
│   │       ├── base.py           Tipos compartidos (Cruce, Fuente)
│   │       ├── eliminacion_simple.py
│   │       ├── eliminacion_doble.py
│   │       ├── round_robin.py
│   │       └── suizo.py
│   ├── models/
│   │   ├── catalogo.py          Juego, Torneo, Edicion, Fase
│   │   ├── participantes.py     Equipo, Inscripcion, Jugador (con discord_id)
│   │   ├── partidas.py          Partida, ParticipacionEnPartida, Disputa, ReporteResultado
│   │   └── usuarios.py          Usuario (login por Discord)
│   ├── schemas/
│   │   ├── inscripciones.py
│   │   ├── fases.py
│   │   ├── partidas.py
│   │   └── usuarios.py
│   ├── api/
│   │   ├── deps.py               DbSession, CurrentUser, RequiereOrganizador, UsuarioOpcional
│   │   └── routes/
│   │       ├── auth.py            Login con Discord
│   │       ├── usuarios.py        Listar y promover organizadores
│   │       ├── evidencias.py      Subir/servir capturas
│   │       ├── torneos.py
│   │       ├── inscripciones.py
│   │       ├── fases.py
│   │       └── partidas.py
│   └── db/
│       ├── database.py           engine, sesión, Base, DateTimeUTC
│       └── seed.py               Catálogo de juegos
├── probar_utils.py               Tokens de prueba compartidos por los scripts
├── probar_flujo.py
├── probar_checkin.py
├── probar_formatos.py
├── probar_sorteo.py
├── probar_resultado.py
├── probar_tabla.py
├── probar_suizo.py
├── probar_correccion.py
├── probar_pulido.py
└── probar_organizadores.py
```

`domain/roster.py`, `domain/partidas.py`, `domain/tabla.py` y todo
`domain/formatos/` no importan nada de FastAPI ni SQLAlchemy — son las reglas de
negocio puras y se pueden testear solas, sin base de datos (ver
`probar_formatos.py`). `domain/sorteo.py` es la única pieza de la capa de dominio
que sí toca la DB: traduce la estructura pura de los generadores en filas reales y
resuelve los enlaces de avance.

## Pendiente

- **Frontend** — hay un primer avance visual (`torneos-web`, Next.js, estilo
  Toornament) pero se decidió construir el resto directo en el IDE en vez de
  seguir generándolo acá.
- **Rate limiting** en endpoints públicos (inscripción, login) — nada crítico para
  desarrollo, sí antes de exponerlo a internet sin ningún control delante.
- **Flujo de resultado para multi-equipo (Free Fire, battle royale)** — todo lo
  construido (reportar/confirmar/tabla/corregir) asume enfrentamiento directo.
  Cargar la tabla de una caída con posición+bajas de N escuadras es un endpoint
  aparte que todavía no existe.
- **Despliegue real a Railway/Postgres** — probado exhaustivamente en local con
  SQLite y con Alembic, pero nunca contra Postgres en producción.
