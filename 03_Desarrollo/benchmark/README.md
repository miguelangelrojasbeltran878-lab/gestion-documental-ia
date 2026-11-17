# Benchmark de visión (Fase 3 de la guía)

1. Tome **mínimo 20 fotos reales con celular** (facturas, recibos, capturas de error) en condiciones variadas:
   luz normal, poca luz, inclinadas, borrosas, con reflejos. Cópielas a `benchmark/imagenes/`.
2. Copie `ground_truth.plantilla.csv` a `ground_truth.csv` y diligencie **a mano** lo que realmente dice cada foto
   (deje vacío el campo que no aparezca: no se evalúa).
3. Ejecute `python -m benchmark.run_benchmark` (solo modelos locales) y luego
   `python -m benchmark.run_benchmark --consentimiento` (con Gemini) para comparar.
   Cada corrida genera `resultados_<fecha>.md/.csv` para anexar al documento técnico.

`--demo` genera imágenes sintéticas únicamente para comprobar que el arnés funciona; **no** son evidencia válida
para la entrega. Las fotos reales contienen datos personales: están excluidas de Git (`.gitignore`).
