"""Recepción de lotes de archivos (hasta 35) y consulta de su estado.

Antes este módulo orquestaba un escenario externo de Make; ahora el procesamiento lo hace el motor propio
(`automation_flows.procesar_lote_documental`) con reintentos y registro de ejecuciones.
"""
import hmac
import hashlib
import io
import os
import uuid
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from . import models, config, auth, automation_engine
from .database import get_db

router = APIRouter(prefix="/api/v1/lotes", tags=["Lotes documentales"])

UPLOAD_DIR = config.BATCH_DIR
PUBLIC_BASE_URL = config.PUBLIC_BASE_URL

ALLOWED_EXTENSIONS = {"pdf", "xlsx", "docx", "jpg", "jpeg", "png", "webp", "txt", "csv"}
MAX_FILES_PER_BATCH = 35
MAX_FILE_SIZE_MB = 15


def sign_file_token(batch_code: str, file_code: str) -> str:
    payload = f"{batch_code}:{file_code}".encode("utf-8")
    return hmac.new(config.FILE_TOKEN_SECRET.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def extract_office_or_text_content(ext: str, raw_bytes: bytes) -> str:
    """Extrae texto real de archivos .docx, .xlsx (sharedStrings) o texto en .pdf/.jpg."""
    try:
        if ext == "docx":
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                xml_content = zf.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            texts = [node.text for node in tree.iter() if node.tag.endswith("}t") and node.text]
            return " ".join(texts)[:4000]
        elif ext == "xlsx":
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                if "xl/sharedStrings.xml" in zf.namelist():
                    xml_content = zf.read("xl/sharedStrings.xml")
                    tree = ET.fromstring(xml_content)
                    cells = [node.text for node in tree.iter() if node.tag.endswith("}t") and node.text]
                    return " | ".join(cells)[:4000]
        elif ext == "pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw_bytes))
            return " ".join((pg.extract_text() or "") for pg in reader.pages[:10])[:4000]
        elif ext in ("jpg", "jpeg", "png", "webp"):
            return ""  # las imágenes se interpretan en el módulo de visión, no como texto
        return raw_bytes[:4096].decode("utf-8", errors="ignore")
    except Exception:
        return ""


def handle_ticket_files_batch(
    db: Session,
    ticket: models.Ticket,
    archivos: List[UploadFile]
) -> Dict[str, Any]:
    """Recibe el lote de archivos adjuntos (.pdf, .xlsx, .docx, .jpg), los guarda y ejecuta el flujo del motor propio."""
    valid_uploads = [u for u in archivos if u and u.filename and u.filename.strip()]
    if not valid_uploads:
        return {"batch_id": None, "accepted_count": 0, "skipped_files": []}

    if len(valid_uploads) > MAX_FILES_PER_BATCH:
        raise HTTPException(
            status_code=400,
            detail=f"El lote supera el límite de {MAX_FILES_PER_BATCH} archivos por proceso."
        )

    batch_code = f"LOT-2026-{uuid.uuid4().hex[:6].upper()}"
    batch_folder = os.path.join(UPLOAD_DIR, batch_code)
    os.makedirs(batch_folder, exist_ok=True)

    db_lote = models.LoteArchivos(
        batch_code=batch_code,
        id_ticket=ticket.id_ticket,
        estado_make="QUEUED",
        total_archivos=0,
        archivos_procesados=0
    )
    db.add(db_lote)
    db.commit()
    db.refresh(db_lote)

    manifest_files = []
    skipped_files = []

    for idx, upload in enumerate(valid_uploads, start=1):
        ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            skipped_files.append({
                "filename": upload.filename,
                "reason": f"Formato .{ext} no admitido (Se admiten .pdf, .xlsx, .docx, .txt, .csv, .jpg, .png, .webp)"
            })
            continue

        raw_bytes = upload.file.read()
        size_bytes = len(raw_bytes)

        if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
            skipped_files.append({
                "filename": upload.filename,
                "reason": f"Excede tamaño máximo de {MAX_FILE_SIZE_MB} MB"
            })
            continue

        file_code = f"FIL-{idx:03d}"
        stored_name = f"{file_code}.{ext}"
        full_path = os.path.join(batch_folder, stored_name)
        with open(full_path, "wb") as fp:
            fp.write(raw_bytes)

        token = sign_file_token(batch_code, file_code)
        download_url = f"{PUBLIC_BASE_URL}/api/v1/lotes/temp-files/{batch_code}/{stored_name}?token={token}"

        db_arch = models.ArchivoAdjunto(
            id_lote=db_lote.id_lote,
            file_code=file_code,
            nombre_original=upload.filename,
            extension=ext,
            mime_type=upload.content_type or "application/octet-stream",
            tamano_bytes=size_bytes,
            ruta_temporal=full_path,
            estado_procesamiento="PENDING"
        )
        db.add(db_arch)

        manifest_files.append({
            "file_id": file_code,
            "filename": upload.filename,
            "extension": ext,
            "mime_type": upload.content_type or "application/octet-stream",
            "size_bytes": size_bytes,
            "download_url": download_url
        })

    db_lote.total_archivos = len(manifest_files)
    db.commit()

    manifest = {
        "batch_id": batch_code,
        "ticket_id": ticket.id_ticket,
        "codigo_seguimiento": ticket.codigo_seguimiento,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_files": len(manifest_files),
        "files": manifest_files
    }

    if manifest_files:
        from app import automation_flows
        automation_engine.ejecutar_servicio_con_auditoria(
            db=db, flujo="procesamiento_lote", proceso="PROCESAR_LOTE",
            func=lambda: automation_flows.procesar_lote_documental(db, batch_code),
            usuario=ticket.cliente.correo_electronico if ticket.cliente else "sistema",
            id_ticket=ticket.id_ticket, entrada_resumen=f"{batch_code}: {len(manifest_files)} archivo(s)")

    db.refresh(db_lote)
    return {
        "batch_id": batch_code,
        "status": db_lote.estado_make,
        "accepted_count": len(manifest_files),
        "skipped_files": skipped_files,
        "manifest": manifest
    }


@router.post("/procesar", status_code=202)
def api_procesar_lote(
    ticket_id: int = Form(...),
    archivos: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_authenticated_agent),
):
    """Envía un lote de hasta 35 archivos a un ticket existente (solo agentes con acceso al expediente)."""
    ticket = db.query(models.Ticket).filter_by(id_ticket=ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    auth.ensure_ticket_access(ticket, user)
    res = handle_ticket_files_batch(db, ticket, archivos)
    if res["accepted_count"] == 0 and not res["skipped_files"]:
        raise HTTPException(status_code=400, detail="No se adjuntaron archivos válidos.")
    return res


@router.get("/temp-files/{batch_code}/{stored_name}")
def api_descargar_archivo_lote(
    batch_code: str,
    stored_name: str,
    token: str = "",
    user: Optional[models.UsuarioAgente] = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Descarga un archivo del lote: exige sesión con acceso al expediente o un token HMAC válido."""
    if os.path.basename(stored_name) != stored_name or os.path.basename(batch_code) != batch_code:
        raise HTTPException(status_code=400, detail="Nombre de archivo inválido.")
    file_code = stored_name.rsplit(".", 1)[0]
    if token:
        if not hmac.compare_digest(token, sign_file_token(batch_code, file_code)):
            raise HTTPException(status_code=403, detail="Token de descarga inválido.")
    elif not user:
        raise HTTPException(status_code=401, detail="Se requiere iniciar sesión para descargar archivos.")
    else:
        lote = db.query(models.LoteArchivos).filter_by(batch_code=batch_code).first()
        if lote and lote.ticket:
            auth.ensure_ticket_access(lote.ticket, user)
    full_path = os.path.join(UPLOAD_DIR, batch_code, stored_name)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    return FileResponse(full_path, filename=stored_name)


@router.get("/estado/{batch_code}")
def api_consultar_estado_lote(
    batch_code: str,
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_authenticated_agent),
):
    """Estado del lote y análisis individual de sus archivos (agentes con acceso al expediente)."""
    lote = db.query(models.LoteArchivos).filter_by(batch_code=batch_code).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado.")
    if lote.ticket:
        auth.ensure_ticket_access(lote.ticket, user)
    return {
        "batch_id": lote.batch_code,
        "ticket_id": lote.id_ticket,
        "status": lote.estado_make,
        "total_files": lote.total_archivos,
        "processed_files": lote.archivos_procesados,
        "global_summary": lote.sintesis_global_ia,
        "files": [
            {
                "file_id": a.file_code,
                "filename": a.nombre_original,
                "extension": a.extension,
                "size_bytes": a.tamano_bytes,
                "status": a.estado_procesamiento,
                "document_type": a.tipo_documento_ia,
                "extracted_summary": a.resumen_extraido_ia,
                "suggested_priority": a.prioridad_detectada,
                "ai_action_recommendation": a.recomendacion_ia,
                "confidence_score": a.score_confianza,
            }
            for a in lote.archivos
        ],
    }
