"""Módulo de Visión por Computador e IA Multimodal.
Procesa imágenes y documentos escaneados (.jpg, .jpeg, .png, .webp, .pdf),
extrae texto estructurado mediante Gemini Multimodal o OCR / extractor local,
y genera entidades estructuradas (tipo, fecha, emisor, montos, número, NIT) con nivel de confianza.
"""
import os
import io
import json
import uuid
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session
from app import models, config, ai_provider, automation_engine

log = logging.getLogger("vision_service")

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


def validar_archivo_vision(filename: str, file_bytes: bytes, mime_type: str) -> Tuple[bool, str]:
    """Valida tamaño, formato y presencia de bytes de la imagen o documento escaneado."""
    if not file_bytes:
        return False, "El archivo está vacío (0 bytes)."
    
    max_bytes = config.VISION_MAX_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        return False, f"El archivo excede el tamaño máximo permitido ({config.VISION_MAX_MB} MB)."
    
    ext = os.path.splitext(filename.lower())[1]
    if ext not in IMAGE_EXTENSIONS and mime_type not in ALLOWED_IMAGE_TYPES:
        return False, f"Formato no admitido ('{ext}'). Se admiten: .jpg, .jpeg, .png, .webp, .pdf."
    
    return True, "OK"


def guardar_archivo_vision(filename: str, file_bytes: bytes) -> Tuple[str, str, str]:
    """Guarda el archivo en el directorio de almacenamiento y retorna (codigo, ruta_guardada, sha256)."""
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    codigo = f"VIS-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    ext = os.path.splitext(filename.lower())[1] or ".jpg"
    
    storage_folder = os.path.join(config.UPLOAD_DIR, "vision")
    os.makedirs(storage_folder, exist_ok=True)
    
    dest_path = os.path.join(storage_folder, f"{codigo}{ext}")
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
        
    return codigo, dest_path, sha256


def procesar_vision_con_gemini(filename: str, file_bytes: bytes, mime_type: str) -> Optional[Dict[str, Any]]:
    """Envía la imagen/documento a Gemini Multimodal para interpretación y extracción estructurada JSON."""
    if not ai_provider.is_available():
        return None
        
    prompt = """Analiza detenidamente esta imagen o documento escaneado (factura, recibo de pago, captura de error, formulario o documento de soporte).
Extrae la información en formato JSON estrictamente válido, sin texto adicional alrededor, con esta estructura:
{
  "document_type": "factura | recibo_pago | captura_error | formulario | certificado | otro",
  "categoria_sugerida": "Facturación y Auditoría | Soporte Técnico | Conectividad y Servidores | Acceso y Cuentas | Gestión Documental",
  "prioridad_sugerida": "Alta | Media | Baja",
  "texto_completo_extraido": "Transcripción o lectura OCR fiel del texto visible",
  "resumen": "Resumen claro y ejecutivo en 2 o 3 líneas del documento",
  "confidence": 0.95,
  "fields": {
    "emisor_o_proveedor": "Nombre del emisor/empresa detectada o null",
    "cliente_o_receptor": "Nombre del cliente/receptor detectado o null",
    "identificacion_fiscal_nit": "NIT, RUT o ID fiscal o null",
    "numero_documento": "Número de factura, consecutivo o ID de ticket reportado o null",
    "fecha_emision": "YYYY-MM-DD o null",
    "fecha_vencimiento": "YYYY-MM-DD o null",
    "monto_total": 0.0,
    "moneda": "COP | USD | EUR | null",
    "codigo_error_detectado": "Código de error técnico si es captura (ej. Error 500) o null",
    "observaciones_clave": "Observaciones relevantes detectadas en el documento"
  }
}
Si un campo numérico no está presente, usa 0 o null. La confianza (confidence) debe ser un número flotante entre 0.0 y 1.0 que refleje la legibilidad real del documento."""

    res = ai_provider.generate(
        prompt=prompt,
        json_mode=True,
        images=[(file_bytes, mime_type)],
        system="Eres un perito experto en visión por computador y análisis documental multimodal."
    )
    
    if res.ok and res.data and isinstance(res.data, dict):
        res.data["proveedor"] = "gemini_multimodal"
        return res.data
    return None


def procesar_vision_fallback_local(filename: str, file_bytes: bytes, mime_type: str) -> Dict[str, Any]:
    """Plan B local: análisis heurístico basado en bytes legibles o estructura de archivo."""
    texto_detectado = ""
    try:
        texto_detectado = file_bytes[:10000].decode("utf-8", errors="ignore")
    except Exception:
        pass
        
    texto_low = f"{filename} {texto_detectado}".lower()
    
    doc_type = "otro"
    categoria = "Soporte Técnico"
    prioridad = "Media"
    
    if any(k in texto_low for k in ["factura", "fe-", "invoice", "cobro", "iva", "subtotal", "valor total"]):
        doc_type = "factura"
        categoria = "Facturación y Auditoría"
    elif any(k in texto_low for k in ["recibo", "pago", "comprobante", "consignacion", "transferencia"]):
        doc_type = "recibo_pago"
        categoria = "Facturación y Auditoría"
    elif any(k in texto_low for k in ["error", "exception", "500", "crash", "fallo", "bloqueo", "falla"]):
        doc_type = "captura_error"
        prioridad = "Alta"
    elif any(k in texto_low for k in ["formulario", "solicitud", "inscripcion", "registro"]):
        doc_type = "formulario"
        categoria = "Gestión Documental"
        
    return {
        "document_type": doc_type,
        "categoria_sugerida": categoria,
        "prioridad_sugerida": prioridad,
        "texto_completo_extraido": texto_detectado[:1500] if len(texto_detectado) > 20 else f"Archivo de imagen ({mime_type}) cargado para procesamiento.",
        "resumen": f"Documento clasificado preliminarmente como {doc_type.upper()} mediante análisis local de metadatos.",
        "confidence": 0.65,
        "proveedor": "local_fallback",
        "fields": {
            "emisor_o_proveedor": None,
            "cliente_o_receptor": None,
            "identificacion_fiscal_nit": None,
            "numero_documento": None,
            "fecha_emision": datetime.utcnow().strftime("%Y-%m-%d"),
            "monto_total": 0.0,
            "moneda": "COP",
            "codigo_error_detectado": None,
            "observaciones_clave": "Procesado mediante Plan B local (sin conexión a IA externa o cuota consumida)."
        }
    }


def procesar_documento_vision(
    db: Session,
    filename: str,
    file_bytes: bytes,
    mime_type: str,
    cargado_por: str = "cliente",
    id_ticket: Optional[int] = None
) -> models.DocumentoVision:
    """Flujo completo de procesamiento de visión por computador con persistencia, confianza y trazabilidad."""
    valido, mensaje = validar_archivo_vision(filename, file_bytes, mime_type)
    if not valido:
        raise ValueError(mensaje)
        
    codigo, ruta_guardada, sha256 = guardar_archivo_vision(filename, file_bytes)
    
    doc_record = models.DocumentoVision(
        codigo=codigo,
        id_ticket=id_ticket,
        nombre_original=filename,
        mime_type=mime_type,
        tamano_bytes=len(file_bytes),
        sha256=sha256,
        ruta_archivo=ruta_guardada,
        cargado_por=cargado_por,
        estado="PROCESANDO"
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    def _ejecutar():
        analisis = procesar_vision_con_gemini(filename, file_bytes, mime_type)
        plan_b = False
        if not analisis:
            analisis = procesar_vision_fallback_local(filename, file_bytes, mime_type)
            plan_b = True
            
        doc_record.tipo_documento = analisis.get("document_type", "otro")
        doc_record.repositorio = f"repo_{doc_record.tipo_documento}"
        doc_record.texto_extraido = analisis.get("texto_completo_extraido", "")
        doc_record.campos_json = json.dumps(analisis.get("fields", {}), ensure_ascii=False)
        confianza = float(analisis.get("confidence", 0.70))
        doc_record.confianza = confianza
        doc_record.proveedor = analisis.get("proveedor", "desconocido")
        
        # Si la confianza es menor al umbral configurado, requiere revisión humana obligatoria
        if confianza < config.VISION_CONFIDENCE_THRESHOLD:
            doc_record.estado = "PENDIENTE_REVISION"
        else:
            doc_record.estado = "CONFIRMADO"
            doc_record.campos_confirmados_json = doc_record.campos_json
            
        db.commit()
        db.refresh(doc_record)
        return {
            "ok": True,
            "codigo_vision": doc_record.codigo,
            "tipo": doc_record.tipo_documento,
            "confianza": doc_record.confianza,
            "estado": doc_record.estado,
            "proveedor_ia": doc_record.proveedor,
            "plan_b_utilizado": plan_b
        }

    automation_engine.ejecutar_servicio_con_auditoria(
        db=db,
        flujo="vision_multimodal",
        proceso="extraccion_documental",
        func=_ejecutar,
        usuario=cargado_por,
        id_ticket=id_ticket,
        entrada_resumen=f"Archivo: {filename} ({len(file_bytes)} bytes, {mime_type})"
    )
    
    db.refresh(doc_record)
    return doc_record
