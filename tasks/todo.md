# Tareas: evolución del sistema

## Corte 1: acceso seguro y lenguaje coherente

- [ ] Proteger rutas y recursos documentales.
  - Aceptación: visitante recibe 401/403 en toda operación sensible; cada agente solo puede acceder a sus expedientes.
  - Verificación: pruebas de autorización y prueba local de rutas.
  - Archivos: `auth.py`, `main.py`, `make_batch_router.py`, `test_suite.py`.

- [ ] Eliminar secretos por defecto y validar archivos por contenido.
  - Aceptación: no hay secretos funcionales incrustados; archivos y descargas exigen validación y autorización.
  - Verificación: pruebas de token y formato inválido.
  - Archivos: `config.py`, `make_batch_router.py`, `vision_service.py`, `test_suite.py`.

- [ ] Corregir UI y chatbot para reflejar el motor propio.
  - Aceptación: textos, enlaces y estados no anuncian integraciones inexistentes; el chatbot diferencia datos disponibles de datos no extraíbles.
  - Verificación: pruebas y revisión local de `/`, `/crear-solicitud`, `/vision`.
  - Archivos: plantillas prioritarias, `ai_module.py`, `main.py`, pruebas.

## Punto de control

- [ ] Todas las pruebas pasan sin tocar la base de producción.
- [ ] Las rutas sensibles están protegidas y la interfaz no hace afirmaciones falsas.

## Cortes posteriores

- [ ] Implementar servicios propios auditables de automatización documental.
- [ ] Integrar OCR real tras aprobación de la dependencia seleccionada.
- [ ] Reemplazar benchmark sintético por 20 fotos reales autorizadas/anonimizadas.
- [ ] Preparar migraciones, despliegue y documentación Word basada en evidencia.

## Tercer corte — aplicación de la guía (estado)
- [x] Motor propio (8 flujos, APScheduler, reintentos, log), LangChain/LangGraph, cadena Gemini→Groq→Ollama→reglas
- [x] Visión de facturas/recibos con confianza, revisión humana, gasto, auditoría, consentimiento
- [x] Docs en 03_Desarrollo/docs, benchmark, Docker/Render, 60 pruebas
- [ ] Desplegar y anotar URL; video ≤ 8 min; ≥ 20 fotos reales + benchmark; commits de todos los integrantes
