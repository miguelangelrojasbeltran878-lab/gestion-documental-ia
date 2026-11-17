"""Métricas del benchmark de visión: comparación campo a campo contra la verdad de terreno."""
import unicodedata
from typing import Any, Dict, List, Optional

from app import vision_service

CAMPOS = ["emisor_o_proveedor", "identificacion_fiscal_nit", "numero_documento", "fecha_emision", "monto_total"]


def _txt(v: Any) -> str:
    sin_tildes = unicodedata.normalize("NFKD", str(v or "")).encode("ascii", "ignore").decode()
    return "".join(ch for ch in sin_tildes.lower() if ch.isalnum())


def coincide(campo: str, esperado: Any, obtenido: Any) -> Optional[bool]:
    """True/False si hay valor esperado; None si la verdad de terreno no define el campo (no se evalúa)."""
    if esperado in (None, ""):
        return None
    if campo == "monto_total":
        a, b = vision_service.parse_monto(esperado), vision_service.parse_monto(obtenido)
        return a is not None and b is not None and abs(a - b) < 0.5
    if campo == "fecha_emision":
        return vision_service.normalizar_fecha(esperado) == vision_service.normalizar_fecha(obtenido)
    if campo == "identificacion_fiscal_nit":
        return _txt(esperado).lstrip("0") == _txt(obtenido).lstrip("0")
    if campo == "emisor_o_proveedor":
        e, o = _txt(esperado), _txt(obtenido)
        return bool(e) and bool(o) and (e in o or o in e)
    return _txt(esperado) == _txt(obtenido)


def resumir(filas: List[Dict[str, Any]], umbral: float = 0.75) -> Dict[str, Any]:
    """`filas`: una por imagen con esperado, obtenido, confianza, tipo_esperado, tipo_obtenido, latencia_ms."""
    por_campo: Dict[str, Dict[str, int]] = {c: {"ok": 0, "n": 0} for c in CAMPOS}
    confirmadas_ok = confirmadas = 0
    for f in filas:
        resultados = {}
        for c in CAMPOS:
            r = coincide(c, f["esperado"].get(c), f["obtenido"].get(c))
            if r is None:
                continue
            resultados[c] = r
            por_campo[c]["n"] += 1
            por_campo[c]["ok"] += int(r)
        f["campos_ok"] = resultados
        f["documento_ok"] = bool(resultados) and all(resultados.values())
        if f["confianza"] >= umbral:
            confirmadas += 1
            confirmadas_ok += int(f["documento_ok"])
    n = len(filas) or 1
    con_tipo = [f for f in filas if f.get("tipo_esperado")]
    return {
        "imagenes": len(filas),
        "precision_por_campo": {c: (round(100 * v["ok"] / v["n"], 1) if v["n"] else None) for c, v in por_campo.items()},
        "muestras_por_campo": {c: v["n"] for c, v in por_campo.items()},
        "precision_tipo_documento": (round(100 * sum(f["tipo_esperado"] == f["tipo_obtenido"] for f in con_tipo) / len(con_tipo), 1)
                                     if con_tipo else None),
        "documentos_completamente_correctos": round(100 * sum(f["documento_ok"] for f in filas) / n, 1),
        "enviadas_a_revision_humana": round(100 * sum(f["confianza"] < umbral for f in filas) / n, 1),
        "precision_de_las_auto_confirmadas": round(100 * confirmadas_ok / confirmadas, 1) if confirmadas else None,
        "confianza_media": round(sum(f["confianza"] for f in filas) / n, 2),
        "latencia_media_ms": int(sum(f.get("latencia_ms", 0) for f in filas) / n),
    }
