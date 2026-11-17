# Documento técnico — Tercer corte (máx. 10 páginas)

## 1. Resumen
Aplicativo empresarial de gestión documental y tickets (FastAPI). En el tercer corte n8n/Make se reemplazó por un motor de
automatización propio (Ruta A) y se añadió un módulo de visión que lee facturas/recibos y capturas de error. Todas las
herramientas son gratuitas: Gemini/Groq (nivel gratuito), Ollama (local), Tesseract, LangChain/LangGraph, APScheduler, SQLite/PostgreSQL, Render.

## 2. Arquitectura final
Ver `ARQUITECTURA.md` (diagrama). Capas: web/API → motor (`automation_engine`) → flujos (`automation_flows`) → IA (`llm_chains`, `chatbot_graph`, `ai_provider`) → visión (`vision_service`) → datos y auditoría.

## 3. Flujos migrados
Ocho flujos (tabla completa en `INVENTARIO_FLUJOS.md`): radicación de tickets, procesamiento de lote, respuesta a réplicas, visión de documentos,
proceso de negocio de la visión, monitor de SLA, cola de reintento de IA y resumen diario. Cada ejecución queda en `tbl_ejecucion_automatizacion`
con fecha, entrada, resultado, duración, reintentos y estado (EXITOSO / PLAN_B / FALLIDO). Los errores no reintentables (`ValueError`, `PermissionError`) se registran sin reintento.

## 4. Módulo de visión
- **Proceso atendido**: lectura de facturas y recibos (proveedor, NIT, número, fecha, total) y capturas de error de los tickets.
- **Captura**: web, celular (cámara) y chatbot.
- **Procesamiento**: pypdf/Tesseract → extractor de reglas → (si hay consentimiento) modelo multimodal Gemini o Ollama; validaciones deterministas (dígito de verificación DIAN, montos, fechas).
- **Salida**: JSON con confianza por campo y global. Umbral 0.75: por debajo, `PENDIENTE_REVISION` y confirmación humana. Estados: CONFIRMADO, RECHAZADO, COLA_REINTENTO.
- **Decisión de la IA y errores**: la IA propone los campos; si se equivoca con baja confianza el humano corrige; si se equivoca con alta confianza, el gasto puede corregirse/anularse y queda auditado. Duplicados se detectan por NIT + número + monto.
- **Integración**: la confirmación dispara `proceso_negocio_vision` (crea `Gasto` o sube la prioridad del ticket); el chatbot acepta imágenes y usa el mismo pipeline.

## 5. Pruebas
- 60 pruebas automáticas (`pytest`), ver `PLAN_PRUEBAS_VISION.md`.
- Benchmark con ≥ 20 fotos reales: **[pendiente — pegar aquí la tabla de `benchmark/resultados_*.md`]**.

## 6. Seguridad y protección de datos
Roles Agente/Administrador, PBKDF2, cookies firmadas, claves en variables de entorno, archivos con control de acceso, auditoría de acciones de la IA,
consentimiento para envío externo, anonimización, documentos de identidad solo en local. Detalle en `PROTECCION_DATOS_LEY1581.md`.

## 7. Plan B y control de costos
Cadena Gemini → Groq → Ollama → reglas locales; cuota 429 pasa al siguiente proveedor; sin modelo ni OCR el documento va a revisión humana; la cola de reintento reprocesa más tarde.

## 8. Despliegue
Docker/Render (plan gratuito). URL y credenciales de prueba: **[completar tras desplegar]**. Comandos en el README.

## 9. Limitaciones conocidas
- Sin Tesseract/Ollama instalados, la lectura de imágenes depende del modelo externo con consentimiento.
- Un solo worker (APScheduler en proceso); SQLite en Render gratuito no es persistente (usar PostgreSQL de Supabase/Neon).
- La precisión real depende de la calidad de las fotos; resultados medidos pendientes de adjuntar.
- No hay portal de autoservicio para derechos del titular ni política de retención automática.
- No hay migraciones de esquema para tablas existentes.
