# Plan de pruebas del módulo de visión

## Pruebas unitarias y de integración (automáticas)
`python -m pytest test_suite.py -q` → 60 pruebas (base aislada temporal, modelo simulado): motor, flujos, proveedores y Plan B,
validación NIT/monto/fecha, pipeline de visión (confirmación, baja confianza, duplicado, rechazo, consentimiento, documentos
de identidad locales, sin invención de datos), control de acceso y auditoría, chatbot con memoria.

## Prueba con imágenes reales (requisito: ≥ 20 fotos de celular)
1. Tomar 20 o más fotos reales (facturas, recibos, capturas de error) con luz normal, poca luz, inclinadas, borrosas y con reflejos.
2. Copiarlas a `benchmark/imagenes/` y diligenciar `benchmark/ground_truth.csv` a mano (plantilla incluida).
3. `python -m benchmark.run_benchmark` (solo local) y `python -m benchmark.run_benchmark --consentimiento` (con Gemini).
4. Los reportes `benchmark/resultados_*.md/.csv` se anexan al documento técnico.

Métricas: precisión por campo (proveedor, NIT, número, fecha, total), documentos totalmente correctos, % enviado a revisión
humana, precisión de los auto-confirmados, precisión del tipo de documento, confianza y latencia medias, resultado por condición de captura.

## Resultados medidos
| Campo | Precisión | Muestras |
|---|---|---|
| (pendiente: ejecutar el benchmark con fotos reales) | — | — |

> Nota: el modo `--demo` usa imágenes sintéticas solo para validar el arnés; no es evidencia para la entrega.
