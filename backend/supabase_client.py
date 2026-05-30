"""Cliente Supabase singleton para el backend de MisFacturas.

Usa service_role key (acceso completo, bypass RLS).
Solo para uso server-side — nunca exponer esta key al frontend.
"""

import os

from dotenv import load_dotenv
from supabase import Client, create_client

# El .env principal está en la raíz del proyecto (un nivel arriba de backend/)
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
load_dotenv(_env_path)

supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"],
)
