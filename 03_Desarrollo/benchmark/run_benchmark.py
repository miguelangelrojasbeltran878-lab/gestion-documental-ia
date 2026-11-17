"""Benchmark del módulo de visión (Fase 3 de la guía: mínimo 20 imágenes reales con medición).

Uso (desde 03_Desarrollo):
    python -m benchmark.run_benchmark                    # usa benchmark/imagenes + benchmark/ground_truth.csv
    python -m benchmark.run_benchmark --consentimiento   # permite además el modelo externo (Gemini)
    python -m benchmark.run_benchmark --demo             # genera 20 imágenes SINTÉTICAS solo para probar el arnés

La verdad de terreno (ground_truth.csv) la diligencia el grupo a mano mirando cada foto. Las imágenes
sintéticas del modo --demo NO sirven como evidencia para la entrega: la guía exige fotos reales de celular.
"""
import argparse
import csv
import mimetypes
import os
import random
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config, vision_service  # noqa: E402
from benchmark.metricas import CAMPOS, resumir  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
IMAGENES = os.path.join(AQUI, "imagenes")
GT = os.path.join(AQUI, "ground_truth.csv")
COLUMNAS_GT = ["archivo", "tipo", "condicion", "emisor_o_proveedor", "identificacion_fiscal_nit",
               "numero_documento", "fecha_emision", "monto_total"]


def generar_demo(n: int = 20) -> None:
    """Facturas sintéticas con degradaciones (inclinación, desenfoque, poca luz) para validar el arnés."""
    from PIL import Image, ImageDraw, ImageFilter
    os.makedirs(IMAGENES, exist_ok=True)
    random.seed(7)
    filas = []
    for i in range(n):
        base = str(random.randint(800000000, 901999999))
        nit = f"{base}-{vision_service.digito_verificacion_nit(base)}"
        monto = random.randint(50, 5000) * 1000
        numero = f"FE-{random.randint(1000, 99999)}"
        fecha = f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
        emisor = random.choice(["Papelería El Tintero S.A.S.", "Ferretería Los Andes", "Tecnologías del Valle Ltda"])
        img = Image.new("RGB", (900, 1100), "white")
        d = ImageDraw.Draw(img)
        lineas = [emisor, f"NIT: {nit}", f"Factura Electrónica de Venta No. {numero}",
                  f"Fecha de emisión: {fecha}", "Total a pagar: $" + f"{monto:,}".replace(",", ".")]
        for y, linea in enumerate(lineas):
            d.text((60, 80 + y * 60), linea, fill="black")
        cond = "limpia"
        if i % 4 == 1:
            img = img.rotate(random.choice([-6, 6]), expand=True, fillcolor="white")
            cond = "inclinada"
        elif i % 4 == 2:
            img = img.filter(ImageFilter.GaussianBlur(2.2))
            cond = "desenfocada"
        elif i % 4 == 3:
            img = Image.eval(img, lambda v: int(v * 0.55))
            cond = "poca_luz"
        nombre = f"demo_{i + 1:02d}.jpg"
        img.save(os.path.join(IMAGENES, nombre), quality=80)
        filas.append([nombre, "factura", cond, emisor, nit, numero, fecha, monto])
    with open(GT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNAS_GT)
        w.writerows(filas)
    print(f"Generadas {n} imágenes sintéticas en {IMAGENES} y su ground_truth.csv (SOLO DEMO).")


def correr(consentimiento: bool) -> None:
    if not os.path.exists(GT):
        sys.exit("Falta benchmark/ground_truth.csv (ver ground_truth.plantilla.csv).")
    filas = []
    with open(GT, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            ruta = os.path.join(IMAGENES, r["archivo"])
            if not os.path.exists(ruta):
                print(f"  ! No existe la imagen {r['archivo']}, se omite")
                continue
            mime = mimetypes.guess_type(ruta)[0] or "image/jpeg"
            with open(ruta, "rb") as fh:
                data = fh.read()
            t0 = time.time()
            res = vision_service.analizar_documento(data, mime, consentimiento=consentimiento)
            filas.append({
                "archivo": r["archivo"], "condicion": r.get("condicion", ""),
                "esperado": {c: r.get(c) for c in CAMPOS},
                "obtenido": res.get("fields", {}), "confianza": res["confidence"],
                "estado": "PENDIENTE_REVISION" if res["confidence"] < config.VISION_CONFIDENCE_THRESHOLD else "CONFIRMADO",
                "tipo_esperado": r.get("tipo"), "tipo_obtenido": res.get("document_type"),
                "proveedor": res.get("proveedor"), "latencia_ms": int((time.time() - t0) * 1000),
            })
            print(f"  {r['archivo']:<28} {str(res.get('proveedor')):<12} conf={res['confidence']:.2f}")

    if len(filas) < 20:
        print(f"\nAVISO: la guía exige al menos 20 imágenes; hay {len(filas)}.")
    resumen = resumir(filas, config.VISION_CONFIDENCE_THRESHOLD)
    salida = os.path.join(AQUI, "resultados_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    with open(salida + ".csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "condicion", "proveedor", "confianza", "estado", "documento_ok", "latencia_ms"] + CAMPOS)
        for x in filas:
            w.writerow([x["archivo"], x["condicion"], x["proveedor"], x["confianza"], x["estado"], x["documento_ok"],
                        x["latencia_ms"]] + [("OK" if x["campos_ok"][c] else "FALLA") if c in x["campos_ok"] else "" for c in CAMPOS])
    with open(salida + ".md", "w", encoding="utf-8") as f:
        f.write(f"# Resultados del benchmark de visión ({datetime.now():%Y-%m-%d %H:%M})\n\n")
        f.write(f"- Imágenes evaluadas: **{resumen['imagenes']}**\n- Modelo externo permitido: **{consentimiento}**\n"
                f"- OCR local (Tesseract) disponible: **{vision_service.ocr_disponible()}**\n\n"
                "## Precisión por campo\n\n| Campo | Precisión | Muestras |\n|---|---|---|\n")
        for c in CAMPOS:
            p = resumen["precision_por_campo"][c]
            f.write(f"| {c} | {'—' if p is None else str(p) + ' %'} | {resumen['muestras_por_campo'][c]} |\n")
        f.write(f"\n## Indicadores globales\n\n"
                f"- Documentos con todos los campos correctos: {resumen['documentos_completamente_correctos']} %\n"
                f"- Enviados a revisión humana (confianza < {config.VISION_CONFIDENCE_THRESHOLD}): {resumen['enviadas_a_revision_humana']} %\n"
                f"- Precisión de los auto-confirmados: {resumen['precision_de_las_auto_confirmadas']} %\n"
                f"- Precisión del tipo de documento: {resumen['precision_tipo_documento']} %\n"
                f"- Confianza media: {resumen['confianza_media']}\n- Latencia media: {resumen['latencia_media_ms']} ms\n")
        f.write("\n## Por condición de captura\n\n| Condición | Imágenes | Documentos correctos |\n|---|---|---|\n")
        for cond in sorted({x["condicion"] for x in filas}):
            g = [x for x in filas if x["condicion"] == cond]
            f.write(f"| {cond or '—'} | {len(g)} | {round(100 * sum(x['documento_ok'] for x in g) / len(g), 1)} % |\n")
    print(f"\nResumen: {resumen}\nReporte: {salida}.md")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--consentimiento", action="store_true", help="permite enviar las imágenes al modelo externo configurado")
    ap.add_argument("--demo", action="store_true", help="genera imágenes sintéticas (solo para probar el arnés)")
    a = ap.parse_args()
    if a.demo:
        generar_demo()
    correr(a.consentimiento)
