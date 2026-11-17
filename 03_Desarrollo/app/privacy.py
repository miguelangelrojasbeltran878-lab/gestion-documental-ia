"""Protección de datos personales (Ley 1581 de 2012).

- `anonimizar_texto`: enmascara datos personales antes de enviar texto a un servicio externo.
- `detectar_datos_personales`: indica qué categorías de datos personales aparecen en un texto.
- `tipo_requiere_modelo_local`: documentos de identidad nunca salen a servicios externos.
"""
import re
from typing import Dict, List, Tuple

# Orden importa: patrones más específicos primero.
_PATRONES: List[Tuple[str, "re.Pattern[str]", str]] = [
    ("correo", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[CORREO]"),
    ("telefono", re.compile(r"(?<!\d)(?:\+?57[\s-]?)?3\d{2}[\s-]?\d{3}[\s-]?\d{4}(?!\d)"), "[TELEFONO]"),
    ("cuenta_bancaria", re.compile(r"(?<!\d)\d{10,20}(?!\d)"), "[CUENTA]"),
    ("cedula", re.compile(r"(?i)\b(?:c\.?\s?c\.?|cedula|cédula|documento)\s*(?:n[o°º.]*)?\s*:?\s*\d{1,3}(?:[.\s]?\d{3}){2,3}\b"), "[CEDULA]"),
]

TIPOS_SOLO_LOCAL = {"cedula", "cédula", "documento_identidad", "rut", "certificado"}


def detectar_datos_personales(texto: str) -> Dict[str, int]:
    """Cuenta las coincidencias por categoría de dato personal."""
    hallazgos: Dict[str, int] = {}
    for nombre, patron, _ in _PATRONES:
        n = len(patron.findall(texto or ""))
        if n:
            hallazgos[nombre] = n
    return hallazgos


def anonimizar_texto(texto: str) -> str:
    """Reemplaza datos personales por etiquetas. El NIT de una empresa no es dato personal y se conserva."""
    salida = texto or ""
    for _, patron, etiqueta in _PATRONES:
        salida = patron.sub(etiqueta, salida)
    return salida


def tipo_requiere_modelo_local(tipo_documento: str) -> bool:
    return (tipo_documento or "").strip().lower() in TIPOS_SOLO_LOCAL


def enmascarar_identificador(valor: str) -> str:
    """Muestra solo los últimos 3 caracteres (para logs de auditoría)."""
    valor = (valor or "").strip()
    if len(valor) <= 3:
        return "***"
    return "*" * (len(valor) - 3) + valor[-3:]
