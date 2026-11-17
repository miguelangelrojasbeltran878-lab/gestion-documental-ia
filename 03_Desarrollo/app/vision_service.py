"""Módulo de visión por computador e IA multimodal.

Caso de uso elegido: **lectura de facturas y recibos** (más captura de errores y documentos de soporte).
Una foto tomada con el celular (o un PDF escaneado) se interpreta y el resultado, como JSON estructurado
con nivel de confianza por campo, alimenta un proceso de negocio (registro de gasto / actualización de ticket).

Cadena de procesamiento:
  1. Validación por contenido (firma binaria) y tamaño.
  2. Almacenamiento con control de acceso + auditoría de quién subió y cuándo.
  3. OCR local (PDF con texto -> pypdf; imagen -> Tesseract si está instalado).
  4. Enrutamiento por privacidad (Ley 1581): la imagen solo sale a un servicio externo con autorización
     expresa de quien la sube y nunca si es un documento de identidad; en otro caso se usa Ollama local o
     el extractor por reglas sobre el texto del OCR.
  5. Validaciones deterministas (dígito de verificación del NIT, fecha, monto) que ajustan la confianza.
  6. Confianza < umbral -> PENDIENTE_REVISION (el usuario confirma, corrige o rechaza antes de guardar).
  7. Confianza suficiente o confirmación humana -> proceso de negocio (`automation_flows`).
"""
import hashlib
import io
import json
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import ai_provider, automation_engine, config, models, privacy

log = logging.getLogger("vision_service")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
TIPOS_FINANCIEROS = {"factura", "recibo_pago", "cuenta_cobro"}
CAMPOS_EVALUABLES = ["emisor_o_proveedor", "identificacion_fiscal_nit", "numero_documento",
                     "fecha_emision", "monto_total"]


# --------------------------------------------------------------------------- validación y almacenamiento

_MIME_POR_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".pdf": "application/pdf"}


def normalizar_mime(filename: str, declarado: Optional[str]) -> str:
    """Los celulares y algunos navegadores mandan MIME vacío o genérico: se deduce de la extensión."""
    ext = os.path.splitext((filename or "").lower())[1]
    return _MIME_POR_EXT.get(ext) or declarado or "application/octet-stream"


def validar_archivo_vision(filename: str, file_bytes: bytes, mime_type: str) -> Tuple[bool, str]:
    """Valida tamaño, formato y firma binaria de la imagen o documento escaneado."""
    if not file_bytes:
        return False, "El archivo está vacío (0 bytes)."

    max_bytes = config.VISION_MAX_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        return False, f"El archivo excede el tamaño máximo permitido ({config.VISION_MAX_MB} MB)."

    ext = os.path.splitext(filename.lower())[1]
    if ext not in IMAGE_EXTENSIONS:
        return False, f"Formato no admitido ('{ext}'). Se admiten: .jpg, .jpeg, .png, .webp, .pdf."

    signatures = {
        ".jpg": lambda d: d.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda d: d.startswith(b"\xff\xd8\xff"),
        ".png": lambda d: d.startswith(b"\x89PNG\r\n\x1a\n"),
        ".webp": lambda d: d.startswith(b"RIFF") and d[8:12] == b"WEBP",
        ".pdf": lambda d: d.startswith(b"%PDF-"),
    }
    if not signatures[ext](file_bytes):
        return False, "El contenido del archivo no coincide con el formato declarado."
    return True, "OK"


def guardar_archivo_vision(filename: str, file_bytes: bytes) -> Tuple[str, str, str]:
    """Guarda el archivo en el almacenamiento privado y retorna (codigo, ruta, sha256).

    El directorio NO se expone como estático: solo se sirve mediante `/api/v1/vision/{codigo}/archivo`,
    que exige sesión y propiedad del documento.
    """
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    codigo = f"VIS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    ext = os.path.splitext(filename.lower())[1] or ".jpg"
    storage_folder = os.path.join(config.UPLOAD_DIR, "vision")
    os.makedirs(storage_folder, exist_ok=True)
    dest_path = os.path.join(storage_folder, f"{codigo}{ext}")
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    return codigo, dest_path, sha256


# --------------------------------------------------------------------------- auditoría y acceso

def auditar(db: Session, usuario: Optional[str], accion: str, recurso: Optional[str] = None,
            proveedor: Optional[str] = None, detalle: Optional[str] = None) -> None:
    db.add(models.AuditoriaIA(usuario=usuario, accion=accion, recurso=recurso, proveedor=proveedor,
                              detalle=(detalle or "")[:1000]))
    db.commit()


def puede_acceder(doc: models.DocumentoVision, user: models.UsuarioAgente, db: Optional[Session] = None) -> bool:
    """Administrador: todo. Agente: lo que subió él mismo o lo vinculado a un ticket que tiene asignado."""
    if user.rol == "Administrador":
        return True
    if doc.cargado_por == user.correo_electronico:
        return True
    if doc.id_ticket and db is not None:
        ticket = db.query(models.Ticket).filter(models.Ticket.id_ticket == doc.id_ticket).first()
        return bool(ticket and ticket.id_agente_asignado == user.id_agente)
    return False


# --------------------------------------------------------------------------- OCR local

def ocr_disponible() -> bool:
    try:
        import pytesseract  # noqa: F401
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_local(file_bytes: bytes, mime_type: str) -> str:
    """Texto del documento sin salir del servidor. Devuelve '' si no hay forma de leerlo localmente."""
    try:
        if mime_type == "application/pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n".join((p.extract_text() or "") for p in reader.pages[:10]).strip()
        if ocr_disponible():
            import pytesseract
            from PIL import Image, ImageOps
            img = ImageOps.exif_transpose(Image.open(io.BytesIO(file_bytes))).convert("L")
            img = ImageOps.autocontrast(img)
            return pytesseract.image_to_string(img, lang=config.OCR_LANGS).strip()
    except Exception as e:  # noqa: BLE001
        log.warning("OCR local falló: %s", e)
    return ""


# --------------------------------------------------------------------------- validaciones deterministas

_NIT_PESOS = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]


def digito_verificacion_nit(base: str) -> int:
    """Dígito de verificación DIAN para un NIT colombiano (sin DV)."""
    digitos = [int(c) for c in re.sub(r"\D", "", base)][::-1]
    total = sum(d * _NIT_PESOS[i] for i, d in enumerate(digitos[:len(_NIT_PESOS)]))
    r = total % 11
    return r if r in (0, 1) else 11 - r


def nit_valido(nit: Optional[str]) -> Optional[bool]:
    """True/False si el NIT trae DV verificable; None si no se puede verificar (sin guion/DV)."""
    if not nit:
        return None
    m = re.match(r"^\s*([\d.]{5,15})\s*-\s*(\d)\s*$", str(nit))
    if not m:
        return None
    base = re.sub(r"\D", "", m.group(1))
    return digito_verificacion_nit(base) == int(m.group(2))


def parse_monto(valor: Any) -> Optional[float]:
    """Convierte '1.450.200', '1,450,200.50', '$ 285.450,00' o números a float."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    s = re.sub(r"[^\d.,]", "", str(valor))
    if not s:
        return None
    if "." in s and "," in s:
        decimal = "." if s.rfind(".") > s.rfind(",") else ","
        s = s.replace("," if decimal == "." else ".", "").replace(decimal, ".")
    elif "." in s or "," in s:
        sep = "." if "." in s else ","
        partes = s.split(sep)
        if len(partes) > 2 or len(partes[-1]) == 3:
            s = "".join(partes)          # separador de miles
        else:
            s = ".".join(partes)         # decimal
    try:
        return float(s)
    except ValueError:
        return None


def normalizar_fecha(valor: Any) -> Optional[str]:
    if not valor:
        return None
    s = str(valor).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%y", "%d.%m.%Y"):
        try:
            return datetime.strptime(s[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- extractor por reglas (Plan B)

_TIPOS = [
    ("cedula", ["cédula de ciudadanía", "cedula de ciudadania", "registraduría", "registraduria", "república de colombia", "cédula"]),
    ("factura", ["factura", "invoice", "factura electrónica", "fe-", "iva", "subtotal"]),
    ("cuenta_cobro", ["cuenta de cobro", "cuenta cobro"]),
    ("recibo_pago", ["recibo", "comprobante de pago", "tirilla", "pago recibido"]),
    ("captura_error", ["error", "exception", "traceback", "stack trace", "http 500", "fatal"]),
    ("formulario", ["formulario", "solicitud de", "diligencie"]),
]


def clasificar_texto(texto: str) -> str:
    t = (texto or "").lower()
    for tipo, claves in _TIPOS:
        if any(c in t for c in claves):
            return tipo
    return "otro"


def extraer_campos_de_texto(texto: str) -> Dict[str, Any]:
    """Extractor determinista sobre texto OCR. No inventa datos: lo que no encuentra queda en None."""
    texto = texto or ""
    campos: Dict[str, Any] = {k: None for k in
                              ["emisor_o_proveedor", "cliente_o_receptor", "identificacion_fiscal_nit",
                               "numero_documento", "fecha_emision", "monto_total", "moneda",
                               "codigo_error_detectado", "observaciones_clave"]}

    m = re.search(r"(?i)\bNIT\b[\s.:#N°o]*([\d.]{5,15}\s*-\s*\d)", texto) or \
        re.search(r"\b(\d{3}\.\d{3}\.\d{3}\s*-\s*\d)\b", texto) or \
        re.search(r"(?i)\bNIT\b[\s.:#N°o]*(\d{8,10})\b", texto)
    if m:
        campos["identificacion_fiscal_nit"] = re.sub(r"\s+", "", m.group(1))

    m = re.search(r"(?i)(?:factura(?:\s+electr[oó]nica)?(?:\s+de\s+venta)?|recibo|comprobante|cuenta\s+de\s+cobro)\s*(?:n[o°º.]*|#|:)?\s*[:#]?\s*([A-Z]{0,4}-?\d{2,12})", texto) or \
        re.search(r"\b(FE-?\d{2,12})\b", texto, re.I)
    if m:
        campos["numero_documento"] = m.group(1).upper()

    m = re.search(r"(?i)(?:fecha(?:\s+de)?(?:\s+emisi[oó]n)?|date)\s*[:\-]?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4})", texto) or \
        re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b", texto)
    if m:
        campos["fecha_emision"] = normalizar_fecha(m.group(1))

    totales = re.findall(r"(?i)(?:total\s*a\s*pagar|valor\s*total|total\s*factura|total)\s*[:\-]?\s*\$?\s*([\d][\d.,]*)", texto)
    montos = [parse_monto(t) for t in totales]
    montos = [x for x in montos if x]
    if montos:
        campos["monto_total"] = max(montos)
        campos["moneda"] = "COP"

    lineas = [l.strip() for l in texto.splitlines() if len(l.strip()) > 3]
    for l in lineas[:6]:
        if re.search(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]{4,}", l) and not re.search(r"(?i)^(factura|nit|fecha|recibo|total|cliente)\b", l):
            campos["emisor_o_proveedor"] = l[:120]
            break

    m = re.search(r"(?i)\b(error\s*\d{3}|http\s*\d{3}|exception[:\s]+\w+)", texto)
    if m:
        campos["codigo_error_detectado"] = m.group(1)
    return campos


def confianza_por_campo(campos: Dict[str, Any]) -> Dict[str, float]:
    """Confianza 0-1 por campo basada en validaciones deterministas (no en lo que 'dice' el modelo)."""
    conf: Dict[str, float] = {}
    nit = campos.get("identificacion_fiscal_nit")
    v = nit_valido(nit)
    conf["identificacion_fiscal_nit"] = 0.0 if not nit else (0.95 if v else 0.45 if v is None else 0.2)
    conf["fecha_emision"] = 0.9 if normalizar_fecha(campos.get("fecha_emision")) else 0.0
    monto = parse_monto(campos.get("monto_total"))
    conf["monto_total"] = 0.9 if monto and monto > 0 else 0.0
    conf["emisor_o_proveedor"] = 0.8 if campos.get("emisor_o_proveedor") else 0.0
    conf["numero_documento"] = 0.8 if campos.get("numero_documento") else 0.0
    conf["codigo_error_detectado"] = 0.8 if campos.get("codigo_error_detectado") else 0.0
    return conf


def confianza_global(tipo: str, conf_campos: Dict[str, float], confianza_modelo: Optional[float]) -> float:
    """Combina las validaciones deterministas con la confianza declarada por el modelo (la más baja manda)."""
    if tipo in TIPOS_FINANCIEROS:
        pesos = {"monto_total": 0.3, "identificacion_fiscal_nit": 0.2, "fecha_emision": 0.2,
                 "emisor_o_proveedor": 0.15, "numero_documento": 0.15}
        base = sum(conf_campos.get(k, 0.0) * w for k, w in pesos.items())
    else:
        presentes = [v for v in conf_campos.values() if v > 0]
        base = (sum(presentes) / len(conf_campos)) if conf_campos else 0.0
        base = max(base, 0.5 if presentes else 0.0)
    if confianza_modelo is not None:
        if tipo in TIPOS_FINANCIEROS:
            base = min(base, float(confianza_modelo))   # lo validable (NIT, total, fecha) limita al modelo
        else:  # sin campos que validar de forma determinista: manda la legibilidad declarada, con tope si no hay datos
            base = float(confianza_modelo) if base > 0 else min(float(confianza_modelo), 0.5)
    return round(max(0.0, min(0.99, base)), 2)


# --------------------------------------------------------------------------- modelo multimodal

PROMPT_VISION = """Analiza esta imagen o documento escaneado (factura, recibo, captura de error, formulario o documento de soporte).
Devuelve SOLO un JSON válido con esta estructura (usa null cuando un dato no sea legible; NO inventes valores):
{
  "document_type": "factura | recibo_pago | cuenta_cobro | captura_error | formulario | cedula | certificado | otro",
  "categoria_sugerida": "Facturación y Auditoría | Soporte Técnico | Conectividad y Servidores | Acceso y Cuentas | Gestión Documental",
  "prioridad_sugerida": "Alta | Media | Baja",
  "texto_completo_extraido": "transcripción fiel del texto visible",
  "resumen": "resumen ejecutivo en 2 líneas",
  "confidence": 0.0,
  "fields": {
    "emisor_o_proveedor": null, "cliente_o_receptor": null, "identificacion_fiscal_nit": null,
    "numero_documento": null, "fecha_emision": "YYYY-MM-DD", "monto_total": 0.0, "moneda": "COP",
    "codigo_error_detectado": null, "observaciones_clave": null
  }
}
`confidence` (0.0 a 1.0) debe reflejar la legibilidad real: baja si la foto está borrosa, cortada o con reflejos."""


def _usar_modelo(file_bytes: bytes, mime_type: str, *, solo_local: bool) -> Tuple[Optional[Dict[str, Any]], str]:
    """Llama al modelo multimodal. Devuelve (datos, proveedor|error)."""
    if mime_type == "application/pdf" and not solo_local:
        images = [(file_bytes, mime_type)]  # Gemini admite PDF
    elif mime_type == "application/pdf":
        return None, "PDF no soportado por el modelo local"
    else:
        images = [(file_bytes, mime_type)]
    res = ai_provider.generate(PROMPT_VISION, json_mode=True, images=images,
                               system="Eres un perito en visión por computador y análisis documental. Responde solo JSON.",
                               local_only=solo_local)
    if res.ok and isinstance(res.data, dict):
        res.data["proveedor"] = res.provider
        return res.data, res.provider
    return None, res.error or "sin proveedor disponible"


def _analisis_por_reglas(texto: str) -> Dict[str, Any]:
    tipo = clasificar_texto(texto)
    campos = extraer_campos_de_texto(texto)
    obs = "Extracción por reglas sobre texto OCR local." if texto else \
        "No fue posible leer el documento: sin OCR local ni modelo disponible. Ingrese los datos manualmente."
    campos["observaciones_clave"] = obs
    return {
        "document_type": tipo,
        "categoria_sugerida": "Facturación y Auditoría" if tipo in TIPOS_FINANCIEROS else "Gestión Documental",
        "prioridad_sugerida": "Alta" if tipo == "captura_error" else "Media",
        "texto_completo_extraido": texto[:3000],
        "resumen": f"Documento clasificado como {tipo}.",
        "confidence": None,
        "proveedor": "local_reglas" if texto else "sin_lectura",
        "fields": campos,
    }


def analizar_documento(file_bytes: bytes, mime_type: str, consentimiento: bool = False) -> Dict[str, Any]:
    """Enrutamiento por privacidad + extracción. Devuelve el análisis con `plan_b`, `enviado_externo` y `error_ia`."""
    texto_local = ocr_local(file_bytes, mime_type)
    tipo_previo = clasificar_texto(texto_local)
    datos_personales = privacy.detectar_datos_personales(texto_local)
    es_identidad = privacy.tipo_requiere_modelo_local(tipo_previo) or "cedula" in datos_personales

    externo_permitido = config.AI_EXTERNAL_ALLOWED and (consentimiento or not config.VISION_REQUIRE_CONSENT)
    solo_local = es_identidad or not externo_permitido

    analisis: Optional[Dict[str, Any]] = None
    error_ia = ""
    enviado_externo = False
    if ai_provider.is_available(local_only=solo_local, vision=True):
        analisis, info = _usar_modelo(file_bytes, mime_type, solo_local=solo_local)
        if analisis:
            enviado_externo = analisis.get("proveedor") in ai_provider.EXTERNAL
        else:
            error_ia = info

    plan_b = analisis is None
    if plan_b:
        analisis = _analisis_por_reglas(texto_local)

    analisis.setdefault("fields", {})
    tipo = str(analisis.get("document_type") or "otro")
    campos = analisis["fields"]
    if plan_b is False:  # normaliza lo que devolvió el modelo
        campos["monto_total"] = parse_monto(campos.get("monto_total"))
        campos["fecha_emision"] = normalizar_fecha(campos.get("fecha_emision")) or campos.get("fecha_emision")
    conf_campos = confianza_por_campo(campos)
    modelo_conf = analisis.get("confidence")
    try:
        modelo_conf = float(modelo_conf) if modelo_conf is not None else None
    except (TypeError, ValueError):
        modelo_conf = None
    analisis["confidence"] = confianza_global(tipo, conf_campos, modelo_conf)
    analisis["confianza_campos"] = conf_campos
    analisis["plan_b"] = plan_b
    analisis["enviado_externo"] = enviado_externo
    analisis["solo_local"] = solo_local
    analisis["error_ia"] = error_ia
    analisis["datos_personales_detectados"] = datos_personales
    return analisis


# --------------------------------------------------------------------------- flujo completo

def _aplicar_analisis(db: Session, doc: models.DocumentoVision, analisis: Dict[str, Any], usuario: str) -> Dict[str, Any]:
    doc.tipo_documento = analisis.get("document_type", "otro")
    doc.repositorio = f"repo_{doc.tipo_documento}"
    doc.texto_extraido = analisis.get("texto_completo_extraido", "")
    campos = dict(analisis.get("fields", {}))
    campos["_confianza_campos"] = analisis.get("confianza_campos", {})
    doc.campos_json = json.dumps(campos, ensure_ascii=False, default=str)
    doc.confianza = float(analisis["confidence"])
    doc.proveedor = analisis.get("proveedor", "desconocido")
    doc.error = analisis.get("error_ia") or None

    sin_lectura = analisis.get("proveedor") == "sin_lectura"
    if sin_lectura and analisis.get("error_ia"):
        doc.estado = "COLA_REINTENTO"      # el modelo estaba configurado pero falló: la cola lo reintenta
    elif doc.confianza < config.VISION_CONFIDENCE_THRESHOLD:
        doc.estado = "PENDIENTE_REVISION"
    else:
        doc.estado = "CONFIRMADO"
        doc.campos_confirmados_json = doc.campos_json
    db.commit()
    db.refresh(doc)

    auditar(db, usuario, "EXTRACCION_IA", doc.codigo, doc.proveedor,
            f"tipo={doc.tipo_documento} confianza={doc.confianza} estado={doc.estado} "
            f"externo={analisis.get('enviado_externo')} solo_local={analisis.get('solo_local')} "
            f"plan_b={analisis.get('plan_b')}")

    proceso = None
    if doc.estado == "CONFIRMADO":
        from app import automation_flows
        proceso = automation_flows.aplicar_proceso_negocio(db, doc, usuario)
    return {
        "ok": True,
        "codigo_vision": doc.codigo,
        "tipo": doc.tipo_documento,
        "confianza": doc.confianza,
        "estado": doc.estado,
        "proveedor_ia": doc.proveedor,
        "plan_b_utilizado": bool(analisis.get("plan_b")),
        "proceso_negocio": proceso,
    }


def procesar_documento_vision(
    db: Session,
    filename: str,
    file_bytes: bytes,
    mime_type: str,
    cargado_por: str = "cliente",
    id_ticket: Optional[int] = None,
    consentimiento: bool = False,
) -> models.DocumentoVision:
    """Flujo completo con persistencia, confianza, auditoría y disparo del proceso de negocio."""
    mime_type = normalizar_mime(filename, mime_type)
    valido, mensaje = validar_archivo_vision(filename, file_bytes, mime_type)
    if not valido:
        raise ValueError(mensaje)

    codigo, ruta, sha256 = guardar_archivo_vision(filename, file_bytes)
    doc = models.DocumentoVision(
        codigo=codigo, id_ticket=id_ticket, nombre_original=os.path.basename(filename)[:255],
        mime_type=mime_type, tamano_bytes=len(file_bytes), sha256=sha256, ruta_archivo=ruta,
        cargado_por=cargado_por, estado="PROCESANDO",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    auditar(db, cargado_por, "SUBIDA_IMAGEN", codigo, None,
            f"archivo={doc.nombre_original} bytes={len(file_bytes)} sha256={sha256[:12]} consentimiento={consentimiento}")

    automation_engine.ejecutar_servicio_con_auditoria(
        db=db, flujo="vision_documento", proceso="EXTRACCION_DOCUMENTAL",
        func=lambda: _aplicar_analisis(db, doc, analizar_documento(file_bytes, mime_type, consentimiento), cargado_por),
        usuario=cargado_por, id_ticket=id_ticket,
        entrada_resumen=f"{codigo}: {doc.nombre_original} ({len(file_bytes)} bytes, {mime_type})",
    )
    db.refresh(doc)
    return doc


def reprocesar_documento(db: Session, doc: models.DocumentoVision, usuario: str = "scheduler") -> Dict[str, Any]:
    """Reintenta documentos que quedaron en COLA_REINTENTO (modelo caído / cuota agotada)."""
    with open(doc.ruta_archivo, "rb") as f:
        data = f.read()
    consent = False  # una cola automática nunca amplía el consentimiento original: solo modelos locales/reglas
    return _aplicar_analisis(db, doc, analizar_documento(data, doc.mime_type, consent), usuario)


def confirmar_documento(db: Session, doc: models.DocumentoVision, datos: Dict[str, Any], usuario: str) -> Dict[str, Any]:
    tipo_corregido = str(datos.pop("tipo_documento", "") or "").strip()
    if tipo_corregido in TIPOS_FINANCIEROS | {"captura_error", "otro"}:
        doc.tipo_documento = tipo_corregido  # el revisor humano puede corregir el tipo detectado
    doc.campos_confirmados_json = json.dumps(datos, ensure_ascii=False)
    doc.estado = "CONFIRMADO"
    doc.revisado_por = usuario
    doc.fecha_revision = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    auditar(db, usuario, "CONFIRMACION_HUMANA", doc.codigo, doc.proveedor, "campos confirmados/corregidos por el usuario")
    from app import automation_flows
    return automation_flows.aplicar_proceso_negocio(db, doc, usuario)


def rechazar_documento(db: Session, doc: models.DocumentoVision, motivo: str, usuario: str) -> None:
    doc.estado = "RECHAZADO"
    doc.revisado_por = usuario
    doc.fecha_revision = datetime.utcnow()
    doc.error = (motivo or "Rechazado por el revisor")[:500]
    db.commit()
    auditar(db, usuario, "RECHAZO_HUMANO", doc.codigo, doc.proveedor, doc.error)
