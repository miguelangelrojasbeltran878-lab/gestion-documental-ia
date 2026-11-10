import os

main_path = r'c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\03_Desarrollo\app\main.py'
with open(main_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check imports
if 'from app import auth' not in content:
    content = content.replace(
        'from app import models, schemas, crud, ai_module, make_batch_router',
        'from app import models, schemas, crud, ai_module, make_batch_router, auth, automation_engine, vision_service, config'
    )

# Add login POST, logout and protected routes check
login_routes = '''
# -------------------------------------------------------------
# RUTAS DE AUTENTICACIÓN Y SESIÓN (COMPONENTE TRANSVERSAL DE SEGURIDAD)
# -------------------------------------------------------------

@app.post("/login", response_class=HTMLResponse)
def post_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Autentica agentes y administradores con hash PBKDF2 y cookie de sesión firmada."""
    agente = db.query(models.UsuarioAgente).filter(models.UsuarioAgente.correo_electronico == email.strip().lower()).first()
    if not agente or not agente.password_hash or not auth.verify_password(password, agente.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={"error_login": "Credenciales inválidas. Verifique su correo y contraseña."},
            status_code=401
        )
    
    agente.ultimo_acceso = datetime.utcnow()
    db.commit()
    
    token = auth.create_session_token({"id_agente": agente.id_agente, "email": agente.correo_electronico, "rol": agente.rol})
    response = RedirectResponse(url="/agente/tickets", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=auth.COOKIE_NAME,
        value=token,
        max_age=auth.MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False  # en producción con HTTPS se establece en True
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
def page_vision(request: Request, db: Session = Depends(get_db)):
    """Portal interactivo de visión por computador para fotos tomadas con celular o documentos escaneados."""
    documentos = db.query(models.DocumentoVision).order_by(models.DocumentoVision.fecha_carga.desc()).all()
    user = auth.get_current_user(request, db)
    return templates.TemplateResponse(
        request=request,
        name="vision.html",
        context={"documentos": documentos, "usuario_actual": user}
    )


@app.post("/api/v1/vision/procesar", tags=["Visión por Computador"])
async def api_procesar_vision(
    archivo: UploadFile = File(...),
    id_ticket: Optional[int] = Form(None),
    cargado_por: Optional[str] = Form("cliente_web"),
    db: Session = Depends(get_db)
):
    """Recibe fotografía/documento escaneado, extrae entidades con Gemini Multimodal / OCR local y devuelve JSON estructurado con confianza."""
    file_bytes = await archivo.read()
    mime = archivo.content_type or "image/jpeg"
    try:
        doc = vision_service.procesar_documento_vision(
            db=db,
            filename=archivo.filename,
            file_bytes=file_bytes,
            mime_type=mime,
            cargado_por=cargado_por,
            id_ticket=id_ticket
        )
        return {
            "ok": True,
            "codigo": doc.codigo,
            "tipo_documento": doc.tipo_documento,
            "confianza": doc.confianza,
            "estado": doc.estado,
            "campos": json.loads(doc.campos_json) if doc.campos_json else {},
            "resumen": doc.texto_extraido[:300] if doc.texto_extraido else "",
            "proveedor": doc.proveedor
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/vision/{codigo}/confirmar", tags=["Visión por Computador"])
def api_confirmar_vision(
    codigo: str,
    datos_confirmados: dict,
    request: Request,
    db: Session = Depends(get_db)
):
    """Permite al agente o usuario confirmar o corregir los campos extraídos tras la revisión humana."""
    doc = db.query(models.DocumentoVision).filter(models.DocumentoVision.codigo == codigo).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    
    user = auth.get_current_user(request, db)
    doc.campos_confirmados_json = json.dumps(datos_confirmados, ensure_ascii=False)
    doc.estado = "CONFIRMADO"
    doc.revisado_por = user.correo_electronico if user else "usuario_verificado"
    doc.fecha_revision = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    return {"ok": True, "codigo": doc.codigo, "estado": doc.estado}
'''

if 'post_login' not in content:
    content = content.replace(
        '@app.get("/", response_class=HTMLResponse)',
        login_routes + '\n@app.get("/", response_class=HTMLResponse)'
    )
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Main.py updated with login, logout and vision API routes!")
else:
    print("Routes already present in main.py.")
