"""Crea (o resetea la contraseña de) las dos cuentas de arranque pedidas
para probar el panel de admin sin depender de Discord OAuth:
  - una cuenta organizadora (admin)
  - una cuenta cliente normal (jugador)

Ejecutar: python sembrar_cuentas_demo.py
"""

from app.core.security import hash_password
from app.db.database import SessionLocal
from app.models import Usuario

CUENTAS = [
    {
        "email": "admin@arenaesports.local",
        "password": "Admin12345",
        "nombre": "Admin Arena",
        "es_organizador": True,
        "puede_gestionar_organizadores": True,
    },
    {
        "email": "cliente@arenaesports.local",
        "password": "Cliente12345",
        "nombre": "Cliente Demo",
        "es_organizador": False,
        "puede_gestionar_organizadores": False,
    },
]

db = SessionLocal()
try:
    for c in CUENTAS:
        usuario = db.query(Usuario).filter(Usuario.email == c["email"]).first()
        if usuario:
            usuario.password_hash = hash_password(c["password"])
            usuario.es_organizador = c["es_organizador"]
            usuario.puede_gestionar_organizadores = c["puede_gestionar_organizadores"]
            print(f"Actualizada: {c['email']}")
        else:
            usuario = Usuario(
                discord_id=f"local:{c['email']}",
                discord_username=c["nombre"],
                email=c["email"],
                password_hash=hash_password(c["password"]),
                es_organizador=c["es_organizador"],
                puede_gestionar_organizadores=c["puede_gestionar_organizadores"],
            )
            db.add(usuario)
            print(f"Creada: {c['email']}")
    db.commit()
finally:
    db.close()

print("\nListo. Credenciales:")
for c in CUENTAS:
    rol = "organizador" if c["es_organizador"] else "cliente"
    print(f"  [{rol}] {c['email']} / {c['password']}")
