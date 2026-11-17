"""Suite de pruebas del sistema de gestión documental con IA.

Convención: ninguna prueba llama a servicios externos; la IA se simula con monkeypatch.
Entorno aislado (BD y carpetas temporales) en conftest.py.
"""
import json
import uuid

import pytest

from app import (ai_provider, auth, automation_engine, automation_flows, chatbot_graph, config, models,
                 privacy, scheduler, vision_service)

LOGIN_AGENTE = {"email": "andres.gomez@empresa.com", "password": "Password123*"}


# ======================================================================= web, sesión y control de acceso

def test_homepage_loads(anonimo):
    r = anonimo.get("/")
    assert r.status_code == 200
    assert "DocuAI" in r.text
    assert "Nueva solicitud" in r.text


def test_login_invalid_credentials(anonimo):
    r = anonimo.post("/login", data={"email": "noexiste@empresa.com", "password": "wrong"})
    assert r.status_code == 401
    assert "Credenciales inválidas" in r.text


def test_login_valid_credentials(anonimo):
    r = anonimo.post("/login", data=LOGIN_AGENTE, follow_redirects=False)
    assert r.status_code == 303
    assert auth.COOKIE_NAME in r.cookies


def test_password_hashing():
    h = auth.hash_password("MiContraseñaSegura123!")
    assert auth.verify_password("MiContraseñaSegura123!", h) is True
    assert auth.verify_password("incorrecta", h) is False


def test_sensitive_pages_require_an_authenticated_agent(anonimo):
    for path in ["/agente/tickets", "/admin/dashboard", "/admin/clientes", "/vision",
                 "/automatizacion/flujos", "/make/flujos"]:
        assert anonimo.get(path, follow_redirects=False).status_code == 401, path


def test_sensitive_api_requires_an_authenticated_agent(anonimo):
    for path in ["/api/v1/agente/tickets/", "/api/v1/admin/dashboard", "/api/v1/soluciones/",
                 "/api/v1/vision/", "/api/v1/automatizaciones/flujos", "/api/v1/automatizaciones/logs",
                 "/api/v1/admin/auditoria", "/api/v1/ia/estado"]:
        assert anonimo.get(path).status_code == 401, path
    assert anonimo.post("/api/v1/chatbot/mensaje", data={"pregunta": "hola"}).status_code == 401
    assert anonimo.post("/api/v1/automatizaciones/flujos/monitor_sla/ejecutar").status_code == 401


def test_admin_only_routes_reject_a_regular_agent(agente):
    assert agente.get("/api/v1/automatizaciones/logs").status_code == 403
    assert agente.get("/api/v1/admin/auditoria").status_code == 403
    assert agente.post("/api/v1/automatizaciones/flujos/monitor_sla/ejecutar").status_code == 403
    assert agente.get("/api/v1/admin/dashboard").status_code == 403


def test_batch_status_and_stored_files_require_authentication(anonimo):
    assert anonimo.get("/api/v1/lotes/estado/LOT-INEXISTENTE").status_code == 401
    assert anonimo.get("/api/v1/lotes/temp-files/LOT-X/FILE-01.pdf").status_code == 401


def test_health_endpoint_is_public(anonimo):
    r = anonimo.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_vision_page_and_flujos_page_render(agente):
    assert "Lectura de facturas y recibos" in agente.get("/vision").text
    pagina = agente.get("/automatizacion/flujos")
    assert pagina.status_code == 200
    assert "Flujos automáticos" in pagina.text


def test_ticket_upload_accepts_png_txt_pdf_and_rejects_exe(anonimo):
    """Regresión: crear un ticket con adjuntos fallaba con 500 (import faltante) y solo aceptaba pocos formatos."""
    png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201a1a5f7650000000049454e44ae426082")
    r = anonimo.post("/api/v1/tickets-lote", data={
        "nombre_cliente": "Ana Prueba", "correo_cliente": "ana@prueba.test",
        "titulo": "Prueba de adjuntos", "descripcion": "Adjunto tres archivos para validar la carga."},
        files=[("archivos", ("f.png", png, "image/png")),
               ("archivos", ("n.txt", b"Factura urgente", "text/plain")),
               ("archivos", ("d.pdf", b"%PDF-1.4\n%%EOF", "application/pdf")),
               ("archivos", ("x.exe", b"MZ", "application/octet-stream"))])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted_count"] == 3
    assert {f["extension"] for f in body["processed_files"]} == {"png", "txt", "pdf"}
    assert any("x.exe" in str(s) for s in body["skipped_files"])


def test_vision_reviewer_can_correct_type_and_create_expense(agente):
    """Si la IA no pudo clasificar, el revisor corrige el tipo y la factura genera el gasto (sin duplicados)."""
    png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cfc0f01f0005000201a1a5f7650000000049454e44ae426082")
    datos = {"tipo_documento": "factura", "emisor_o_proveedor": "Proveedor Test SAS", "identificacion_fiscal_nit": "900999111-1",
             "numero_documento": "FT-777", "fecha_emision": "2026-11-10", "monto_total": 99000}
    codigos = []
    for nombre in ("a.png", "b.png"):
        d = agente.post("/api/v1/vision/procesar", files={"archivo": (nombre, png, "application/octet-stream")},
                        data={"autoriza_envio_externo": "false"})
        assert d.status_code == 200, d.text
        codigos.append(d.json()["codigo"])
    primero = agente.post(f"/api/v1/vision/{codigos[0]}/confirmar", json=dict(datos)).json()["proceso_negocio"]
    segundo = agente.post(f"/api/v1/vision/{codigos[1]}/confirmar", json=dict(datos)).json()["proceso_negocio"]
    assert primero["accion"] == "GASTO_REGISTRADO"
    assert segundo["accion"] == "DUPLICADO_NO_REGISTRADO"


def test_vision_api_rejects_a_file_that_is_not_a_real_image(agente):
    r = agente.post("/api/v1/vision/procesar",
                    files={"archivo": ("factura_test.png", b"Factura Electronica FE-999. Esto no es un PNG.", "image/png")})
    assert r.status_code == 400
    assert "contenido" in r.json()["detail"].lower()


# ======================================================================= motor de automatización

def test_engine_success_is_logged(db):
    res = automation_engine.ejecutar_servicio_con_auditoria(
        db, "test_flujo", "OK", lambda: {"ok": True}, usuario="pytest", entrada_resumen="entrada de prueba")
    fila = db.query(models.EjecucionAutomatizacion).filter_by(codigo_ejecucion=res["codigo_ejecucion"]).one()
    assert fila.estado == "EXITOSO" and fila.intentos == 1
    assert fila.entrada_resumen == "entrada de prueba"
    assert fila.duracion_ms is not None


def test_engine_retries_transient_errors_until_success(db):
    intentos = {"n": 0}

    def inestable():
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise ConnectionError("servicio caído")
        return {"ok": True}

    res = automation_engine.ejecutar_servicio_con_auditoria(db, "test_flujo", "REINTENTO", inestable, max_reintentos=3)
    fila = db.query(models.EjecucionAutomatizacion).filter_by(codigo_ejecucion=res["codigo_ejecucion"]).one()
    assert intentos["n"] == 3 and fila.intentos == 3 and fila.estado == "EXITOSO"


def test_engine_marks_failed_after_max_attempts_and_keeps_the_error(db):
    def siempre_falla():
        raise RuntimeError("boom")

    res = automation_engine.ejecutar_servicio_con_auditoria(db, "test_flujo", "FALLO", siempre_falla, max_reintentos=2)
    assert res["ok"] is False and res["estado"] == "FALLIDO"
    fila = db.query(models.EjecucionAutomatizacion).filter_by(codigo_ejecucion=res["codigo_ejecucion"]).one()
    assert fila.estado == "FALLIDO" and fila.intentos == 2 and "boom" in fila.error


def test_engine_does_not_retry_validation_errors_and_reraises(db):
    llamadas = {"n": 0}

    def invalido():
        llamadas["n"] += 1
        raise ValueError("dato inválido")

    with pytest.raises(ValueError):
        automation_engine.ejecutar_servicio_con_auditoria(db, "test_flujo", "VALIDACION", invalido, max_reintentos=3)
    assert llamadas["n"] == 1
    fila = (db.query(models.EjecucionAutomatizacion).filter_by(proceso="VALIDACION")
            .order_by(models.EjecucionAutomatizacion.id_ejecucion.desc()).first())
    assert fila.estado == "FALLIDO"


def test_engine_flags_plan_b(db):
    res = automation_engine.ejecutar_servicio_con_auditoria(
        db, "test_flujo", "PLAN_B", lambda: {"plan_b_utilizado": True, "proveedor_ia": "local_reglas"})
    fila = db.query(models.EjecucionAutomatizacion).filter_by(codigo_ejecucion=res["codigo_ejecucion"]).one()
    assert fila.estado == "PLAN_B"


def test_flow_inventory_lists_the_registered_flows(db):
    ids = {f["id"] for f in automation_engine.inventario(db)}
    assert {"radicacion_tickets", "procesamiento_lote", "respuesta_replica", "vision_documento",
            "proceso_negocio_vision", "monitor_sla", "cola_reintento_ia", "resumen_diario"} <= ids
    for f in automation_engine.inventario(db):
        assert f["disparador"] and f["pasos"] and f["servicios"] and f["resultado"], f["id"]


def test_logs_endpoint_for_admin_shows_executions(admin, db):
    automation_engine.ejecutar_servicio_con_auditoria(db, "test_flujo", "VISIBLE", lambda: {"ok": True})
    r = admin.get("/api/v1/automatizaciones/logs?flujo=test_flujo")
    assert r.status_code == 200
    assert any(l["proceso"] == "VISIBLE" for l in r.json())


# ======================================================================= tareas programadas (cron)

def test_scheduler_registers_cron_jobs_and_stops(monkeypatch):
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", True)
    sch = scheduler.iniciar()
    try:
        assert sch is not None
        esperados = {f.id for f in automation_engine.FLUJOS.values() if f.tipo == "cron"}
        assert esperados and esperados == {j.id for j in sch.get_jobs()}
    finally:
        scheduler.detener()


def test_scheduler_disabled_by_config(monkeypatch):
    monkeypatch.setattr(config, "SCHEDULER_ENABLED", False)
    assert scheduler.iniciar() is None


@pytest.mark.parametrize("flujo", ["monitor_sla", "cola_reintento_ia", "resumen_diario"])
def test_cron_flows_run_and_leave_a_log(admin, flujo):
    r = admin.post(f"/api/v1/automatizaciones/flujos/{flujo}/ejecutar")
    assert r.status_code == 200, r.text
    assert r.json().get("codigo_ejecucion")
    assert admin.post("/api/v1/automatizaciones/flujos/no_existe/ejecutar").status_code == 404


# ======================================================================= proveedores de IA (cadena y Plan B)

def test_provider_chain_falls_back_when_the_first_is_out_of_quota(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(config, "GROQ_API_KEY", "y")
    monkeypatch.setattr(config, "AI_PROVIDER_ORDER", ["gemini", "groq"])

    def sin_cuota(*a, **k):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setitem(ai_provider._CALLERS, "gemini", sin_cuota)
    monkeypatch.setitem(ai_provider._CALLERS, "groq", lambda *a, **k: "respuesta de groq")
    res = ai_provider.generate("hola")
    assert res.ok and res.provider == "groq" and res.text == "respuesta de groq"


def test_provider_returns_error_when_every_provider_fails(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(config, "AI_PROVIDER_ORDER", ["gemini"])
    monkeypatch.setattr(config, "AI_MAX_RETRIES", 1)

    def falla(*a, **k):
        raise ConnectionError("sin red")

    monkeypatch.setitem(ai_provider._CALLERS, "gemini", falla)
    res = ai_provider.generate("hola")
    assert res.ok is False and res.provider == "local" and "sin red" in res.error


def test_no_provider_configured_means_plan_b():
    assert ai_provider.is_available() is False
    assert ai_provider.generate("hola").ok is False
    assert ai_provider.status()["available"] is False


def test_local_only_never_uses_external_providers(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(config, "GROQ_API_KEY", "y")
    monkeypatch.setattr(config, "AI_PROVIDER_ORDER", ["gemini", "groq"])
    assert ai_provider.active_providers() == ["gemini", "groq"]
    assert ai_provider.active_providers(local_only=True) == []
    monkeypatch.setattr(config, "AI_EXTERNAL_ALLOWED", False)
    assert ai_provider.active_providers() == []


def test_ticket_classification_uses_plan_b_without_models():
    from app import ai_module
    res = ai_module.analyze_and_suggest("No puedo ingresar", "Mi contraseña no funciona y el acceso está bloqueado", [])
    assert res["prioridad_sugerida"] in {"Alta", "Media", "Baja"}
    assert res.get("plan_b_utilizado") is True


def test_ticket_classification_uses_the_llm_chain_when_available(monkeypatch):
    from app import ai_module
    salida = json.dumps({"prioridad": "Alta", "categoria": "Acceso y Cuentas", "respuesta": "Restableceremos su acceso.", "confianza": 0.9})
    monkeypatch.setattr(ai_provider, "generate",
                        lambda *a, **k: ai_provider.AIResult(ok=True, provider="groq", text=salida))
    res = ai_module.analyze_and_suggest("Sin acceso", "No puedo entrar a mi cuenta", [])
    assert res["prioridad_sugerida"] == "Alta"
    assert res["categoria_sugerida"] == "Acceso y Cuentas"
    assert res["proveedor_ia"] == "groq"


# ======================================================================= privacidad (Ley 1581)

def test_privacy_masks_personal_data_before_external_use():
    texto = "Contacto juan.perez@correo.com, celular 300 123 4567, cuenta 12345678901234"
    limpio = privacy.anonimizar_texto(texto)
    for crudo in ["juan.perez@correo.com", "300 123 4567", "12345678901234"]:
        assert crudo not in limpio
    assert "[CORREO]" in limpio and "[TELEFONO]" in limpio


def test_privacy_detects_categories_and_identity_documents_stay_local():
    assert privacy.detectar_datos_personales("escríbanos a a@b.co").get("correo") == 1
    assert privacy.tipo_requiere_modelo_local("cedula") is True
    assert privacy.tipo_requiere_modelo_local("factura") is False
    assert privacy.enmascarar_identificador("1020304050").endswith("5050") or "*" in privacy.enmascarar_identificador("1020304050")


# ======================================================================= validaciones de visión

def _nit(base: str) -> str:
    return f"{base}-{vision_service.digito_verificacion_nit(base)}"


def test_nit_check_digit_validation():
    assert vision_service.digito_verificacion_nit("860034313") == 7  # NIT público conocido (Bancolombia): 860.034.313-7
    assert vision_service.nit_valido(_nit("900123456")) is True
    assert vision_service.nit_valido("900123456-0" if vision_service.digito_verificacion_nit("900123456") != 0 else "900123456-1") is False
    assert vision_service.nit_valido("900123456") is None  # sin DV no se puede verificar
    assert vision_service.nit_valido(None) is None


@pytest.mark.parametrize("texto,esperado", [
    ("1.450.200", 1450200.0), ("$ 285.450,00", 285450.0), ("1,450,200.50", 1450200.5),
    ("1234.5", 1234.5), (350000, 350000.0), ("sin número", None), (None, None),
])
def test_amount_parsing(texto, esperado):
    assert vision_service.parse_monto(texto) == esperado


def test_date_normalization():
    assert vision_service.normalizar_fecha("15/03/2026") == "2026-03-15"
    assert vision_service.normalizar_fecha("2026-03-15") == "2026-03-15"
    assert vision_service.normalizar_fecha("no es fecha") is None


TEXTO_FACTURA = f"""Papelería El Tintero S.A.S.
NIT: {_nit('900123456')}
Factura Electrónica de Venta No. FE-20451
Fecha de emisión: 15/03/2026
Subtotal 1.000.000
IVA 190.000
Total a pagar: $ 1.190.000
"""


def test_rule_extractor_reads_an_invoice_without_inventing_data():
    assert vision_service.clasificar_texto(TEXTO_FACTURA) == "factura"
    c = vision_service.extraer_campos_de_texto(TEXTO_FACTURA)
    assert c["identificacion_fiscal_nit"] == _nit("900123456")
    assert c["numero_documento"] == "FE-20451"
    assert c["fecha_emision"] == "2026-03-15"
    assert c["monto_total"] == 1190000.0
    vacio = vision_service.extraer_campos_de_texto("")
    assert all(v is None for v in vacio.values())


def test_confidence_is_low_when_key_fields_are_missing():
    campos = vision_service.extraer_campos_de_texto("texto ilegible sin datos")
    conf = vision_service.confianza_por_campo(campos)
    assert vision_service.confianza_global("factura", conf, None) < config.VISION_CONFIDENCE_THRESHOLD


# ======================================================================= pipeline de visión (modelo simulado)

def _modelo_simulado(monkeypatch, fields, confidence=0.92, tipo="factura", capturar=None):
    monkeypatch.setattr(ai_provider, "is_available", lambda **k: True)
    monkeypatch.setattr(vision_service, "ocr_local", lambda *a, **k: "")

    def falso(file_bytes, mime_type, *, solo_local):
        if capturar is not None:
            capturar.append(solo_local)
        return {"document_type": tipo, "confidence": confidence, "fields": dict(fields),
                "texto_completo_extraido": "texto", "proveedor": "ollama" if solo_local else "gemini"}, "mock"

    monkeypatch.setattr(vision_service, "_usar_modelo", falso)


def _campos_factura(numero=None, monto=1190000.0, nit=None):
    return {"emisor_o_proveedor": "Papelería El Tintero", "identificacion_fiscal_nit": nit or _nit("900123456"),
            "numero_documento": numero or f"FE-{uuid.uuid4().hex[:8]}", "fecha_emision": "2026-03-15",
            "monto_total": monto, "moneda": "COP"}


def _subir(cliente, png, consentimiento=False, id_ticket=None):
    data = {"autoriza_envio_externo": "true" if consentimiento else "false"}
    if id_ticket:
        data["id_ticket"] = str(id_ticket)
    return cliente.post("/api/v1/vision/procesar", files={"archivo": ("foto.png", png, "image/png")}, data=data)


def test_high_confidence_invoice_is_confirmed_and_creates_an_expense(monkeypatch, agente, png_bytes, db):
    campos = _campos_factura()
    _modelo_simulado(monkeypatch, campos)
    r = _subir(agente, png_bytes, consentimiento=True)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["estado"] == "CONFIRMADO" and body["confianza"] >= config.VISION_CONFIDENCE_THRESHOLD
    assert set(body["confianza_campos"]) >= {"monto_total", "identificacion_fiscal_nit", "fecha_emision"}
    gasto = db.query(models.Gasto).filter_by(codigo_documento=body["codigo"]).one()
    assert gasto.monto_total == 1190000.0 and gasto.numero_documento == campos["numero_documento"]


def test_low_confidence_goes_to_human_review_and_creates_no_expense(monkeypatch, agente, png_bytes, db):
    _modelo_simulado(monkeypatch, {"emisor_o_proveedor": None, "monto_total": None}, confidence=0.3)
    body = _subir(agente, png_bytes).json()
    assert body["estado"] == "PENDIENTE_REVISION" and body["requiere_revision"] is True
    assert db.query(models.Gasto).filter_by(codigo_documento=body["codigo"]).count() == 0


def test_human_confirmation_triggers_the_business_process(monkeypatch, agente, png_bytes, db):
    _modelo_simulado(monkeypatch, {"emisor_o_proveedor": None}, confidence=0.3)
    codigo = _subir(agente, png_bytes).json()["codigo"]
    corregido = _campos_factura()
    r = agente.post(f"/api/v1/vision/{codigo}/confirmar", json=corregido)
    assert r.status_code == 200 and r.json()["estado"] == "CONFIRMADO"
    assert db.query(models.Gasto).filter_by(codigo_documento=codigo).count() == 1


def test_duplicate_invoice_is_detected_and_not_registered_twice(monkeypatch, agente, png_bytes, db):
    campos = _campos_factura()
    _modelo_simulado(monkeypatch, campos)
    _subir(agente, png_bytes)
    segundo = _subir(agente, png_bytes).json()
    assert db.query(models.Gasto).filter_by(numero_documento=campos["numero_documento"]).count() == 1
    assert db.query(models.Gasto).filter_by(codigo_documento=segundo["codigo"]).count() == 0
    assert db.query(models.AuditoriaIA).filter_by(accion="DUPLICADO_DETECTADO", recurso=segundo["codigo"]).count() == 1


def test_rejected_document_cannot_be_confirmed(monkeypatch, agente, png_bytes):
    _modelo_simulado(monkeypatch, {}, confidence=0.2)
    codigo = _subir(agente, png_bytes).json()["codigo"]
    assert agente.post(f"/api/v1/vision/{codigo}/rechazar", data={"motivo": "ilegible"}).json()["estado"] == "RECHAZADO"
    assert agente.post(f"/api/v1/vision/{codigo}/confirmar", json={}).status_code == 409


def test_without_consent_images_are_processed_with_local_models_only(monkeypatch, agente, png_bytes):
    usos = []
    _modelo_simulado(monkeypatch, _campos_factura(), capturar=usos)
    _subir(agente, png_bytes, consentimiento=False)
    _subir(agente, png_bytes, consentimiento=True)
    assert usos == [True, False]


def test_identity_documents_never_leave_the_server_even_with_consent(monkeypatch, agente, png_bytes):
    usos = []
    _modelo_simulado(monkeypatch, {"emisor_o_proveedor": None}, tipo="cedula", capturar=usos)
    monkeypatch.setattr(vision_service, "ocr_local", lambda *a, **k: "REPÚBLICA DE COLOMBIA cédula de ciudadanía")
    _subir(agente, png_bytes, consentimiento=True)
    assert usos == [True]


def test_without_any_model_or_ocr_the_document_is_not_fabricated(agente, png_bytes):
    body = _subir(agente, png_bytes).json()
    assert body["proveedor"] == "sin_lectura"
    assert body["estado"] == "PENDIENTE_REVISION"
    assert all(v in (None, "") for k, v in body["campos"].items() if k != "observaciones_clave")


def test_image_access_is_restricted_and_audited(monkeypatch, agente, otro_agente, admin, png_bytes, db):
    _modelo_simulado(monkeypatch, _campos_factura())
    codigo = _subir(agente, png_bytes).json()["codigo"]
    assert otro_agente.get(f"/api/v1/vision/{codigo}").status_code == 403
    assert otro_agente.get(f"/api/v1/vision/{codigo}/archivo").status_code == 403
    assert otro_agente.post(f"/api/v1/vision/{codigo}/confirmar", json={}).status_code == 403
    assert agente.get(f"/api/v1/vision/{codigo}/archivo").status_code == 200
    assert admin.get(f"/api/v1/vision/{codigo}").status_code == 200
    acciones = {a.accion for a in db.query(models.AuditoriaIA).filter_by(recurso=codigo).all()}
    assert {"SUBIDA_IMAGEN", "EXTRACCION_IA", "ACCESO_ARCHIVO", "ACCESO_DENEGADO"} <= acciones
    assert codigo not in {d["codigo"] for d in otro_agente.get("/api/v1/vision/").json()}


def test_error_screenshot_raises_ticket_priority(monkeypatch, agente, png_bytes, db):
    ticket = db.query(models.Ticket).filter(models.Ticket.id_agente_asignado.isnot(None)).first()
    agente_ticket = db.query(models.UsuarioAgente).filter_by(id_agente=ticket.id_agente_asignado).one()
    cliente = agente if agente_ticket.correo_electronico == LOGIN_AGENTE["email"] else None
    if cliente is None:
        pytest.skip("el ticket de la semilla no está asignado al agente de prueba")
    ticket.prioridad = "Baja"
    db.commit()
    _modelo_simulado(monkeypatch, {"codigo_error_detectado": "HTTP 500", "emisor_o_proveedor": "Portal"},
                     confidence=0.95, tipo="captura_error")
    _subir(cliente, png_bytes, id_ticket=ticket.id_ticket)
    db.refresh(ticket)
    assert ticket.prioridad == "Alta"


# ======================================================================= chatbot (LangGraph)

def test_chatbot_keeps_memory_between_turns(monkeypatch, db):
    prompts = []

    def falso(prompt, **k):
        prompts.append(prompt)
        return ai_provider.AIResult(ok=True, provider="groq", text="ok")

    monkeypatch.setattr(ai_provider, "generate", falso)
    user = db.query(models.UsuarioAgente).first()
    hilo = f"test-{uuid.uuid4().hex}"
    chatbot_graph.conversar(db, user, "Mi proveedor se llama Distribuidora Andina", thread_id=hilo)
    r2 = chatbot_graph.conversar(db, user, "¿Cómo se llama mi proveedor?", thread_id=hilo)
    assert "Distribuidora Andina" in prompts[1]
    assert r2["proveedor"] == "groq" and r2["turnos_en_memoria"] == 2
    chatbot_graph.olvidar(hilo)
    chatbot_graph.conversar(db, user, "otra pregunta", thread_id=hilo)
    assert "Distribuidora Andina" not in prompts[2]


def test_chatbot_threads_are_isolated(monkeypatch, db):
    prompts = []
    monkeypatch.setattr(ai_provider, "generate",
                        lambda p, **k: prompts.append(p) or ai_provider.AIResult(ok=True, provider="groq", text="ok"))
    user = db.query(models.UsuarioAgente).first()
    chatbot_graph.conversar(db, user, "dato secreto ALFA", thread_id="hilo-a")
    chatbot_graph.conversar(db, user, "hola", thread_id="hilo-b")
    assert "ALFA" not in prompts[1]


def test_chatbot_uses_tools_and_plan_b(db):
    user = db.query(models.UsuarioAgente).first()
    ticket = db.query(models.Ticket).first()
    res = chatbot_graph.conversar(db, user, f"¿Cuál es el estado del ticket {ticket.codigo_seguimiento}?", thread_id="t-tools")
    assert "consultar_ticket" in res["herramientas"]
    assert res["proveedor"] == "local" and res["respuesta"]  # sin modelos: responde el motor local (Plan B)


def test_chatbot_endpoint_with_memory_and_image(monkeypatch, agente, png_bytes):
    _modelo_simulado(monkeypatch, _campos_factura())
    monkeypatch.setattr(ai_provider, "generate",
                        lambda p, **k: ai_provider.AIResult(ok=True, provider="groq", text="Recibí tu factura."))
    r = agente.post("/api/v1/chatbot/mensaje", data={"pregunta": "¿Qué dice esta factura?"},
                    files={"imagen": ("f.png", png_bytes, "image/png")})
    assert r.status_code == 200, r.text
    assert r.json()["vision"]["estado"] == "CONFIRMADO"
    assert agente.delete("/api/v1/chatbot/memoria").json() == {"ok": True}


def test_public_chatbot_endpoints_still_work(anonimo):
    r = anonimo.post("/api/v1/chatbot-archivos", json={"pregunta": "¿Qué puedo hacer?", "archivos": []})
    assert r.status_code in (200, 422)  # contrato heredado; no debe romperse por la migración


# ======================================================================= lotes documentales

def test_batch_processing_runs_through_the_engine(db):
    import os
    ticket = db.query(models.Ticket).first()
    codigo = f"LOT-TEST-{uuid.uuid4().hex[:6].upper()}"
    ruta = os.path.join(config.BATCH_DIR, f"{codigo}.pdf")
    with open(ruta, "wb") as f:
        f.write(b"%PDF-1.4 vacio")
    lote = models.LoteArchivos(batch_code=codigo, id_ticket=ticket.id_ticket, total_archivos=2, estado_make="QUEUED")
    db.add(lote)
    db.commit()
    db.add_all([
        models.ArchivoAdjunto(id_lote=lote.id_lote, file_code="FILE-01", nombre_original="roto.pdf", extension="pdf", mime_type="application/pdf",
                              tamano_bytes=0, ruta_temporal=os.path.join(config.BATCH_DIR, "no_existe.pdf")),
        models.ArchivoAdjunto(id_lote=lote.id_lote, file_code="FILE-02", nombre_original="x.pdf", extension="pdf", mime_type="application/pdf",
                              tamano_bytes=14, ruta_temporal=ruta),
    ])
    db.commit()
    res = automation_flows.procesar_lote_documental(db, codigo)
    assert res["total"] == 2 and res["procesados"] == 1  # el archivo dañado no detiene el lote
    db.refresh(lote)
    assert lote.estado_make == "COMPLETED"
    estados = {a.file_code: a.estado_procesamiento for a in lote.archivos}
    assert estados["FILE-01"] == "ERROR_UNREADABLE"


# ======================================================================= métricas del dashboard

def test_real_dashboard_metrics(admin):
    r = admin.get("/api/v1/admin/dashboard")
    assert r.status_code == 200
    m = r.json()
    for k in ["total_tickets", "total_ejecuciones_automatizacion", "tasa_exito_automatizacion", "total_documentos_vision"]:
        assert k in m
    assert isinstance(m["tiempo_promedio_respuesta_minutos"], (int, float))


# ======================================================================= benchmark de visión (métricas)

def test_benchmark_metrics_per_field_and_review_rate():
    from benchmark.metricas import resumir
    esperado = {"emisor_o_proveedor": "Papelería El Tintero", "identificacion_fiscal_nit": "900123456-1",
                "numero_documento": "FE-1", "fecha_emision": "2026-03-15", "monto_total": "1190000"}
    bien = dict(esperado, monto_total=1190000.0, emisor_o_proveedor="PAPELERIA EL TINTERO S.A.S.", fecha_emision="15/03/2026")
    mal = dict(esperado, monto_total=119000.0)
    filas = [
        {"esperado": esperado, "obtenido": bien, "confianza": 0.9, "tipo_esperado": "factura", "tipo_obtenido": "factura", "latencia_ms": 10},
        {"esperado": esperado, "obtenido": mal, "confianza": 0.8, "tipo_esperado": "factura", "tipo_obtenido": "factura", "latencia_ms": 30},
        {"esperado": esperado, "obtenido": {}, "confianza": 0.2, "tipo_esperado": "factura", "tipo_obtenido": "otro", "latencia_ms": 20},
    ]
    r = resumir(filas)
    assert r["precision_por_campo"]["monto_total"] == pytest.approx(33.3, abs=0.1)
    assert r["precision_por_campo"]["numero_documento"] == pytest.approx(66.7, abs=0.1)
    assert r["enviadas_a_revision_humana"] == pytest.approx(33.3, abs=0.1)
    assert r["precision_de_las_auto_confirmadas"] == 50.0
    assert r["precision_tipo_documento"] == pytest.approx(66.7, abs=0.1)
    assert r["latencia_media_ms"] == 20
