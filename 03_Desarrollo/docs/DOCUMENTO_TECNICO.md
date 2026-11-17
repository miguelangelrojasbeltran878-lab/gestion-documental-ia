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
- Benchmark (`python -m benchmark.run_benchmark --consentimiento`, Gemini `gemini-3.5-flash-lite`), 18 facturas fotografiadas sobre mesa; verdad de terreno diligenciada a mano:

| Campo | Precisión |
|---|---|
| Emisor / proveedor | 100 % |
| NIT | 94,4 % |
| Número de documento | 100 % |
| Fecha de emisión | 100 % |
| Monto total | 100 % |

  Documentos con todos los campos correctos: 94,4 %. Tipo de documento: 100 %. Precisión de los auto-confirmados: 100 %. Enviados a revisión humana: 77,8 %. Latencia media: 7,3 s. El único error (NIT de `foto_15`, tomada inclinada) quedó en revisión humana y no se confirmó automáticamente. Se necesitan 2 imágenes más para llegar al mínimo de 20 de la guía.

## 6. Seguridad y protección de datos
Roles Agente/Administrador, PBKDF2, cookies firmadas, claves en variables de entorno, archivos con control de acceso, auditoría de acciones de la IA,
consentimiento para envío externo, anonimización, documentos de identidad solo en local. Detalle en `PROTECCION_DATOS_LEY1581.md`.

## 7. Plan B y control de costos
Cadena Gemini → Groq → Ollama → reglas locales; cuota 429 pasa al siguiente proveedor; sin modelo ni OCR el documento va a revisión humana; la cola de reintento reprocesa más tarde.

## 8. Despliegue
Docker/Render (plan gratuito). URL y credenciales de prueba: **https://gestion-documental-ia-1yc4.onrender.com** (admin `miguel.rojas@empresa.com` / agente `andres.gomez@empresa.com`, contraseña `Password123*`). Comandos en el README.

## 9. Limitaciones conocidas
- Sin Tesseract/Ollama instalados, la lectura de imágenes depende del modelo externo con consentimiento.
- Un solo worker (APScheduler en proceso); SQLite en Render gratuito no es persistente (usar PostgreSQL de Supabase/Neon).
- Las 18 imágenes del benchmark son limpias en su mayoría (16 limpias, 2 inclinadas): faltan casos de poca luz, borrosas y con reflejos, por lo que la precisión real en campo puede ser menor.
- El 77,8 % pasa a revisión humana porque los NIT de prueba no cumplen el dígito de verificación de la DIAN, lo que limita la confianza a 0,73 (< 0,75). Con NIT válidos la confianza llega a 0,88.
- Render plano gratuito: la base SQLite se reinicia en cada despliegue y el servicio se duerme tras 15 min sin uso.
- No hay portal de autoservicio para derechos del titular ni política de retención automática.
- No hay migraciones de esquema para tablas existentes.
