"""Utilidades compartidas por los scripts de prueba: emitir tokens sin pasar
por Discord de verdad (ver app/core/security_dev.py — solo desarrollo).
"""

from app.core.security_dev import token_de_prueba


def headers_organizador(db, discord_id: str = "org-test-001") -> dict:
    """El 'organizador' de los scripts de prueba representa al fundador:
    tiene tanto es_organizador como puede_gestionar_organizadores. Para
    probar un organizador SIN ese segundo permiso (el caso normal de
    alguien recién promovido), usar headers_organizador_limitado.
    """
    token = token_de_prueba(
        db,
        discord_id=discord_id,
        es_organizador=True,
        puede_gestionar_organizadores=True,
        username="Organizador",
    )
    return {"Authorization": f"Bearer {token}"}


def headers_organizador_limitado(db, discord_id: str) -> dict:
    """Un organizador promovido normal — puede operar el torneo pero NO
    tocar la lista de quién más es organizador."""
    token = token_de_prueba(
        db,
        discord_id=discord_id,
        es_organizador=True,
        puede_gestionar_organizadores=False,
        username=f"organizador_{discord_id}",
    )
    return {"Authorization": f"Bearer {token}"}


def headers_capitan(db, discord_id: str) -> dict:
    token = token_de_prueba(
        db, discord_id=discord_id, es_organizador=False, username=f"capitan_{discord_id}"
    )
    return {"Authorization": f"Bearer {token}"}
