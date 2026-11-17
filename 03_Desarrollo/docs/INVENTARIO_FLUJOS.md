# Inventario de flujos (especificación del Componente 1)

Ruta elegida: **Ruta A, código propio** (FastAPI + APScheduler). Ningún flujo depende de n8n/Make. La fuente de verdad
es el registro `FLUJOS` en `app/automation_flows.py`, publicado en `GET /api/v1/automatizaciones/flujos` y visible en
`/automatizacion/flujos`. Cada flujo se ejecuta con `automation_engine` (reintentos con backoff exponencial, estados
`EXITOSO` / `PLAN_B` / `FALLIDO`, y registro en `tbl_ejecucion_automatizacion` con fecha, entrada y resultado).

| # | Flujo (id) | Disparador | Pasos | Servicios externos | Resultado | Origen (n8n/Make) |
|---|---|---|---|---|---|---|
| 1 | `radicacion_tickets` | `POST /api/v1/tickets/` o formulario `/crear-solicitud` | Crear/actualizar cliente con autorización → clasificar prioridad/categoría (LLM o reglas) → calcular SLA → respuesta inicial | Gemini/Groq/Ollama (opcional) | Ticket con SLA y trazabilidad | Webhook → IA → crear ticket |
| 2 | `procesamiento_lote` | Subida de lote (hasta 35 archivos) | Validar → guardar → iterar y clasificar por formato → extraer texto → agregar y resumir (anonimizado) → actualizar ticket | LLM opcional, sistema de archivos | Síntesis del lote y mensaje en el ticket | Iterador → clasificador → agregador |
| 3 | `respuesta_replica` | `POST /mis-tickets/{codigo}/replicar` | Registrar mensaje → respuesta contextual → reabrir si estaba cerrado | BD | Mensaje IA en el hilo | Webhook réplica → respuesta IA |
| 4 | `vision_documento` | `POST /api/v1/vision/procesar` (web, celular o chatbot) | Validar firma y tamaño → guardar con control de acceso → OCR local → enrutar por privacidad → extraer → confianza por campo | Gemini visión / Ollama / Tesseract | JSON con confianza y estado | (nuevo, Corte 3) |
| 5 | `proceso_negocio_vision` | Documento `CONFIRMADO` (auto o humano) | Leer campos → factura/recibo: detectar duplicado y crear `Gasto`; captura de error: subir prioridad a Alta | BD | Registro en `tbl_gasto` / ticket priorizado | Nodo final: crear registro |
| 6 | `monitor_sla` | Cron cada `SLA_CHECK_MINUTES` | Buscar tickets sin respuesta → escalar → alertar sin duplicar | BD | Tickets escalados | Schedule trigger |
| 7 | `cola_reintento_ia` | Cron cada `RETRY_QUEUE_MINUTES` | Buscar documentos en `COLA_REINTENTO` → reprocesar → actualizar | Gemini/Ollama | Documentos recuperados | Error workflow → reintento |
| 8 | `resumen_diario` | Cron diario 23:55 (America/Bogotá) | Contar ejecuciones, fallos, Plan B y pendientes de revisión | BD | Instantánea en el log | Schedule trigger → métricas |

## Cómo se probó cada flujo
- Motor: éxito, reintentos, fallo definitivo, errores no reintentables (`ValueError`/`PermissionError`) y Plan B (`test_suite.py`).
- Flujos cron: se ejecutan manualmente con `POST /api/v1/automatizaciones/flujos/{id}/ejecutar` (solo administrador) y se verifica el log.
- Visión → proceso de negocio: confirmación crea `Gasto`, duplicado detectado, rechazo, baja confianza → revisión humana.
- Ejecutar: `python -m pytest test_suite.py -q`.
