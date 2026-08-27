# Despliegue

Notas para poner esto en producción. Escritas contra Railway + Postgres, pero
casi todo aplica igual a Render o Fly.

> **Nunca corrió en producción.** Todo lo verificado —1716 tests, torneos
> completos, brackets, reportes— fue contra SQLite. La cadena de migraciones
> nunca tocó un Postgres real. El primer `alembic upgrade head` contra la base
> nueva es el momento de verdad; si algo falla, va a fallar ahí.

---

## Las tres cosas que rompen el despliegue si se pasan por alto

**1. Las migraciones tienen que correr antes de que arranque la app.**

En Postgres, `create_all` está deshabilitado a propósito (`app/main.py`): el
esquema lo gobierna Alembic y nada más. Si la app arranca sin migrar, levanta
perfecto y falla en la primera consulta, con un error de tabla inexistente que
parece un bug de código.

Por eso el `Procfile` encadena las dos cosas:

```
web: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
```

El `&&` importa: si la migración falla, el deploy falla en vez de quedar
sirviendo una app rota.

**2. Un solo worker.**

El `--workers 1` no es un descuido. El bus de eventos que alimenta el bracket
y el chat en vivo vive en la memoria del proceso (`app/core/eventos.py`), y lo
mismo los tickets de stream (`app/core/tickets.py`). Con dos workers, un
evento publicado en uno no llega a los clientes conectados al otro: **algunos
usuarios ven el bracket congelado y no aparece ningún error en ningún lado**.

Si en algún momento hace falta escalar, la salida está documentada en
`app/core/eventos.py`: reemplazar el hub por Postgres `LISTEN/NOTIFY`. Ya hay
Postgres, no haría falta Redis.

**3. La raíz del proyecto es `torneos-backend/`, no el repo.**

Es un monorepo con backend y frontend. En Railway hay que configurar el *Root
Directory* en `torneos-backend`, o no va a encontrar ni el `Procfile` ni el
`requirements.txt`.

---

## Variables de entorno

`DATABASE_URL` la inyecta Railway sola. **No hace falta editarla**: llega como
`postgresql://` y la app la normaliza a `postgresql+psycopg://` al leerla (ver
`app/core/config.py`), porque el proyecto usa psycopg 3 y SQLAlchemy si no
buscaría psycopg2, que no está instalado.

Las que sí hay que poner a mano:

| Variable | Valor | Si no la ponés |
|---|---|---|
| `JWT_SECRET` | Generar uno nuevo (≥32 chars) | Cualquiera que lea el repo puede firmar tokens de organizador |
| `DEBUG` | `false` | Queda `/docs` abierto al público |
| `CORS_ORIGINS` | Dominio real del frontend (Vercel), sin `/` al final | El navegador bloquea todas las llamadas |
| `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET` | De la app en Discord Developers | Nadie puede iniciar sesión |
| `DISCORD_REDIRECT_URI` | `https://TU-BACKEND/api/auth/discord/callback` (mismo valor en Discord) | El login Discord falla al volver |
| `DISCORD_IDS_ORGANIZADORES_INICIALES` | Tu Discord ID | **Nadie puede administrar nada**: no hay forma de crear el primer organizador |
| `ALMACENAMIENTO_LOCAL` | `false` | Las evidencias se escriben en disco efímero y se pierden en cada deploy |
| `R2_*` | Credenciales de Cloudflare R2 | Ídem |
| `RUN_SEED` | `true` (al menos en el primer deploy) | El catálogo queda vacío y no se puede crear ningún torneo |

En el frontend (`torneos-web` en Vercel):

| Variable | Valor |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://TU-BACKEND/api` (con `/api` al final) |

Para el secreto:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`DISCORD_IDS_ORGANIZADORES_INICIALES` es el que más se olvida y el más
molesto: sin eso la plataforma queda sin nadie que pueda crear un torneo, y no
hay forma de arreglarlo desde la interfaz. Tu Discord ID sale activando "Modo
desarrollador" en Discord, click derecho en tu perfil, "Copiar ID de usuario".

---

## Después del primer deploy

```bash
curl https://TU-BACKEND/api/health          # {"status":"ok"}
curl https://TU-BACKEND/api/juegos          # tiene que traer solo mlbb
```

Si `/api/juegos` viene vacío, el seed no corrió: revisar `RUN_SEED`.

Si algo responde 500, el lugar donde mirar son los logs del deploy, y lo
primero a descartar es que `alembic upgrade head` haya fallado.

---

## El frontend va aparte

`torneos-web/` es una app Next y se despliega por su cuenta (Vercel es lo
natural). Necesita `NEXT_PUBLIC_API_URL` apuntando al backend, y ese dominio
tiene que estar en `CORS_ORIGINS` del backend. Son dos pasos que dependen uno
del otro: conviene desplegar el backend primero, anotar su URL, y recién ahí
el frontend.

---

## Qué NO llevar a producción

La base de desarrollo tiene datos sembrados de prueba: 52 equipos con nombres
repetidos ("Alpha Wolves" aparece tres veces), torneos de prueba y usuarios
demo. **Producción arranca vacía.** El seed crea el catálogo de juegos y nada
más; los torneos se crean desde la interfaz.
