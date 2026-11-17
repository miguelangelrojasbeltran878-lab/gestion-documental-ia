# Arquitectura

```mermaid
flowchart LR
  U[Usuario web / celular] --> API[FastAPI app.main]
  CB[Chatbot LangGraph] --> API
  API --> AUTH[Auth PBKDF2 + roles + cookie firmada]
  API --> VIS[vision_service: OCR Tesseract + extractor de reglas + validaciones NIT/monto/fecha]
  VIS --> PRIV[privacy: consentimiento, anonimización, docs de identidad solo local]
  PRIV --> PROV[ai_provider: Gemini -> Groq -> Ollama -> reglas locales Plan B]
  VIS --> ENG[automation_engine: reintentos, log, Plan B]
  ENG --> FL[automation_flows: 8 flujos]
  SCH[APScheduler cron] --> ENG
  FL --> DB[(SQLite / PostgreSQL)]
  VIS --> FS[(storage/vision con control de acceso)]
  API --> AUD[(AuditoriaIA)]
```

## Capas
- **Presentación**: plantillas Jinja2 + Bootstrap (`/vision`, `/automatizacion/flujos`, tickets, dashboard).
- **API**: FastAPI con sesión por cookie `HttpOnly`/`SameSite`, roles Agente y Administrador.
- **Motor de automatización**: `automation_engine.py` (ejecución, reintentos con backoff, estados, logs), `automation_flows.py` (registro `FLUJOS`), `scheduler.py` (APScheduler, zona America/Bogotá, un solo worker).
- **IA**: `llm_chains.py` (LangChain: prompt | modelo | parser con fallbacks), `chatbot_graph.py` (LangGraph, nodos recuperar → responder, memoria por usuario con `MemorySaver`), `ai_provider.py` (cadena de proveedores, cuota 429 → siguiente).
- **Visión**: `vision_service.py`, caso de uso *lectura de facturas/recibos* (+ capturas de error y documentos de identidad).
- **Datos**: SQLAlchemy; tablas nuevas `tbl_gasto` y `tbl_auditoria_ia` creadas con `create_all`.

## Plan B ante fallos del modelo
1. Cuota/falla de Gemini → Groq → Ollama (si `OLLAMA_BASE_URL`) → reglas locales.
2. Visión sin modelo ni OCR → estado `sin_lectura` y revisión humana (nunca se inventan datos).
3. Documento sin proveedor disponible → `COLA_REINTENTO`, reprocesado por el cron.

## Despliegue
`Dockerfile` (Python 3.12 + Tesseract spa) y `render.yaml` (Render, plan gratuito, health check `/health`). Variables en `.env.example`.
