-- MisFacturas v2 — Migración 002: Organización Drive + Comprobantes de pago
-- Fecha: 2026-05-30
-- Descripción: Agrega sistema de comprobantes de pago usando Google Drive
--   como storage (no Supabase Storage), y columnas de tracking Drive en bills.
--
-- Ejecutar en: Supabase Dashboard → SQL Editor

-- ─── Tabla de comprobantes ────────────────────────────────────────────────────
-- Los archivos viven en Google Drive del usuario, no en Supabase Storage.
-- Esta tabla solo guarda metadatos y los IDs de Drive para referenciarlos.

CREATE TABLE public.receipts (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  bill_id               UUID NOT NULL REFERENCES public.bills(id) ON DELETE CASCADE,
  drive_file_id         TEXT NOT NULL,        -- ID del archivo en Google Drive
  drive_folder_id       TEXT NOT NULL,        -- ID de la carpeta Comprobantes/mes en Drive
  file_name             TEXT NOT NULL,        -- nombre original del archivo (para mostrar)
  file_size             INTEGER,              -- bytes
  mime_type             TEXT,
  drive_web_view_link   TEXT,                 -- URL para ver en Drive (no expira)
  drive_web_content_link TEXT,               -- URL de descarga directa
  uploaded_at           TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Row Level Security ───────────────────────────────────────────────────────

ALTER TABLE public.receipts ENABLE ROW LEVEL SECURITY;

-- El backend usa service_role (bypass RLS). Esta policy protege
-- el acceso directo desde el cliente Supabase con anon/user key.
CREATE POLICY "users_own_receipts" ON public.receipts
  FOR ALL USING (auth.uid() = user_id);

-- ─── Columnas nuevas en bills ─────────────────────────────────────────────────
-- Trackean el archivo de factura en Drive para poder moverlo al cambiar la fecha.

ALTER TABLE public.bills
  ADD COLUMN IF NOT EXISTS drive_file_id       TEXT,      -- ID del archivo en Drive
  ADD COLUMN IF NOT EXISTS drive_folder_id     TEXT,      -- ID carpeta Facturas/mes en Drive
  ADD COLUMN IF NOT EXISTS drive_web_view_link TEXT;      -- URL para ver la factura en Drive

-- ─── Índices ──────────────────────────────────────────────────────────────────

CREATE INDEX receipts_bill_id ON public.receipts (bill_id);
CREATE INDEX receipts_user_id ON public.receipts (user_id, uploaded_at DESC);
