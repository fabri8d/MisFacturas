"""Middleware de autenticación JWT para MisFacturas v2.

Verifica tokens emitidos por Supabase Auth usando el cliente con service_role.
Todas las rutas protegidas usan Depends(get_current_user).
"""

from fastapi import Header, HTTPException

from supabase_client import supabase


async def get_current_user(authorization: str = Header(...)) -> dict:
    """Extrae y verifica el JWT de Supabase del header Authorization.

    Retorna dict con id y email del usuario autenticado.
    Lanza HTTPException 401 si el token es inválido o falta.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")
    token = authorization[7:].strip()
    try:
        resp = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")
    if not resp.user:
        raise HTTPException(status_code=401, detail="Token inválido")
    return {
        "id": resp.user.id,
        "email": resp.user.email,
        "user_metadata": resp.user.user_metadata or {},
    }
