# Sistema Inteligente de Gestión y Análisis Documental con IA Multimodal
## Guía Tercer Corte — Desarrollo de Aplicaciones Empresariales

Aplicativo web empresarial desarrollado en Python con **FastAPI**, **SQLAlchemy** y **Bootstrap 5.3 + GSAP**, integrado con un **motor de automatización propio en código**, un **módulo de visión por computador e IA multimodal** y un **chatbot documental interactivo**, eliminando la dependencia de plataformas de pago como n8n en la nube.

---

## 1. Características Principales

1. **Componente 1 — Automatización Propia en Código (Ruta A de la Guía):**
   - Reemplazo de flujos n8n externos por servicios modulares desacoplados (`app/automation_engine.py`).
   - Registro persistente de cada ejecución en base de datos (`tbl_ejecucion_automatizacion`) con identificador único (`EXE-...`), proceso, usuario, duración en milisegundos, estado (`EXITOSO`, `FALLIDO`, `PLAN_B`), reintentos automáticos y manejo controlado de excepciones.
   - 8 flujos registrados (ver `docs/INVENTARIO_FLUJOS.md`), 3 de ellos programados con APScheduler (SLA, cola de reintento, resumen diario).
   - Cadena de proveedores de IA **Gemini → Groq → Ollama → reglas locales (Plan B)**, orquestada con LangChain; chatbot con LangGraph y memoria por usuario.

2. **Componente 2 — Visión por Computador e IA Multimodal:**
   - Procesamiento de imágenes y documentos escaneados (`.jpg`, `.png`, `.pdf`) tomados con cámara de celular o cargados desde la web (`/vision`).
   - Extracción de entidades estructuradas en formato JSON (`document_type`, `emisor_o_proveedor`, `nit`, `fecha`, `monto_total`, `codigo_error`).
   - Cálculo de índice de confianza (`confidence`). Si la confianza es inferior a 0.75, el sistema lo marca automáticamente como **`PENDIENTE_REVISION`** para permitir confirmación, corrección o rechazo humano.
   - Disparo automático del proceso de negocio: vinculación con expediente y reclasificación de prioridad del caso.

3. **Chatbot Documental Interactivo:**
   - Asistente inteligente en tiempo real (`/api/v1/chatbot/mensaje`, con imágenes y memoria) capaz de leer el contenido interno de lotes de hasta 30 archivos (`.pdf`, `.xlsx`, `.docx`, `.jpg`) y responder preguntas o generar resúmenes ejecutivos claros.

4. **Seguridad y Protección de Datos (Ley 1581 de 2012):**
   - Autenticación segura mediante contraseñas con hash criptográfico **PBKDF2-SHA256** (100.000 iteraciones) y sesiones firmadas con cookies seguras (`HttpOnly`, `SameSite=Lax`).
   - Control de acceso basado en roles (`Agente`, `Administrador`).
   - Trazabilidad y anonimización de datos sensibles en los registros de auditoría.
   - Consentimiento y autorización previa para el tratamiento de datos personales en el registro de clientes.

5. **Dashboard con Métricas 100% Reales:**
   - Tiempos de resolución calculados matemáticamente desde la base de datos SQLite.
   - Satisfacción del cliente basada en calificaciones CSAT de 1 a 5 estrellas.
   - Estadísticas de éxito del motor de automatización y conteo de documentos procesados por visión.

---

## 2. Requisitos Previos

- Python 3.10 o superior (probado en Python 3.14).
- Sistema operativo: Windows, Linux o macOS.
- Navegador web moderno (Chrome, Edge, Firefox).

---

## 3. Instalación y Configuración Local

1. **Clonar o descargar el repositorio:**
   ```bash
   cd 03_Desarrollo
   ```

2. **Crear y activar un entorno virtual (recomendado):**
   ```bash
   python -m venv venv
   # En Windows:
   .\venv\Scripts\activate
   # En Linux/macOS:
   source venv/bin/activate
   ```

3. **Instalar dependencias oficiales:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   Copia el archivo `.env.example` a `.env`:
   ```bash
   copy .env.example .env
   ```
   *(Opcional: Si deseas habilitar el modelo multimodal Gemini de Google en su nivel gratuito, genera una API Key en [Google AI Studio](https://aistudio.google.com/app/apikey) y asígnala en `GEMINI_API_KEY`. Si se deja vacía, el sistema operará automáticamente con el Plan B local).*

5. **Inicializar y poblar la base de datos:**
   ```bash
   python seed_data.py
   ```

6. **Iniciar el servidor web:**
   ```bash
   python run.py
   ```
   La aplicación quedará disponible en: `http://127.0.0.1:8000`

---

## 4. Credenciales de Prueba para la Sustentación

- **Agente de Soporte:**
  - Correo: `andres.gomez@empresa.com`
  - Contraseña: `Password123*`
- **Administrador:**
  - Correo: `miguel.rojas@empresa.com`
  - Contraseña: `Password123*`

---

## 4a. Interfaz y carga de archivos

Interfaz rediseñada (tema claro/oscuro, menú lateral por rol, responsive). Mapa de páginas:

| Ruta | Quién | Para qué |
|---|---|---|
| `/` · `/crear-solicitud` · `/mis-tickets` | Público | Radicar solicitud con adjuntos y consultar el ticket por código |
| `/login` | Equipo | Acceso (redirige a la página que se pidió) |
| `/agente/tickets` · `/agente/tickets/{id}` | Agente/Admin | Bandeja, respuesta oficial, archivos del ticket |
| `/vision` | Agente/Admin | Foto o PDF de factura/recibo → campos con confianza → revisión humana → gasto |
| `/chatbot` | Agente/Admin | Asistente con memoria; acepta imagen adjunta |
| `/automatizacion/flujos` | Agente/Admin | Inventario, registro y ejecución manual (Admin) de flujos |
| `/admin/dashboard` · `/admin/reportes` · `/admin/clientes` · `/admin/auditoria` | Admin | Métricas, reporte mensual con CSV, clientes (Ley 1581), bitácora y gastos |

**Carga de archivos:** clic, arrastrar y soltar o pegar (Ctrl+V). Formatos: `pdf, xlsx, docx, txt, csv, jpg, jpeg, png, webp`; hasta 15 MB por archivo y 35 por solicitud. Los formatos no admitidos se rechazan con un aviso claro.

**Lectura de documentos sin clave de IA:** sin `GEMINI_API_KEY` (gratuita) ni OCR local, la visión no puede leer el texto; el documento queda en revisión humana y el revisor completa los campos y elige el tipo (factura, recibo…). Con una clave gratuita de Gemini la extracción es automática.

**Sesión:** si no defines `SECRET_KEY`, se genera una vez en `.secret_key` (ignorado por git) para que reiniciar el servidor no cierre las sesiones.

## 4b. Documentación
`docs/`: INVENTARIO_FLUJOS, ARQUITECTURA, PROTECCION_DATOS_LEY1581, PLAN_PRUEBAS_VISION, DOCUMENTO_TECNICO, GUION_VIDEO y MATRIZ_CUMPLIMIENTO_GUIA.
Benchmark de visión con fotos reales: `benchmark/README.md`.

## 5. Ejecución de Pruebas Automatizadas

El proyecto incluye una suite de pruebas unitarias y de integración construida con `pytest`:

```bash
python -m pytest test_suite.py -v
```

Verifica:
- Carga de interfaces web principales.
- Seguridad de login y rechazo de credenciales incorrectas.
- Algoritmo de hashing criptográfico PBKDF2.
- Extracción estructurada del módulo de visión por computador.
- Auditoría en base de datos del motor de automatización.
- Cálculo de métricas reales del dashboard administrativo.

---

## 6. Despliegue en Producción

El aplicativo está preparado para desplegarse en plataformas PaaS gratuitas como **Render** o **Railway**:
- **Comando de inicio:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (o Docker con el `Dockerfile` y `render.yaml`, que instalan Tesseract). Usar `DATABASE_URL` de PostgreSQL (Supabase/Neon) para persistencia y definir `SECRET_KEY`, `ADMIN_PASSWORD`, `COOKIE_SECURE=true`.
- **Variables de entorno:** Configurar según `.env.example`.
- **Almacenamiento persistente:** Para almacenar archivos en planes gratuitos que no ofrecen disco persistente, configurar `UPLOAD_DIR` hacia un volumen montado o almacenamiento compatible S3.
