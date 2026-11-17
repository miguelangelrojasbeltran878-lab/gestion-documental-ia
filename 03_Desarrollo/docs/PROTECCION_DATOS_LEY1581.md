# Protección de datos personales (Ley 1581 de 2012)

## Datos personales que maneja el sistema
| Dato | Dónde | Naturaleza |
|---|---|---|
| Nombre, correo, teléfono, documento del cliente | `tbl_cliente`, tickets | Privado |
| Contraseñas de agentes | `tbl_agente` | Solo hash PBKDF2-SHA256 |
| Imágenes de facturas/recibos (NIT, nombres, montos) | `storage/vision` | Privado / financiero |
| Cédula, RUT u otro documento de identidad en imágenes | Visión | Sensible: se procesa **solo en local** |
| Contenido de lotes documentales | `temp_batches` | Privado |

## Cumplimiento
- **Finalidad**: los datos se usan únicamente para gestionar tickets, procesar documentos y registrar gastos; se informa en el formulario.
- **Autorización**: el cliente marca el consentimiento previo en el registro; para enviar una imagen a un modelo externo (Gemini) el usuario debe marcar `autoriza_envio_externo` (`VISION_REQUIRE_CONSENT`). Sin consentimiento solo se usa OCR/modelo local.
- **Minimización y anonimización**: el texto se anonimiza (documentos, correos, teléfonos) antes de ir a un LLM externo; los documentos de identidad nunca salen del servidor.
- **Seguridad**: contraseñas PBKDF2 (100.000 iteraciones), cookies `HttpOnly`/`SameSite`/`Secure` en producción, claves de API solo en variables de entorno, acceso a archivos con control de rol y propiedad (403 + auditoría `ACCESO_DENEGADO`), validación de firma binaria y tamaño de archivos.
- **Trazabilidad**: `tbl_auditoria_ia` registra quién y cuándo (SUBIDA_IMAGEN, EXTRACCION_IA, ACCESO_ARCHIVO, ACCESO_DENEGADO, CONFIRMACION_HUMANA, RECHAZO_HUMANO, GASTO_REGISTRADO, DUPLICADO_DETECTADO, CHATBOT_TURNO); consultable por el administrador en `/api/v1/admin/auditoria`.
- **Supervisión humana**: confianza < 0.75 → `PENDIENTE_REVISION`; ninguna decisión financiera se aplica sin confirmación si hay duda.
- **Conservación y supresión**: pendiente de política formal; las imágenes de prueba reales están excluidas de Git.
- **Derechos del titular**: consulta, actualización y supresión se atienden por el administrador (limitación: no hay portal de autoservicio).
