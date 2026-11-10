# Sistema Inteligente de Gestión y Análisis Documental con IA Multimodal
## Guía Tercer Corte — Desarrollo de Aplicaciones Empresariales

Aplicativo web empresarial desarrollado en Python con **FastAPI**, **SQLAlchemy** y **Bootstrap 5.3 + GSAP**, integrado con un **motor de automatización propio en código**, un **módulo de visión por computador e IA multimodal** y un **chatbot documental interactivo**, eliminando la dependencia de plataformas de pago como n8n en la nube.

---

## 1. Características Principales

1. **Componente 1 — Automatización Propia en Código (Ruta A de la Guía):**
   - Reemplazo de flujos n8n externos por servicios modulares desacoplados (`app/automation_engine.py`).
   - Registro persistente de cada ejecución en base de datos (`tbl_ejecucion_automatizacion`) con identificador único (`EXE-...`), proceso, usuario, duración en milisegundos, estado (`EXITOSO`, `FALLIDO`, `PLAN_B`), reintentos automáticos y manejo controlado de excepciones.
   - Proveedor de IA desacoplado con **Google Gemini (nivel gratuito)** y **Plan B automático** mediante reglas heurísticas locales cuando no hay conexión o se agota la cuota.

2. **Componente 2 — Visión por Computador e IA Multimodal:**
   - Procesamiento de imágenes y documentos escaneados (`.jpg`, `.png`, `.pdf`) tomados con cámara de celular o cargados desde la web (`/vision`).
   - Extracción de entidades estructuradas en formato JSON (`document_type`, `emisor_o_proveedor`, `nit`, `fecha`, `monto_total`, `codigo_error`).
   - Cálculo de índice de confianza (`confidence`). Si la confianza es inferior a 0.75, el sistema lo marca automáticamente como **`PENDIENTE_REVISION`** para permitir confirmación, corrección o rechazo humano.
   - Disparo automático del proceso de negocio: vinculación con expediente y reclasificación de prioridad del caso.

3. **Chatbot Documental Interactivo:**
   - Asistente inteligente en tiempo real (`/api/v1/chatbot-archivos-upload`) capaz de leer el contenido interno de lotes de hasta 30 archivos (`.pdf`, `.xlsx`, `.docx`, `.jpg`) y responder preguntas o generar resúmenes ejecutivos claros.

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
- **Comando de inicio:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Variables de entorno:** Configurar según `.env.example`.
- **Almacenamiento persistente:** Para almacenar archivos en planes gratuitos que no ofrecen disco persistente, configurar `UPLOAD_DIR` hacia un volumen montado o almacenamiento compatible S3.
