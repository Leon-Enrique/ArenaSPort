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
