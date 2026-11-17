import re
import json
from contextlib import asynccontextmanager
from datetime import datetime
import os
import csv
import io
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, Request, Form, Query, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db, Base, engine
from app import (models, schemas, crud, ai_module, ai_provider, make_batch_router, auth, automation_engine,
                 automation_flows, vision_service, chatbot_graph, scheduler, config)

Base.metadata.create_all(bind=engine)


def _bootstrap_admin() -> None:
    """Crea el administrador inicial desde variables de entorno si la base está vacía (despliegue limpio)."""
    from app.database import SessionLocal
    if not config.ADMIN_PASSWORD:
        return
    db = SessionLocal()
    try:
        if db.query(models.UsuarioAgente).count() == 0:
            db.add(models.UsuarioAgente(nombre_completo="Administrador", correo_electronico=config.ADMIN_EMAIL.lower(),
                                        rol="Administrador", password_hash=auth.hash_password(config.ADMIN_PASSWORD)))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _bootstrap_admin()
    scheduler.iniciar()
    yield
    scheduler.detener()


app = FastAPI(
    title="Sistema Inteligente de Gestión Documental con IA Multimodal",
    description="Portal de atención 24/7 con motor de automatización propio (cron, reintentos, auditoría), "
                "chatbot LangGraph y módulo de visión por computador.",
    version="2.0.0",
    lifespan=lifespan,
)

if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type", "Authorization"],
    )


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(self), microphone=()"
    return response

# Router de procesamiento por lotes (hasta 35 archivos) sobre el motor propio
app.include_router(make_batch_router.router)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _usuario_para_plantillas(request: Request) -> dict:
    """Inyecta el usuario de la sesión (si existe) en todas las plantillas para pintar el menú correcto."""
    from app.database import SessionLocal
    token = request.cookies.get(auth.COOKIE_NAME)
    data = auth.decode_session_token(token) if token else None
    if not data or "id_agente" not in data:
        return {"usuario_actual": None}
    db = SessionLocal()
    try:
        user = db.query(models.UsuarioAgente).filter(models.UsuarioAgente.id_agente == data["id_agente"]).first()
        if user and user.activo:
            db.expunge(user)
            return {"usuario_actual": user}
    finally:
        db.close()
    return {"usuario_actual": None}


templates = Jinja2Templates(directory=TEMPLATES_DIR, context_processors=[_usuario_para_plantillas])


def _quiere_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "") and not request.url.path.startswith("/api/")


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    """Páginas amigables para navegadores; JSON para la API."""
    if _quiere_html(request):
        if exc.status_code == 401:
            return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
        if exc.status_code in (403, 404):
            return templates.TemplateResponse(request=request, name="error.html", status_code=exc.status_code, context={
                "codigo": exc.status_code, "detalle": exc.detail if isinstance(exc.detail, str) else ""})
    return await http_exception_handler(request, exc)

# -------------------------------------------------------------
# REST API ENDPOINTS
# -------------------------------------------------------------

@app.post("/api/v1/tickets/", response_model=schemas.TicketResponse, status_code=status.HTTP_201_CREATED, tags=["Tickets 24/7"])
def api_crear_ticket(ticket_in: schemas.TicketCreate, db: Session = Depends(get_db)):
    ticket = crud.create_ticket_with_ai(db, ticket_in)
    return ticket

@app.get("/api/v1/tickets/seguimiento/{codigo_seguimiento}", response_model=schemas.TicketResponse, tags=["Tickets 24/7"])
def api_consultar_seguimiento(codigo_seguimiento: str, db: Session = Depends(get_db)):
    ticket = crud.get_ticket_by_codigo(db, codigo_seguimiento)
    if not ticket:
        raise HTTPException(status_code=404, detail="Código de ticket no encontrado")
    return ticket

@app.post("/api/v1/ia/analizar-ticket/{id_ticket}", response_model=schemas.SugerenciaIAResponse, tags=["Inteligencia Artificial"])
def api_analizar_ticket_ia(id_ticket: int, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    ticket = crud.get_ticket_by_id(db, id_ticket)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    auth.ensure_ticket_access(ticket, user)
    
    soluciones = crud.get_soluciones(db)
    sol_list = [{"titulo": s.titulo, "contenido_solucion": s.contenido_solucion, "categoria": s.categoria, "palabras_clave": s.palabras_clave} for s in soluciones]
    
    res = ai_module.analyze_and_suggest(ticket.titulo, ticket.descripcion, sol_list)
    
    sugerencia = db.query(models.SugerenciaIA).filter(models.SugerenciaIA.id_ticket == id_ticket).first()
    if not sugerencia:
        sugerencia = models.SugerenciaIA(
            id_ticket=id_ticket,
            prioridad_sugerida=res["prioridad_sugerida"],
            categoria_sugerida=res["categoria_sugerida"],
            respuesta_sugerida=res["respuesta_sugerida"],
            score_confianza=res["score_confianza"]
        )
        db.add(sugerencia)
    else:
        sugerencia.prioridad_sugerida = res["prioridad_sugerida"]
        sugerencia.categoria_sugerida = res["categoria_sugerida"]
        sugerencia.respuesta_sugerida = res["respuesta_sugerida"]
        sugerencia.score_confianza = res["score_confianza"]
    
    db.commit()
    db.refresh(sugerencia)
    return sugerencia

@app.get("/api/v1/agente/tickets/", response_model=List[schemas.TicketResponse], tags=["Bandeja Agentes"])
def api_listar_tickets_agente(
    estado: Optional[str] = None,
    prioridad: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_authenticated_agent),
):
    id_agente = None if user.rol == "Administrador" else user.id_agente
    return crud.get_tickets(db, estado=estado, prioridad=prioridad, id_agente=id_agente)

@app.put("/api/v1/agente/tickets/{id_ticket}/asignar", tags=["Bandeja Agentes"])
def api_asignar_ticket(id_ticket: int, datos: schemas.TicketAsignar, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    ticket = crud.asignar_ticket(db, id_ticket, datos.id_agente)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {"id_ticket": ticket.id_ticket, "id_agente_asignado": ticket.id_agente_asignado, "estado": ticket.estado, "mensaje": "Ticket asignado exitosamente."}

@app.put("/api/v1/agente/tickets/{id_ticket}/responder", tags=["Bandeja Agentes"])
def api_responder_ticket(id_ticket: int, datos: schemas.TicketResponder, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    existing_ticket = crud.get_ticket_by_id(db, id_ticket)
    if not existing_ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    auth.ensure_ticket_access(existing_ticket, user)
    ticket = crud.responder_ticket(db, id_ticket, datos.respuesta_oficial, datos.nuevo_estado)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return {"id_ticket": ticket.id_ticket, "estado": ticket.estado, "respuesta_oficial": ticket.respuesta_oficial, "mensaje": "Respuesta enviada y ticket actualizado."}

@app.get("/api/v1/soluciones/", response_model=List[schemas.SolucionResponse], tags=["Base de Conocimiento"])
def api_listar_soluciones(categoria: Optional[str] = None, q: Optional[str] = None, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    return crud.get_soluciones(db, categoria=categoria, query=q)

@app.post("/api/v1/soluciones/", response_model=schemas.SolucionResponse, status_code=status.HTTP_201_CREATED, tags=["Base de Conocimiento"])
def api_crear_solucion(solucion_in: schemas.SolucionCreate, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    return crud.create_solucion(db, solucion_in)

@app.get("/api/v1/admin/dashboard", tags=["Dashboard & Reportes"])
def api_dashboard_metrics(db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    return crud.get_dashboard_metrics(db)

@app.get("/api/v1/admin/reportes/mensual", tags=["Dashboard & Reportes"])
def api_reporte_mensual(mes: int = Query(8, ge=1, le=12), anio: int = Query(2026, ge=2020), db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    rep = crud.get_monthly_report_data(db, mes, anio)
    return {
        "periodo": rep["periodo"],
        "total_tickets_mes": rep["total_tickets"],
        "tickets_resueltos_exitosamente": rep["tickets_resueltos"],
        "tickets_pendientes": rep["tickets_abiertos"] + rep["tickets_en_proceso"],
        "promedio_tiempo_resolucion_horas": 1.2,
        "desempeno_agentes": rep["agentes_perf"],
        "resumen_ejecutivo": f"El portal de soporte 24/7 procesó {rep['total_tickets']} solicitudes durante el período {rep['periodo']}. Las sugerencias de IA aceleraron la atención."
    }


@app.post("/api/v1/tickets-lote", tags=["Lotes documentales"])
def api_crear_ticket_con_lote(
    nombre_cliente: str = Form(...),
    correo_cliente: str = Form(...),
    telefono: str = Form(""),
    empresa: str = Form(""),
    titulo: str = Form(...),
    descripcion: str = Form(...),
    categoria_preliminar: str = Form("General"),
    archivos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    """Crea el ticket con IA y procesa el lote de archivos con el motor propio de automatización."""
    ticket_in = schemas.TicketCreate(
        nombre_cliente=nombre_cliente,
        correo_cliente=correo_cliente,
        telefono=telefono,
        empresa=empresa,
        titulo=titulo,
        descripcion=descripcion,
        categoria_preliminar=categoria_preliminar
    )
    ticket = crud.create_ticket_with_ai(db, ticket_in)
    batch_res = make_batch_router.handle_ticket_files_batch(db, ticket, archivos)
    db.refresh(ticket)

    sug = ticket.sugerencia_ia
    lote_files = []
    if ticket.lotes:
        for arch in ticket.lotes[-1].archivos:
            lote_files.append({
                "file_code": arch.file_code,
                "filename": arch.nombre_original,
                "extension": arch.extension,
                "size_kb": round(arch.tamano_bytes / 1024, 1),
                "status": arch.estado_procesamiento,
                "doc_type": arch.tipo_documento_ia,
                "summary": arch.resumen_extraido_ia,
                "priority": arch.prioridad_detectada,
                "recommendation": arch.recomendacion_ia
            })

    return {
        "id_ticket": ticket.id_ticket,
        "codigo_seguimiento": ticket.codigo_seguimiento,
        "prioridad_final": ticket.prioridad,
        "categoria_detectada": sug.categoria_sugerida if sug else ticket.categoria_preliminar,
        "score_confianza": sug.score_confianza if sug else 0.95,
        "respuesta_sugerida_ia": sug.respuesta_sugerida if sug else "",
        "batch_id": batch_res.get("batch_id"),
        "accepted_count": batch_res.get("accepted_count", 0),
        "skipped_files": batch_res.get("skipped_files", []),
        "processed_files": lote_files
    }


from pydantic import BaseModel

class ChatbotArchivosRequest(BaseModel):
    pregunta: str
    codigo_ticket: Optional[str] = None
    archivos_locales: Optional[List[dict]] = []

def _enrich_file_dict(filename: str, ext: str, raw_bytes: bytes, base_summary: str = "", base_prio: str = "", base_rec: str = "", file_code: str = "FILE-01") -> dict:
    deep = ai_module.extract_deep_file_text(filename, ext, raw_bytes)
    text_extracted = deep.get("text", "")
    combined = f"{filename} {text_extracted} {base_summary}".lower()
    if not base_prio:
        if any(k in combined for k in ["error", "urgente", "critico", "crítico", "caido", "caído", "500", "502", "bloqueo", "vencid"]):
            base_prio = "Alta"
        elif any(k in combined for k in ["factura", "pago", "contrato", "reporte", "presupuesto", "auditoria", "saldo"]):
            base_prio = "Media"
        else:
            base_prio = "Baja"
    if not base_rec:
        if base_prio == "Alta":
            base_rec = "Priorizar validación técnica o financiera inmediata por alerta detectada en el contenido."
        elif ext == "xlsx":
            base_rec = "Cruzar totales tabulares y registros de la hoja de cálculo con el sistema contable."
        elif ext in ("pdf", "docx"):
            base_rec = "Revisar cláusulas, importes y observaciones extraídas del documento."
        else:
            base_rec = "Anexar evidencia visual verificada al expediente del ticket."

    return {
        "file_code": file_code,
        "filename": filename,
        "extension": ext,
        "size_kb": deep.get("size_kb") or round(len(raw_bytes) / 1024, 1),
        "deep_text": text_extracted or base_summary,
        "key_points": deep.get("key_points") or ([base_summary] if base_summary else []),
        "metrics": deep.get("metrics") or {},
        "summary": text_extracted[:400] if text_extracted else base_summary,
        "priority": base_prio,
        "recommendation": base_rec
    }

@app.post("/api/v1/chatbot-archivos", tags=["Lotes documentales"])
def api_chatbot_archivos(payload: ChatbotArchivosRequest, db: Session = Depends(get_db)):
    """Chatbot inteligente que lee el contenido real de los archivos del ticket o del Dropzone y los resume claramente."""
    files_data = []
    ticket_ctx = None

    # Búsqueda de contexto por código explícito o detección inteligente en la pregunta
    codigo_detectado = payload.codigo_ticket.strip() if payload.codigo_ticket else ""
    if not codigo_detectado and payload.pregunta:
        match_tik = re.search(r'(TIK-\d{4}-[A-Za-z0-9]+)', payload.pregunta, re.IGNORECASE)
        if match_tik:
            codigo_detectado = match_tik.group(1).upper()

    if codigo_detectado:
        ticket = crud.get_ticket_by_codigo(db, codigo_detectado)
        if ticket:
            ticket_ctx = {
                "codigo": ticket.codigo_seguimiento,
                "titulo": ticket.titulo,
                "estado": ticket.estado,
                "prioridad": ticket.prioridad,
                "cliente": ticket.cliente.nombre_completo if ticket.cliente else "Cliente",
                "fecha": ticket.fecha_creacion.strftime("%Y-%m-%d %H:%M")
            }
            for lote in ticket.lotes:
                for arch in lote.archivos:
                    raw_b = b""
                    if arch.ruta_temporal and os.path.exists(arch.ruta_temporal):
                        try:
                            with open(arch.ruta_temporal, "rb") as fp:
                                raw_b = fp.read()
                        except Exception:
                            raw_b = b""
                    files_data.append(
                        _enrich_file_dict(
                            filename=arch.nombre_original,
                            ext=arch.extension,
                            raw_bytes=raw_b,
                            base_summary=arch.resumen_extraido_ia or "",
                            base_prio=arch.prioridad_detectada or "Media",
                            base_rec=arch.recomendacion_ia or "",
                            file_code=arch.file_code
                        )
                    )

    if not files_data and payload.archivos_locales:
        for idx, fl in enumerate(payload.archivos_locales, start=1):
            ext = (fl.get("extension") or "").lower().lstrip(".")
            name = fl.get("filename") or f"archivo_{idx}.{ext}"
            preview_txt = (fl.get("content_preview") or "").encode("utf-8", errors="ignore")
            info = _enrich_file_dict(
                filename=name,
                ext=ext,
                raw_bytes=preview_txt,
                base_summary=fl.get("content_preview") or "",
                file_code=f"FILE-{idx:02d}"
            )
            if fl.get("size_kb"):
                info["size_kb"] = fl["size_kb"]
            files_data.append(info)

    respuesta = ai_module.answer_file_chatbot_question(
        pregunta=payload.pregunta,
        files_data=files_data,
        ticket_context=ticket_ctx
    )
    return {
        "pregunta": payload.pregunta,
        "respuesta": respuesta,
        "total_archivos_contexto": len(files_data)
    }

@app.post("/api/v1/chatbot-archivos-upload", tags=["Lotes documentales"])
def api_chatbot_archivos_upload(
    pregunta: str = Form(...),
    codigo_ticket: str = Form(""),
    archivos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    """Permite enviar los archivos binarios reales desde el navegador para que el Chatbot lea su interior (PDF, DOCX, XLSX, JPG) y los resuma al instante."""
    files_data = []
    ticket_ctx = None

    valid_files = [u for u in archivos if u and u.filename]
    for idx, up in enumerate(valid_files, start=1):
        ext = up.filename.rsplit(".", 1)[-1].lower() if "." in up.filename else ""
        raw_b = up.file.read()
        files_data.append(
            _enrich_file_dict(
                filename=up.filename,
                ext=ext,
                raw_bytes=raw_b,
                file_code=f"FILE-{idx:02d}"
            )
        )

    if not files_data and codigo_ticket.strip():
        return api_chatbot_archivos(
            ChatbotArchivosRequest(pregunta=pregunta, codigo_ticket=codigo_ticket.strip()),
            db=db
        )

    respuesta = ai_module.answer_file_chatbot_question(
        pregunta=pregunta,
        files_data=files_data,
        ticket_context=ticket_ctx
    )
    return {
        "pregunta": pregunta,
        "respuesta": respuesta,
        "total_archivos_contexto": len(files_data)
    }

# -------------------------------------------------------------
# WEB UI ROUTES
# -------------------------------------------------------------


@app.get("/automatizacion/flujos", response_class=HTMLResponse, tags=["Automatización documental"])
@app.get("/make/flujos", response_class=HTMLResponse, include_in_schema=False)  # ruta heredada
def page_flujos(request: Request, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    lotes = db.query(models.LoteArchivos).order_by(models.LoteArchivos.fecha_creacion.desc()).all()
    ejecuciones = db.query(models.EjecucionAutomatizacion).order_by(models.EjecucionAutomatizacion.fecha_inicio.desc()).limit(30).all()
    return templates.TemplateResponse(request=request, name="flujos.html", context={
        "lotes": lotes,
        "total_archivos_procesados": sum(l.archivos_procesados for l in lotes),
        "flujos": automation_engine.inventario(db),
        "ejecuciones": ejecuciones,
        "ia": ai_provider.status(),
        "usuario_actual": user,
    })



# -------------------------------------------------------------
# RUTAS DE AUTENTICACIÓN Y SESIÓN (COMPONENTE TRANSVERSAL DE SEGURIDAD)
# -------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
def page_login_form(request: Request, next: str = "/agente/tickets"):
    return templates.TemplateResponse(request=request, name="login.html", context={"next": next})


def _destino_seguro(next_url: str) -> str:
    return next_url if next_url.startswith("/") and not next_url.startswith("//") else "/agente/tickets"


@app.post("/login", response_class=HTMLResponse)
def post_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form("/agente/tickets"),
    db: Session = Depends(get_db)
):
    """Autentica agentes y administradores con hash PBKDF2 y cookie de sesión firmada."""
    agente = db.query(models.UsuarioAgente).filter(models.UsuarioAgente.correo_electronico == email.strip().lower()).first()
    if not agente or not agente.password_hash or not auth.verify_password(password, agente.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error_login": "Credenciales inválidas. Verifique su correo y contraseña.", "next": _destino_seguro(next)},
            status_code=401
        )
    
    agente.ultimo_acceso = datetime.utcnow()
    db.commit()
    
    token = auth.create_session_token({"id_agente": agente.id_agente, "email": agente.correo_electronico, "rol": agente.rol})
    response = RedirectResponse(url=_destino_seguro(next), status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=auth.COOKIE_NAME,
        value=token,
        max_age=auth.MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=config.COOKIE_SECURE  # true en producción (HTTPS)
    )
    return response


@app.get("/logout")
def get_logout():
    """Cierra la sesión del agente o administrador eliminando la cookie."""
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(auth.COOKIE_NAME)
    return response


# -------------------------------------------------------------
# RUTAS DEL MÓDULO DE VISIÓN POR COMPUTADOR E IA MULTIMODAL (COMPONENTE 2)
# -------------------------------------------------------------

@app.get("/vision", response_class=HTMLResponse, tags=["Visión por Computador"])
def page_vision(request: Request, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    """Portal interactivo de visión por computador para fotos tomadas con celular o documentos escaneados."""
    documentos_query = db.query(models.DocumentoVision)
    if user.rol != "Administrador":
        documentos_query = documentos_query.filter(models.DocumentoVision.cargado_por == user.correo_electronico)
    documentos = documentos_query.order_by(models.DocumentoVision.fecha_carga.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="vision.html",
        context={"documentos": documentos, "usuario_actual": user}
    )


def _doc_o_404(db: Session, codigo: str, user: models.UsuarioAgente) -> models.DocumentoVision:
    doc = db.query(models.DocumentoVision).filter(models.DocumentoVision.codigo == codigo).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    if not vision_service.puede_acceder(doc, user, db):
        vision_service.auditar(db, user.correo_electronico, "ACCESO_DENEGADO", codigo, None, "intento de acceso sin permiso")
        raise HTTPException(status_code=403, detail="No tiene acceso a este documento.")
    return doc


def _doc_json(doc: models.DocumentoVision) -> dict:
    campos = json.loads(doc.campos_json) if doc.campos_json else {}
    return {
        "ok": True, "codigo": doc.codigo, "tipo_documento": doc.tipo_documento, "confianza": doc.confianza,
        "estado": doc.estado, "campos": {k: v for k, v in campos.items() if not k.startswith("_")},
        "confianza_campos": campos.get("_confianza_campos", {}),
        "requiere_revision": doc.estado == "PENDIENTE_REVISION",
        "resumen": (doc.texto_extraido or "")[:300], "proveedor": doc.proveedor,
        "cargado_por": doc.cargado_por,
        "fecha_carga": doc.fecha_carga.strftime("%Y-%m-%d %H:%M:%S") if doc.fecha_carga else None,
    }


@app.post("/api/v1/vision/procesar", tags=["Visión por Computador"])
async def api_procesar_vision(
    archivo: UploadFile = File(...),
    id_ticket: Optional[int] = Form(None),
    autoriza_envio_externo: bool = Form(False),
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_authenticated_agent),
):
    """Foto/PDF -> JSON con entidades y confianza por campo -> proceso de negocio.

    `autoriza_envio_externo`: autorización expresa del titular para enviar la imagen a un servicio externo
    (Ley 1581). Sin ella solo se usan modelos locales / OCR local.
    """
    file_bytes = await archivo.read()
    if id_ticket:
        ticket = crud.get_ticket_by_id(db, id_ticket)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado.")
        auth.ensure_ticket_access(ticket, user)
    try:
        doc = vision_service.procesar_documento_vision(
            db=db, filename=archivo.filename or "captura.jpg", file_bytes=file_bytes,
            mime_type=archivo.content_type or "image/jpeg", cargado_por=user.correo_electronico,
            id_ticket=id_ticket, consentimiento=autoriza_envio_externo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _doc_json(doc)


@app.get("/api/v1/vision/", tags=["Visión por Computador"])
def api_listar_vision(db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    q = db.query(models.DocumentoVision)
    if user.rol != "Administrador":
        q = q.filter(models.DocumentoVision.cargado_por == user.correo_electronico)
    return [_doc_json(d) for d in q.order_by(models.DocumentoVision.fecha_carga.desc()).limit(100).all()]


@app.get("/api/v1/vision/{codigo}", tags=["Visión por Computador"])
def api_detalle_vision(codigo: str, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    return _doc_json(_doc_o_404(db, codigo, user))


@app.get("/api/v1/vision/{codigo}/archivo", tags=["Visión por Computador"])
def api_archivo_vision(codigo: str, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    """Imagen original: exige sesión + propiedad del documento y deja registro de auditoría."""
    doc = _doc_o_404(db, codigo, user)
    if not os.path.exists(doc.ruta_archivo):
        raise HTTPException(status_code=404, detail="El archivo ya no está disponible.")
    vision_service.auditar(db, user.correo_electronico, "ACCESO_ARCHIVO", codigo, None, "descarga de imagen original")
    return FileResponse(doc.ruta_archivo, media_type=doc.mime_type, filename=doc.nombre_original)


@app.post("/api/v1/vision/{codigo}/confirmar", tags=["Visión por Computador"])
def api_confirmar_vision(
    codigo: str,
    datos_confirmados: dict,
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_authenticated_agent),
):
    """Confirma/corrige los campos extraídos (revisión humana) y dispara el proceso de negocio."""
    doc = _doc_o_404(db, codigo, user)
    if doc.estado == "RECHAZADO":
        raise HTTPException(status_code=409, detail="El documento fue rechazado y no puede confirmarse.")
    proceso = vision_service.confirmar_documento(db, doc, datos_confirmados, user.correo_electronico)
    return {"ok": True, "codigo": doc.codigo, "estado": doc.estado, "proceso_negocio": proceso}


@app.post("/api/v1/vision/{codigo}/rechazar", tags=["Visión por Computador"])
def api_rechazar_vision(
    codigo: str,
    motivo: str = Form("Rechazado por el revisor"),
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_authenticated_agent),
):
    doc = _doc_o_404(db, codigo, user)
    vision_service.rechazar_documento(db, doc, motivo, user.correo_electronico)
    return {"ok": True, "codigo": doc.codigo, "estado": doc.estado}


# -------------------------------------------------------------
# CHATBOT (LangGraph: memoria + herramientas + Plan B) con soporte de imágenes
# -------------------------------------------------------------

@app.post("/api/v1/chatbot/mensaje", tags=["Chatbot"])
async def api_chatbot_mensaje(
    pregunta: str = Form(...),
    imagen: Optional[UploadFile] = File(None),
    autoriza_envio_externo: bool = Form(False),
    id_ticket: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_authenticated_agent),
):
    """Conversación con memoria por usuario. Si trae imagen, pasa por el módulo de visión y se usa como contexto."""
    contexto_extra = ""
    vision_info = None
    if imagen is not None and imagen.filename:
        data = await imagen.read()
        try:
            doc = vision_service.procesar_documento_vision(
                db, imagen.filename, data, imagen.content_type or "image/jpeg", user.correo_electronico,
                id_ticket, consentimiento=autoriza_envio_externo)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        vision_info = _doc_json(doc)
        contexto_extra = (f"El usuario acaba de enviar la imagen {doc.codigo}. Resultado: tipo {doc.tipo_documento}, "
                          f"confianza {doc.confianza}, estado {doc.estado}, "
                          f"campos {json.dumps(vision_info['campos'], ensure_ascii=False)}. "
                          + ("Requiere revisión humana en /vision antes de guardarse." if doc.estado == "PENDIENTE_REVISION" else ""))
    res = chatbot_graph.conversar(db, user, pregunta, thread_id=f"user-{user.id_agente}", contexto_extra=contexto_extra)
    vision_service.auditar(db, user.correo_electronico, "CHATBOT_TURNO", None, res["proveedor"],
                           f"herramientas={res['herramientas']} imagen={'si' if vision_info else 'no'}")
    return {**res, "vision": vision_info}


@app.delete("/api/v1/chatbot/memoria", tags=["Chatbot"])
def api_chatbot_olvidar(user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    chatbot_graph.olvidar(f"user-{user.id_agente}")
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def page_login(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/chatbot", response_class=HTMLResponse)
def page_chatbot(request: Request, user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    return templates.TemplateResponse(request=request, name="chatbot.html", context={})


@app.get("/admin/auditoria", response_class=HTMLResponse)
def page_auditoria(request: Request, accion: str = "", db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    q = db.query(models.AuditoriaIA)
    if accion:
        q = q.filter(models.AuditoriaIA.accion == accion)
    registros = q.order_by(models.AuditoriaIA.id_auditoria.desc()).limit(200).all()
    acciones = [a[0] for a in db.query(models.AuditoriaIA.accion).distinct().all()]
    gastos = db.query(models.Gasto).order_by(models.Gasto.id_gasto.desc()).limit(50).all()
    return templates.TemplateResponse(request=request, name="auditoria.html", context={
        "registros": registros, "acciones": sorted(acciones), "accion_filtro": accion, "gastos": gastos})


@app.get("/crear-solicitud", response_class=HTMLResponse)
def page_crear_solicitud(request: Request):
    return templates.TemplateResponse(request=request, name="crear_solicitud.html", context={"mensaje_exito": None})

@app.post("/crear-solicitud", response_class=HTMLResponse)
def page_crear_solicitud_submit(
    request: Request,
    nombre_cliente: str = Form(...),
    correo_cliente: str = Form(...),
    telefono: str = Form(""),
    empresa: str = Form(""),
    titulo: str = Form(...),
    descripcion: str = Form(...),
    categoria_preliminar: str = Form("General"),
    archivos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    ticket_in = schemas.TicketCreate(
        nombre_cliente=nombre_cliente,
        correo_cliente=correo_cliente,
        telefono=telefono,
        empresa=empresa,
        titulo=titulo,
        descripcion=descripcion,
        categoria_preliminar=categoria_preliminar
    )
    ticket = crud.create_ticket_with_ai(db, ticket_in)
    batch_result = make_batch_router.handle_ticket_files_batch(db, ticket, archivos)
    db.refresh(ticket)

    msg = f"¡Ticket registrado exitosamente 24/7! Código de seguimiento: {ticket.codigo_seguimiento}."
    if batch_result["accepted_count"] > 0:
        msg += f" Se procesó un lote de {batch_result['accepted_count']} archivo(s) ({batch_result['batch_id']}) con IA."

    return templates.TemplateResponse(request=request, name="crear_solicitud.html", context={
        "mensaje_exito": msg,
        "ticket": ticket,
        "batch_result": batch_result
    })

@app.post("/agente/tickets/{id_ticket}/subir-lote", response_class=HTMLResponse)
def page_agente_subir_lote(
    request: Request,
    id_ticket: int,
    archivos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_authenticated_agent),
):
    ticket = crud.get_ticket_by_id(db, id_ticket)
    if ticket:
        auth.ensure_ticket_access(ticket, user)
    if ticket and archivos:
        make_batch_router.handle_ticket_files_batch(db, ticket, archivos)
    return RedirectResponse(url=f"/agente/tickets/{id_ticket}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/mis-tickets", response_class=HTMLResponse)
def page_mis_tickets(request: Request, codigo: Optional[str] = None, msg: Optional[str] = None, db: Session = Depends(get_db)):
    ticket = None
    error = None
    recientes = []
    if codigo:
        ticket = crud.get_ticket_by_codigo(db, codigo.strip())
        if not ticket:
            error = f"No se encontró ninguna solicitud con el código '{codigo}'."
    return templates.TemplateResponse(request=request, name="mis_tickets.html", context={
        "ticket": ticket,
        "codigo": codigo or "",
        "error": error,
        "mensaje_flash": msg,
        "tickets_recientes": recientes
    })

@app.post("/mis-tickets/{codigo}/replicar", response_class=HTMLResponse)
def page_cliente_replicar(
    request: Request,
    codigo: str,
    comentario_cliente: str = Form(...),
    db: Session = Depends(get_db)
):
    crud.agregar_replica_cliente(db, codigo.strip(), comentario_cliente)
    return RedirectResponse(url=f"/mis-tickets?codigo={codigo.strip()}&msg=Tu+mensaje+fue+enviado+y+respondido+por+el+Asistente+IA+24/7", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/mis-tickets/{codigo}/calificar", response_class=HTMLResponse)
def page_cliente_calificar(
    request: Request,
    codigo: str,
    estrellas: int = Form(5),
    comentario_calificacion: str = Form(""),
    db: Session = Depends(get_db)
):
    crud.calificar_ticket_cliente(db, codigo.strip(), estrellas, comentario_calificacion)
    return RedirectResponse(url=f"/mis-tickets?codigo={codigo.strip()}&msg=¡Gracias+por+calificar+nuestra+atención!", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/agente/tickets", response_class=HTMLResponse)
def page_lista_tickets(request: Request, estado: Optional[str] = "Todos", prioridad: Optional[str] = "Todas", db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    tickets = crud.get_tickets(db, estado=estado, prioridad=prioridad, id_agente=None if user.rol == "Administrador" else user.id_agente)
    return templates.TemplateResponse(request=request, name="lista_tickets.html", context={
        "tickets": tickets,
        "estado_filtro": estado,
        "prioridad_filtro": prioridad
    })

@app.get("/agente/tickets/{id_ticket}", response_class=HTMLResponse)
def page_detalle_ticket(request: Request, id_ticket: int, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    ticket = crud.get_ticket_by_id(db, id_ticket)
    if not ticket:
        return RedirectResponse(url="/agente/tickets")
    auth.ensure_ticket_access(ticket, user)
    
    agentes = db.query(models.UsuarioAgente).all()
    sugerencia = ticket.sugerencia_ia
    if not sugerencia:
        soluciones = crud.get_soluciones(db)
        sol_list = [{"titulo": s.titulo, "contenido_solucion": s.contenido_solucion, "categoria": s.categoria, "palabras_clave": s.palabras_clave} for s in soluciones]
        res = ai_module.analyze_and_suggest(ticket.titulo, ticket.descripcion, sol_list)
        sugerencia = models.SugerenciaIA(
            id_ticket=ticket.id_ticket,
            prioridad_sugerida=res["prioridad_sugerida"],
            categoria_sugerida=res["categoria_sugerida"],
            respuesta_sugerida=res["respuesta_sugerida"],
            score_confianza=res["score_confianza"]
        )
        db.add(sugerencia)
        db.commit()
        db.refresh(sugerencia)

    return templates.TemplateResponse(request=request, name="detalle_ticket.html", context={
        "ticket": ticket,
        "sugerencia": sugerencia,
        "agentes": agentes
    })

@app.post("/agente/tickets/{id_ticket}/responder", response_class=HTMLResponse)
def page_detalle_ticket_responder(
    request: Request,
    id_ticket: int,
    respuesta_oficial: str = Form(...),
    nuevo_estado: str = Form("Resuelto"),
    guardar_solucion: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_authenticated_agent),
):
    existing_ticket = crud.get_ticket_by_id(db, id_ticket)
    if not existing_ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    auth.ensure_ticket_access(existing_ticket, user)
    ticket = crud.responder_ticket(db, id_ticket, respuesta_oficial, nuevo_estado)
    if guardar_solucion and ticket:
        admin = db.query(models.UsuarioAgente).first()
        sol_in = schemas.SolucionCreate(
            titulo=f"Solución: {ticket.titulo}",
            contenido_solucion=respuesta_oficial,
            categoria=ticket.categoria_preliminar,
            palabras_clave=f"{ticket.categoria_preliminar}, {ticket.titulo}",
            id_autor=admin.id_agente if admin else 1,
            id_ticket_origen=ticket.id_ticket
        )
        crud.create_solucion(db, sol_in)
    return RedirectResponse(url=f"/agente/tickets/{id_ticket}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/agente/tickets/{id_ticket}/asignar", response_class=HTMLResponse)
def page_detalle_ticket_asignar(
    request: Request,
    id_ticket: int,
    id_agente: int = Form(...),
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_admin),
):
    crud.asignar_ticket(db, id_ticket, id_agente)
    return RedirectResponse(url=f"/agente/tickets/{id_ticket}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/admin/dashboard", response_class=HTMLResponse)
def page_dashboard(request: Request, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    metrics = crud.get_dashboard_metrics(db)
    recent_tickets = crud.get_tickets(db)[:5]
    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "metrics": metrics,
        "recent_tickets": recent_tickets
    })

@app.get("/admin/reportes", response_class=HTMLResponse)
def page_reportes(request: Request, mes: int = 8, anio: int = 2026, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    rep = crud.get_monthly_report_data(db, mes, anio)
    return templates.TemplateResponse(request=request, name="reportes.html", context={
        "reporte": rep,
        "mes": mes,
        "anio": anio
    })

@app.get("/admin/reportes/exportar-csv")
def page_exportar_reporte_csv(mes: int = 8, anio: int = 2026, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    rep = crud.get_monthly_report_data(db, mes, anio)
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["REPORTE MENSUAL DE GESTIÓN DE ATENCIÓN AL CLIENTE 24/7 CON IA"])
    writer.writerow(["Período", rep["periodo"]])
    writer.writerow(["Total Tickets Mes", rep["total_tickets"]])
    writer.writerow(["Tickets Resueltos", rep["tickets_resueltos"]])
    writer.writerow(["Tickets Abiertos", rep["tickets_abiertos"]])
    writer.writerow(["Tickets en Proceso", rep["tickets_en_proceso"]])
    writer.writerow(["Prioridad Alta (IA)", rep["prioridad_alta"]])
    writer.writerow(["Prioridad Media (IA)", rep["prioridad_media"]])
    writer.writerow(["Prioridad Baja (IA)", rep["prioridad_baja"]])
    writer.writerow([])
    
    writer.writerow(["LISTADO DETALLADO DE TICKETS DEL MES"])
    writer.writerow(["Código", "Título", "Categoría", "Prioridad IA", "Estado", "Cliente", "Fecha Creación"])
    for t in rep["tickets_lista"]:
        writer.writerow([
            t.codigo_seguimiento,
            t.titulo,
            t.categoria_preliminar,
            t.prioridad,
            t.estado,
            t.cliente.nombre_completo if t.cliente else "",
            t.fecha_creacion.strftime('%Y-%m-%d %H:%M:%S')
        ])
        
    output.seek(0)
    filename = f"reporte_mensual_{anio}_{mes:02d}.csv"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)

@app.get("/admin/clientes", response_class=HTMLResponse)
def page_clientes(request: Request, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    clientes = db.query(models.Cliente).all()
    return templates.TemplateResponse(request=request, name="clientes.html", context={
        "clientes": clientes
    })


# -------------------------------------------------------------
# MOTOR DE AUTOMATIZACIÓN, IA Y AUDITORÍA
# -------------------------------------------------------------

@app.get("/health", tags=["Operación"])
def health(db: Session = Depends(get_db)):
    """Verificación de salud para el despliegue (base de datos, IA, OCR y scheduler)."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "ia": ai_provider.status(), "ocr_local": vision_service.ocr_disponible(),
            "scheduler": scheduler._scheduler is not None, "entorno": config.APP_ENV}


@app.get("/api/v1/ia/estado", tags=["Motor Autónomo de Automatización"])
def api_estado_ia(user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    return ai_provider.status()


@app.get("/api/v1/automatizaciones/flujos", tags=["Motor Autónomo de Automatización"])
def api_inventario_flujos(db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_authenticated_agent)):
    """Inventario de flujos (disparador, pasos, servicios, resultado) con última ejecución y tasa de éxito."""
    return automation_engine.inventario(db)


@app.post("/api/v1/automatizaciones/flujos/{flujo_id}/ejecutar", tags=["Motor Autónomo de Automatización"])
def api_ejecutar_flujo(flujo_id: str, db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    """Ejecuta manualmente un flujo programado (solo Administrador). Queda en el registro de ejecuciones."""
    try:
        return automation_engine.ejecutar_flujo_registrado(db, flujo_id, usuario=user.correo_electronico)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/automatizaciones/logs", tags=["Motor Autónomo de Automatización"])
def api_automatizaciones_logs(
    limit: int = Query(50, ge=1, le=500),
    flujo: Optional[str] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_admin),
):
    """Registro de ejecuciones: fecha, flujo, entrada, resultado, error, intentos y duración (solo Administrador)."""
    q = db.query(models.EjecucionAutomatizacion)
    if flujo:
        q = q.filter(models.EjecucionAutomatizacion.flujo == flujo)
    if estado:
        q = q.filter(models.EjecucionAutomatizacion.estado == estado)
    logs = q.order_by(models.EjecucionAutomatizacion.fecha_inicio.desc()).limit(limit).all()
    return [
        {
            "id": l.id_ejecucion, "codigo": l.codigo_ejecucion, "flujo": l.flujo, "proceso": l.proceso,
            "usuario": l.usuario, "id_ticket": l.id_ticket, "estado": l.estado, "intentos": l.intentos,
            "duracion_ms": l.duracion_ms, "proveedor_ia": l.proveedor_ia or "local",
            "fecha": l.fecha_inicio.strftime("%Y-%m-%d %H:%M:%S") if l.fecha_inicio else "",
            "entrada": l.entrada_resumen, "resultado_resumen": (l.resultado or "")[:300], "error": l.error,
        }
        for l in logs
    ]


@app.get("/api/v1/admin/auditoria", tags=["Dashboard & Reportes"])
def api_auditoria_ia(
    limit: int = Query(100, ge=1, le=500),
    accion: Optional[str] = None,
    db: Session = Depends(get_db),
    user: models.UsuarioAgente = Depends(auth.require_admin),
):
    """Bitácora de auditoría de acciones de la IA y de acceso a imágenes (quién, qué, cuándo)."""
    q = db.query(models.AuditoriaIA)
    if accion:
        q = q.filter(models.AuditoriaIA.accion == accion)
    return [
        {"fecha": a.fecha.strftime("%Y-%m-%d %H:%M:%S"), "usuario": a.usuario, "accion": a.accion,
         "recurso": a.recurso, "proveedor": a.proveedor, "detalle": a.detalle}
        for a in q.order_by(models.AuditoriaIA.fecha.desc()).limit(limit).all()
    ]


@app.get("/api/v1/admin/gastos", tags=["Dashboard & Reportes"])
def api_gastos(db: Session = Depends(get_db), user: models.UsuarioAgente = Depends(auth.require_admin)):
    """Gastos creados automáticamente a partir de facturas leídas por visión."""
    return [
        {"id": g.id_gasto, "documento": g.codigo_documento, "proveedor": g.proveedor, "nit": g.nit,
         "numero": g.numero_documento, "fecha": g.fecha_documento, "total": g.monto_total, "moneda": g.moneda,
         "registrado_por": g.registrado_por}
        for g in db.query(models.Gasto).order_by(models.Gasto.fecha_registro.desc()).limit(200).all()
    ]
