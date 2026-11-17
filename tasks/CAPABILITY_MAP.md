# Capability map: evolución verificable del sistema

| Módulo | Responsabilidad | Depende de |
|---|---|---|
| `access-control` | Sesiones, roles, autorización de recursos, validación segura de archivos | — |
| `document-workflow` | Automatización propia, persistencia, auditoría y revisión humana | `access-control` |
| `ai-chatbot` | Extracción autorizada de contenido, consulta documental y plan B | `access-control`, `document-workflow` |
| `vision-ocr` | OCR/visión real, confianza por campo y resultado estructurado | `access-control`, `document-workflow` |
| `experience-ui` | Navegación, estados, formularios y consumo de los módulos anteriores | `access-control`, `ai-chatbot`, `vision-ocr` |
| `delivery-evidence` | Pruebas reales, Word académico y despliegue reproducible | Todos los módulos anteriores |

Orden de construcción: `access-control` → `document-workflow` → (`ai-chatbot`, `vision-ocr`) → `experience-ui` → `delivery-evidence`.

La primera entrega aprobable combina los dos primeros cortes verticales de alto riesgo: cierre de accesos y reparación del chatbot/UI sin alterar datos existentes.
