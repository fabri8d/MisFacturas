-- MisFacturas v2 — Esquema inicial de Supabase PostgreSQL
-- Ejecutar en: Supabase Dashboard → SQL Editor

-- ─── Tabla de perfiles de usuario ──────────────────────────────────────────────

CREATE TABLE public.profiles (
  id            UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email         TEXT NOT NULL,
  full_name     TEXT,
  avatar_url    TEXT,
  drive_access_token   TEXT,
  drive_refresh_token  TEXT,
  drive_token_expiry   TIMESTAMPTZ,
  drive_account_email  TEXT,
  drive_folder_id      TEXT,
  drive_folder_name    TEXT,
  drive_channel_id     TEXT,
  drive_channel_expiry TIMESTAMPTZ,
  drive_resource_id    TEXT,
  notifications_enabled BOOLEAN DEFAULT true,
  telegram_chat_id      TEXT,
  webhook_url    TEXT,
  webhook_secret TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Tabla de facturas ──────────────────────────────────────────────────────────

CREATE TABLE public.bills (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  category    TEXT NOT NULL CHECK (category IN (
                'electricidad','gas','agua','internet','telefono',
                'alquiler','expensas','seguro','streaming','otro')),
  amount      NUMERIC(12,2) NOT NULL CHECK (amount > 0),
  due_date    DATE NOT NULL,
  month       TEXT NOT NULL,
  is_paid     BOOLEAN DEFAULT false,
  paid_date   DATE,
  notes       TEXT,
  source      TEXT DEFAULT 'manual' CHECK (source IN ('manual','drive')),
  drive_file_id TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Tabla de log de webhooks salientes ─────────────────────────────────────────

CREATE TABLE public.webhook_logs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  event       TEXT NOT NULL,
  status_code INTEGER,
  error       TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Tabla de log de notificaciones ─────────────────────────────────────────────

CREATE TABLE public.notification_logs (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  bill_id    UUID REFERENCES public.bills(id) ON DELETE CASCADE,
  notified_at DATE NOT NULL,
  UNIQUE(bill_id, notified_at)
);

-- ─── Row Level Security ──────────────────────────────────────────────────────────

ALTER TABLE public.profiles          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bills             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.webhook_logs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notification_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_own_profile" ON public.profiles
  FOR ALL USING (auth.uid() = id);

CREATE POLICY "users_own_bills" ON public.bills
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "users_own_webhook_logs" ON public.webhook_logs
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "users_own_notification_logs" ON public.notification_logs
  FOR ALL USING (auth.uid() = user_id);

-- ─── Trigger: crear perfil al registrarse ───────────────────────────────────────

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ─── Índices ─────────────────────────────────────────────────────────────────────

CREATE INDEX bills_user_month       ON public.bills (user_id, month);
CREATE INDEX bills_due_date         ON public.bills (due_date) WHERE is_paid = false;
CREATE INDEX webhook_logs_user      ON public.webhook_logs (user_id, created_at DESC);
CREATE INDEX notification_logs_bill ON public.notification_logs (bill_id, notified_at);