# Guion del video de demostración (máx. 8 min)

Mostrar el sistema **desplegado** (URL pública), no localhost.

| Min | Escena | Qué mostrar |
|---|---|---|
| 0:00–0:30 | Contexto | Problema, caso de uso: lectura de facturas/recibos; n8n reemplazado por código propio |
| 0:30–1:30 | Login y roles | Agente vs Administrador; permisos |
| 1:30–3:00 | Visión con foto real | Subir foto desde el celular; JSON con confianza por campo; consentimiento para modelo externo |
| 3:00–4:00 | Baja confianza | Documento en `PENDIENTE_REVISION`; corregir y confirmar; rechazar otro |
| 4:00–5:00 | Disparo del proceso | Confirmación crea el gasto; duplicado detectado; captura de error sube prioridad del ticket |
| 5:00–6:00 | Chatbot | Enviar imagen por el chatbot; memoria de la conversación |
| 6:00–7:00 | Motor y flujos | `/automatizacion/flujos`: inventario, log, ejecutar un flujo cron como admin |
| 7:00–7:40 | Plan B | Sin clave/cuota del modelo: respuesta local o cola de reintento |
| 7:40–8:00 | Auditoría y resultados | `/api/v1/admin/auditoria`, tabla de precisión del benchmark |
