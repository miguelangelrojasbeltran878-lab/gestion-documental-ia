# Matriz de cumplimiento de la guía del tercer corte

Estado: ✅ hecho en código/docs · ⚠️ requiere acción del grupo (no automatizable desde el repositorio).

| Requisito de la guía | Estado | Evidencia |
|---|---|---|
| Inventario de flujos (disparador, pasos, servicios, resultado) | ✅ | `docs/INVENTARIO_FLUJOS.md`, `FLUJOS`, `/automatizacion/flujos` |
| Ruta A: flujos en código, cron/webhooks | ✅ | `automation_flows.py`, `scheduler.py` (APScheduler) |
| Modelo gratuito (Gemini/Groq/Ollama) | ✅ | `ai_provider.py`, `.env.example` |
| LangChain/LangGraph (cadenas, herramientas, memoria) | ✅ | `llm_chains.py`, `chatbot_graph.py` |
| Chatbot sigue funcionando sobre el nuevo motor | ✅ | `/api/v1/chatbot/mensaje`, pruebas de chatbot |
| Manejo de errores, reintentos y log por ejecución | ✅ | `automation_engine.py`, `tbl_ejecucion_automatizacion` |
| Claves en variables de entorno | ✅ | `config.py`, `.env.example` |
| Motor en servidor desplegado | ⚠️ | `Dockerfile`, `render.yaml` listos; falta desplegar y poner la URL |
| Módulo de visión (caso: facturas/recibos) | ✅ | `vision_service.py`, `/vision` |
| Captura web, celular, chatbot | ✅ | `vision.html`, chatbot con imagen |
| JSON con confianza; revisión si es baja | ✅ | umbral 0.75, `PENDIENTE_REVISION` |
| Visión dispara el proceso de negocio | ✅ | `proceso_negocio_vision`, `tbl_gasto` |
| Imágenes reales de celular, ≥ 20, % de aciertos | ⚠️ | Arnés listo en `benchmark/`; faltan las fotos y la corrida |
| Datos personales protegidos / modelo local | ✅ | `privacy.py`, consentimiento, documentos de identidad locales |
| Imágenes con control de acceso y registro de quién/cuándo | ✅ | `/archivo`, `AuditoriaIA` |
| Autenticación y roles; auditoría de la IA | ✅ | `auth.py`, `/api/v1/admin/auditoria` |
| Ley 1581 | ✅ | `docs/PROTECCION_DATOS_LEY1581.md` |
| Plan B ante cuota/fallo | ✅ | cadena de proveedores, cola de reintento |
| Pruebas unitarias | ✅ | `test_suite.py` (60) |
| Despliegue en internet | ⚠️ | ver arriba |
| Git con commits de todos los integrantes | ⚠️ | cada integrante debe commitear |
| README + `.env.example` | ✅ | `README.md`, `.env.example` |
| Documento técnico ≤ 10 páginas | ✅ (completar resultados) | `docs/DOCUMENTO_TECNICO.md` |
| Video ≤ 8 min | ⚠️ | guion en `docs/GUION_VIDEO.md` |
| Enlace y credenciales de prueba | ⚠️ | credenciales en README; falta URL |
