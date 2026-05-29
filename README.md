# MisFacturas

Aplicación web full-stack para gestionar facturas del hogar en Argentina. Proyecto portfolio de ingeniería informática.

## Funcionalidades

- 📄 **CRUD completo de facturas** con categorías, montos y fechas de vencimiento
- 🔍 **Deduplicación automática** — detecta facturas repetidas por nombre + monto + fecha (HTTP 409)
- 🤖 **Escaneo con IA** (Groq) — cargá una imagen o PDF y se completan los campos automáticamente
- 📊 **Dashboard** con estadísticas del mes, progreso de pago y alertas de vencimiento
- 📈 **Historial** con gráfico de barras de los últimos 6 meses
- 📱 **Notificaciones Telegram** — aviso automático diario para facturas que vencen en los próximos 3 días
- 📂 **Google Drive auto-detección** — subís una factura a Drive y se registra sola
- 🔗 **Webhooks salientes** — integrá con n8n, Make o cualquier endpoint HTTP
- 💾 **Exportar / importar** datos como JSON
- 🌙 Diseño oscuro mobile-first sin frameworks de UI

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | Vue 3 + Vite + Pinia + Vue Router + Axios |
| Charts | Chart.js (CDN) |
| Estilos | CSS custom con variables — sin frameworks |
| Backend | FastAPI (Python 3.11) |
| IA | Groq API — `meta-llama/llama-4-scout-17b-16e-instruct` |
| Scheduler | APScheduler 3.x (AsyncIOScheduler) |
| Telegram | python-telegram-bot v20+ |
| Google Drive | google-api-python-client + OAuth 2.0 |
| HTTP async | httpx |
| Persistencia | JSON files + filelock (sin base de datos) |
| Testing | pytest + pytest-asyncio · Vitest + @vue/test-utils · Playwright |
| Infra | Docker Hub + Watchtower + Nginx + Let's Encrypt |

---

## Desarrollo local

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env    # completar al menos GROQ_API_KEY
mkdir -p ../data
uvicorn main:app --reload --port 8000
```

El archivo `.env` local debe apuntar los paths a `../data/`:
```
DATA_FILE=../data/bills.json
NOTIFICATIONS_LOG=../data/notifications_log.json
DRIVE_CONFIG=../data/drive_config.json
WEBHOOK_LOG=../data/webhook_log.json
```

Verificar: `curl http://localhost:8000/api/health`

### Frontend

```bash
cd frontend
npm install
npm run dev    # corre en localhost:5173, proxy /api → localhost:8000
```

Abrir `http://localhost:5173`

---

## Docker Hub + Watchtower

`deploy.sh` construye las imágenes en **linux/amd64** y las sube a Docker Hub.
Watchtower corre en el VPS y detecta nuevas imágenes cada 5 minutos, reiniciando los contenedores automáticamente.

```bash
# Primera vez o cuando querés publicar cambios:
./deploy.sh fabribiondi2002

# Con tag de versión:
./deploy.sh fabribiondi2002 v1.0.0
```

Después del push, el VPS actualiza solo en ≤ 5 minutos. No se necesita SSH para deploys de rutina.

---

## Despliegue en VPS (primera vez)

1. **Buildear y subir imágenes:** `./deploy.sh fabribiondi2002`
2. **Agregar dominio en DuckDNS** apuntando a la IP del VPS
3. **Agregar el dominio a Nginx HTTP** para el challenge ACME:
   ```bash
   # En ~/infra/nginx/conf.d/http.conf agregar el dominio al server_name
   docker exec nginx nginx -s reload
   ```
4. **Obtener certificado SSL:**
   ```bash
   docker compose -f ~/infra/docker-compose.yml run --rm certbot certonly \
     --webroot -w /var/www/certbot \
     -d misfacturas-fabriziobiondi.duckdns.org
   ```
5. **Copiar config de Nginx:**
   ```bash
   cp docs/nginx/misfacturas.conf ~/infra/nginx/conf.d/
   docker exec nginx nginx -s reload
   ```
6. **Crear directorio y configurar app:**
   ```bash
   mkdir ~/infra/misfacturas && cd ~/infra/misfacturas
   # Copiar docker-compose.yml y crear .env desde .env.example
   # Completar al mínimo: GROQ_API_KEY, APP_BASE_URL
   docker compose up -d
   ```
7. **Verificar:**
   ```bash
   curl https://misfacturas-fabriziobiondi.duckdns.org/api/health
   ```

---

## Groq API

Usada para escanear facturas con visión artificial (imágenes JPEG/PNG y PDFs).

1. Registrarse en [console.groq.com](https://console.groq.com) (tier gratuito disponible)
2. Crear una API key
3. Agregar `GROQ_API_KEY=<tu_clave>` al `.env`

**Modelo actual:** `meta-llama/llama-4-scout-17b-16e-instruct`
- 128K tokens de contexto, hasta 5 imágenes por request
- Los PDFs se convierten a JPEG en el backend con `pdf2image` (requiere poppler-utils)
- El prompt fuerza interpretación de fechas como DD/MM/YYYY (formato argentino)

> Los modelos `llama-3.2-11b-vision-preview` y `llama-3.2-90b-vision-preview` están deprecados desde abril 2025.

---

## Telegram — Configuración de notificaciones

La configuración es exclusivamente por variables de entorno. No hay UI para esto.

1. Buscá **@BotFather** en Telegram → `/newbot` → copiá el token → `TELEGRAM_BOT_TOKEN`
2. Buscá **@userinfobot** en Telegram → `/start` → copiá tu id numérico → `TELEGRAM_CHAT_ID`
3. Agregá ambos al `.env` en el VPS y reiniciá: `docker compose restart misfacturas-backend`
4. Verificar desde curl: `curl -X POST https://<dominio>/api/notifications/test`

Las notificaciones se envían diariamente a la hora configurada en `NOTIFY_HOUR` (default: 9 hs ART)
para facturas que vencen en los próximos 0–3 días. Se deduplicación por `notifications_log.json`.

El dashboard muestra un chip **"Telegram ✓"** cuando las credenciales están configuradas.

---

## Google Drive — Configuración

> ⚠️ La URL del webhook de Drive debe ser HTTPS pública. No funciona en localhost.

La configuración se hace una sola vez:

1. Ir a [console.cloud.google.com](https://console.cloud.google.com) → Nuevo proyecto
2. Habilitar **Google Drive API**
3. Credentials → **OAuth 2.0 Client ID** → Web application
4. Agregar como URI autorizada: `https://misfacturas-fabriziobiondi.duckdns.org/api/drive/oauth/callback`
5. Copiar `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` al `.env` del VPS
6. Abrir en el browser: `https://<dominio>/api/drive/oauth/callback` → completar el flujo OAuth
   (el token de refresco queda guardado en `/data/drive_config.json`)
7. Copiar el ID de la carpeta de Drive (visible en la URL al abrirla) y agregar al `.env`:
   ```
   DRIVE_FOLDER_ID=<id-de-tu-carpeta>
   ```
8. Reiniciar el backend: `docker compose restart misfacturas-backend`
   → el canal push se configura automáticamente al arrancar

A partir de ese momento, cualquier archivo JPEG, PNG o PDF que subas a la carpeta vigilada
se escanea con IA y se agrega automáticamente a MisFacturas.

El dashboard muestra un chip **"Drive ✓"** cuando Drive está conectado y la carpeta configurada.

**Renovación automática:** el canal push expira cada 7 días. APScheduler lo renueva cada 6 días sin intervención.

---

## Webhooks salientes

La configuración es exclusivamente por variables de entorno:

```
WEBHOOK_URL=https://tu-endpoint.com/hook
WEBHOOK_SECRET=tu-secreto-hmac   # opcional
```

Reiniciar el backend después de cambiar estas variables.

| Evento | Cuándo |
|--------|--------|
| `bill.created` | Se crea una factura |
| `bill.paid` | Se marca como pagada |
| `bill.due_today` | Vence hoy (job diario) |
| `bill.auto_detected` | Drive detecta una factura |
| `bill.scan_failed` | Drive sube un archivo no reconocido |
| `webhook.test` | Llamada al endpoint de prueba |

Si `WEBHOOK_SECRET` está configurado, cada petición incluye `X-Signature: sha256=<firma>`.

**Verificar:** `curl -X POST https://<dominio>/api/webhooks/test`

**Integración con n8n:** Creá un trigger "Webhook" en n8n y copiá la URL a `WEBHOOK_URL`.

---

## Exportar / Importar datos

Desde **Ajustes → Datos**:

- **Exportar:** descarga `bills.json` con todas las facturas
- **Importar:** sube un `bills.json` exportado previamente → reemplaza los datos actuales (con confirmación)

---

## Testing

### Backend (pytest)

```bash
cd backend
source venv/bin/activate
pytest -v
```

59 tests que cubren: CRUD completo, deduplicación, storage concurrente, notificaciones Telegram,
webhooks salientes, Drive webhook states, escaneo Groq.

### Frontend — tests unitarios (Vitest)

```bash
cd frontend
npm run test:unit
```

35 tests de componentes y store: BillRow (badges, formato, eventos), StatCard, ProgressBar,
CategoryPicker, MonthNav, store Pinia (getters + acciones).

### Frontend — tests E2E (Playwright)

Requiere la app corriendo (backend + frontend):

```bash
# Terminal 1
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev

# Terminal 3
cd frontend && npm run test:e2e
```

Contra el VPS desplegado:
```bash
PLAYWRIGHT_BASE_URL=https://misfacturas-fabriziobiondi.duckdns.org npm run test:e2e
```

Ver reporte HTML después de correr:
```bash
npm run test:e2e:report
```

Los tests E2E cubren: dashboard, CRUD de facturas, formulario de alta/edición, historial,
y responsividad en 5 viewports (375px → 1920px).

---

## Variables de entorno

| Variable | Requerida | Descripción | Default |
|----------|-----------|-------------|---------|
| `GROQ_API_KEY` | ✅ | Clave de API de Groq (console.groq.com) | — |
| `TELEGRAM_BOT_TOKEN` | ❌ | Token del bot de Telegram (@BotFather) | — |
| `TELEGRAM_CHAT_ID` | ❌ | ID numérico del chat (@userinfobot) | — |
| `NOTIFY_HOUR` | ❌ | Hora de notificaciones diarias (0–23) | `9` |
| `GOOGLE_CLIENT_ID` | ❌ | OAuth Client ID de Google Cloud | — |
| `GOOGLE_CLIENT_SECRET` | ❌ | OAuth Client Secret de Google Cloud | — |
| `GOOGLE_REDIRECT_URI` | ❌ | URI de redirección OAuth | `APP_BASE_URL/api/drive/oauth/callback` |
| `DRIVE_FOLDER_ID` | ❌ | ID de carpeta de Drive a vigilar — auto-configura canal al arrancar | — |
| `WEBHOOK_URL` | ❌ | URL para webhooks salientes (n8n, Make, etc.) | — |
| `WEBHOOK_SECRET` | ❌ | Secreto HMAC para firmar peticiones | — |
| `APP_BASE_URL` | ❌ | URL pública HTTPS (requerida para Drive webhooks) | — |
| `FRONTEND_URL` | ❌ | URL del frontend para CORS | `http://localhost:5173` |
| `DATA_FILE` | ❌ | Ruta a bills.json | `/data/bills.json` |
| `NOTIFICATIONS_LOG` | ❌ | Ruta a notifications_log.json | `/data/notifications_log.json` |
| `DRIVE_CONFIG` | ❌ | Ruta a drive_config.json | `/data/drive_config.json` |
| `WEBHOOK_LOG` | ❌ | Ruta a webhook_log.json | `/data/webhook_log.json` |
| `TZ` | ❌ | Zona horaria del contenedor | `America/Argentina/Buenos_Aires` |
| `VITE_API_BASE_URL` | ❌ | Base URL de la API (frontend) | `/api` |

---

## Referencia de endpoints API

| Método | Path | Descripción |
|--------|------|-------------|
| `GET` | `/api/health` | Estado del servicio |
| `GET` | `/api/bills?month=YYYY-MM` | Listar facturas del mes, ordenadas por dueDate |
| `POST` | `/api/bills` | Crear factura — retorna 409 si es duplicada |
| `POST` | `/api/bills/import` | Importar bills.json, reemplaza datos actuales |
| `PUT` | `/api/bills/{id}` | Actualizar factura |
| `DELETE` | `/api/bills/{id}` | Eliminar factura |
| `PATCH` | `/api/bills/{id}/toggle-paid` | Alternar estado de pago |
| `GET` | `/api/summary?months=6` | Resumen histórico por mes |
| `POST` | `/api/scan-invoice` | Escanear factura con IA (JPEG/PNG/PDF) |
| `GET` | `/api/notifications/config` | Estado de configuración de Telegram |
| `POST` | `/api/notifications/test` | Enviar mensaje de prueba por Telegram |
| `GET` | `/api/drive/oauth/callback` | Callback OAuth de Google Drive |
| `GET` | `/api/drive/status` | Estado de la integración Drive |
| `POST` | `/api/drive/set-folder` | Configurar carpeta vigilada (interno) |
| `POST` | `/api/drive/disconnect` | Desconectar Drive |
| `POST` | `/api/drive/webhook` | Receptor push de Google Drive (Google llama este endpoint) |
| `GET` | `/api/webhooks/config` | Estado de configuración de webhooks |
| `POST` | `/api/webhooks/test` | Disparar webhook de prueba |
| `GET` | `/api/webhooks/log` | Últimas 10 entradas del log de webhooks |

---

Ver [PLAN.md](PLAN.md) para el historial detallado de desarrollo y estado de cada tarea.
