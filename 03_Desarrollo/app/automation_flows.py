"""Flujos de negocio del motor propio. Cada flujo reemplaza un escenario de n8n/Make.

El inventario (disparador, pasos, servicios externos, resultado) está en `FLUJOS` y se publica en
`/api/v1/automatizaciones/flujos`; el documento `docs/INVENTARIO_FLUJOS.md` es su versión narrativa.
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app import ai_provider, automation_engine, config, llm_chains, models
from app.automation_engine import FlujoDef, registrar_flujo

log = logging.getLogger("automation_flows")

PRIO_RANK = {"Baja": 1, "Media": 2, "Alta": 3}


# =========================================================================== F4: proceso de negocio de la visión

def _campos_finales(doc: models.DocumentoVision) -> Dict[str, Any]:
    raw = doc.campos_confirmados_json or doc.campos_json or "{}"
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def aplicar_proceso_negocio(db: Session, doc: models.DocumentoVision, usuario: str) -> Dict[str, Any]:
    """Convierte el resultado de la visión en una acción de negocio, con rastro en el log del motor."""
    return automation_engine.ejecutar_servicio_con_auditoria(
        db=db, flujo="proceso_negocio_vision", proceso=f"APLICAR_{(doc.tipo_documento or 'otro').upper()}",
        func=lambda: _proceso_negocio(db, doc, usuario),
        usuario=usuario, id_ticket=doc.id_ticket,
        entrada_resumen=f"{doc.codigo} tipo={doc.tipo_documento} confianza={doc.confianza}",
    )


def _proceso_negocio(db: Session, doc: models.DocumentoVision, usuario: str) -> Dict[str, Any]:
    from app import vision_service
    campos = _campos_finales(doc)
    tipo = doc.tipo_documento or "otro"

    if tipo in vision_service.TIPOS_FINANCIEROS:
        existente = db.query(models.Gasto).filter(models.Gasto.codigo_documento == doc.codigo).first()
        if existente:
            return {"accion": "GASTO_YA_REGISTRADO", "id_gasto": existente.id_gasto}
        monto = vision_service.parse_monto(campos.get("monto_total")) or 0.0
        nit = campos.get("identificacion_fiscal_nit")
        numero = campos.get("numero_documento")
        duplicado = None
        if nit and numero and monto:
            duplicado = db.query(models.Gasto).filter(
                models.Gasto.nit == nit, models.Gasto.numero_documento == numero,
                models.Gasto.monto_total == monto, models.Gasto.estado == "REGISTRADO").first()
        if duplicado:
            vision_service.auditar(db, usuario, "DUPLICADO_DETECTADO", doc.codigo, doc.proveedor,
                                   f"Coincide con gasto {duplicado.id_gasto}")
            return {"accion": "DUPLICADO_NO_REGISTRADO", "id_gasto_existente": duplicado.id_gasto}
        gasto = models.Gasto(
            codigo_documento=doc.codigo, proveedor=campos.get("emisor_o_proveedor"), nit=nit,
            numero_documento=numero, fecha_documento=vision_service.normalizar_fecha(campos.get("fecha_emision")),
            monto_total=monto, moneda=campos.get("moneda") or "COP", registrado_por=usuario)
        db.add(gasto)
        db.commit()
        db.refresh(gasto)
        vision_service.auditar(db, usuario, "GASTO_REGISTRADO", doc.codigo, doc.proveedor,
                               f"id_gasto={gasto.id_gasto} total={monto}")
        return {"accion": "GASTO_REGISTRADO", "id_gasto": gasto.id_gasto, "monto_total": monto}

    if tipo == "captura_error" and doc.id_ticket:
        ticket = db.query(models.Ticket).filter(models.Ticket.id_ticket == doc.id_ticket).first()
        if ticket:
            if PRIO_RANK.get(ticket.prioridad, 1) < PRIO_RANK["Alta"]:
                ticket.prioridad = "Alta"
            db.add(models.MensajeTicket(
                id_ticket=ticket.id_ticket, remitente_tipo="IA", remitente_nombre="Motor de visión",
                contenido=f"La captura {doc.codigo} muestra un error ({campos.get('codigo_error_detectado') or 'sin código legible'}). "
                          "Se elevó la prioridad del caso a Alta."))
            db.commit()
            return {"accion": "TICKET_PRIORIZADO", "id_ticket": ticket.id_ticket}

    return {"accion": "ARCHIVADO", "repositorio": doc.repositorio}


# =========================================================================== F2: lote documental

def _extraer_texto(ext: str, raw: bytes) -> str:
    from app import make_batch_router
    return make_batch_router.extract_office_or_text_content(ext, raw)


def analizar_archivo(filename: str, ext: str, size_bytes: int, raw: bytes) -> Dict[str, Any]:
    texto = _extraer_texto(ext, raw)
    combinado = f"{filename} {texto}".lower()
    tipos = {"pdf": "Documento PDF", "xlsx": "Hoja de cálculo Excel", "docx": "Documento Word",
             "jpg": "Imagen / evidencia visual", "jpeg": "Imagen / evidencia visual",
             "png": "Imagen / evidencia visual", "webp": "Imagen / evidencia visual", "txt": "Texto plano", "csv": "Tabla CSV"}
    if any(k in combinado for k in ["error", "critico", "crítico", "caido", "caído", "timeout", "urgente", "falla", "500", "bloqueo", "inaccesible"]):
        prio, rec = "Alta", "Atención prioritaria: la evidencia indica una caída o bloqueo de servicio."
    elif any(k in combinado for k in ["factura", "inventario", "reporte", "pago", "acceso", "cuenta", "configuracion", "lento", "auditoria"]):
        prio, rec = "Media", "Verificar los datos extraídos y validar la configuración o cuenta del cliente."
    else:
        prio, rec = "Baja", "Respaldo documental anexado al expediente del ticket."
    snippet = f" Contenido clave: \"{' '.join(texto.split())[:140]}\"" if texto.strip() else ""
    legible = bool(texto.strip()) or ext in ("jpg", "jpeg", "png", "webp")
    return {
        "status": "PROCESSED",
        "document_type": tipos.get(ext, "Documento adjunto"),
        "extracted_summary": f"'{filename}' ({round(size_bytes / 1024, 1)} KB) procesado.{snippet}",
        "suggested_priority": prio,
        "ai_action_recommendation": rec,
        # Confianza honesta: alta solo si se extrajo texto real; las imágenes se leen en el módulo /vision.
        "confidence_score": 0.9 if (texto.strip()) else (0.5 if legible else 0.3),
    }


def procesar_lote_documental(db: Session, batch_code: str) -> Dict[str, Any]:
    """Iterador -> clasificador por tipo -> análisis -> agregador -> actualización del ticket (ex Make)."""
    lote = db.query(models.LoteArchivos).filter_by(batch_code=batch_code).first()
    if not lote:
        raise ValueError(f"Lote {batch_code} no existe")
    lote.estado_make = "PROCESSING"
    lote.archivos_procesados = 0
    db.commit()

    resumenes: List[str] = []
    mas_alta = "Baja"
    por_ext = {"pdf": 0, "xlsx": 0, "docx": 0, "jpg": 0}
    for arch in lote.archivos:
        clave = "jpg" if arch.extension in ("jpg", "jpeg", "png", "webp") else {"txt": "docx", "csv": "xlsx"}.get(arch.extension, arch.extension)
        if clave in por_ext:
            por_ext[clave] += 1
        if not os.path.exists(arch.ruta_temporal) or arch.tamano_bytes == 0:
            arch.estado_procesamiento = "ERROR_UNREADABLE"
            arch.tipo_documento_ia = "Archivo corrupto o vacío"
            arch.resumen_extraido_ia = "Archivo vacío o dañado: omitido sin detener el lote."
            arch.prioridad_detectada = "Baja"
            arch.recomendacion_ia = "Solicitar al cliente reenviar este archivo."
            arch.score_confianza = 0.0
            continue
        with open(arch.ruta_temporal, "rb") as fp:
            raw = fp.read()
        res = analizar_archivo(arch.nombre_original, arch.extension, arch.tamano_bytes, raw)
        arch.estado_procesamiento = res["status"]
        arch.tipo_documento_ia = res["document_type"]
        arch.resumen_extraido_ia = res["extracted_summary"]
        arch.prioridad_detectada = res["suggested_priority"]
        arch.recomendacion_ia = res["ai_action_recommendation"]
        arch.score_confianza = res["confidence_score"]
        if PRIO_RANK[res["suggested_priority"]] > PRIO_RANK[mas_alta]:
            mas_alta = res["suggested_priority"]
        resumenes.append(f"[{arch.file_code}] {arch.nombre_original}: {res['suggested_priority']} — {res['ai_action_recommendation']}")
        lote.archivos_procesados += 1

    dist = f"PDF: {por_ext['pdf']} | XLSX: {por_ext['xlsx']} | DOCX: {por_ext['docx']} | JPG: {por_ext['jpg']}"
    resumen_local = (f"Lote {batch_code}: {lote.archivos_procesados}/{lote.total_archivos} archivos procesados. "
                     f"Distribución: [{dist}]. Prioridad consolidada: {mas_alta}.\n" + "\n".join(resumenes[:35]))
    sintesis = llm_chains.resumir_lote(resumenes, resumen_local)
    lote.sintesis_global_ia = resumen_local if sintesis["plan_b_utilizado"] else f"{resumen_local}\n\nSíntesis IA: {sintesis['resumen']}"
    lote.estado_make = "COMPLETED"
    lote.fecha_completado = datetime.utcnow()

    ticket = db.query(models.Ticket).filter_by(id_ticket=lote.id_ticket).first()
    if ticket:
        if PRIO_RANK[mas_alta] > PRIO_RANK.get(ticket.prioridad, 1):
            ticket.prioridad = mas_alta
            if ticket.sugerencia_ia:
                ticket.sugerencia_ia.prioridad_sugerida = mas_alta
        db.add(models.MensajeTicket(
            id_ticket=ticket.id_ticket, remitente_tipo="IA", remitente_nombre="Motor de automatización",
            contenido=f"Se completó el análisis automático del lote {batch_code} con {lote.archivos_procesados} archivo(s) "
                      f"({dist}). Prioridad consolidada: {mas_alta}."))
    db.commit()
    return {"batch_id": batch_code, "procesados": lote.archivos_procesados, "total": lote.total_archivos,
            "prioridad": mas_alta, "proveedor_ia": sintesis["proveedor_ia"],
            "plan_b_utilizado": sintesis["plan_b_utilizado"]}


# =========================================================================== F5-F7: flujos programados (cron)

def monitor_sla(db: Session) -> Dict[str, Any]:
    """Cada SLA_CHECK_MINUTES: tickets abiertos sin respuesta de un agente tras SLA_ALERT_MINUTES se escalan."""
    limite = datetime.utcnow() - timedelta(minutes=config.SLA_ALERT_MINUTES)
    pendientes = db.query(models.Ticket).filter(
        models.Ticket.estado.in_(["Abierto", "En Proceso"]), models.Ticket.fecha_creacion <= limite).all()
    escalados = 0
    for t in pendientes:
        if any(m.remitente_tipo == "AGENTE" for m in t.mensajes):
            continue
        if any(m.remitente_nombre == "Monitor SLA" for m in t.mensajes):
            continue  # ya alertado: no duplicar
        if PRIO_RANK.get(t.prioridad, 1) < PRIO_RANK["Alta"]:
            t.prioridad = "Alta" if t.prioridad == "Media" else "Media"
        db.add(models.MensajeTicket(
            id_ticket=t.id_ticket, remitente_tipo="IA", remitente_nombre="Monitor SLA",
            contenido=f"Alerta: el ticket superó {config.SLA_ALERT_MINUTES} minutos sin respuesta de un agente. "
                      "Se escaló su prioridad para atención inmediata."))
        escalados += 1
    db.commit()
    return {"revisados": len(pendientes), "escalados": escalados}


def cola_reintento_ia(db: Session) -> Dict[str, Any]:
    """Cada RETRY_QUEUE_MINUTES: reprocesa documentos que quedaron en cola porque el modelo no respondió."""
    from app import vision_service
    docs = db.query(models.DocumentoVision).filter(models.DocumentoVision.estado == "COLA_REINTENTO").limit(20).all()
    recuperados = 0
    for d in docs:
        try:
            vision_service.reprocesar_documento(db, d)
            if d.estado != "COLA_REINTENTO":
                recuperados += 1
        except Exception as e:  # noqa: BLE001
            log.warning("Reintento de %s falló: %s", d.codigo, e)
    return {"en_cola": len(docs), "recuperados": recuperados, "proveedor_ia_disponible": ai_provider.is_available(vision=True)}


def resumen_diario(db: Session) -> Dict[str, Any]:
    """Una vez al día: instantánea de métricas operativas del motor (queda en el log como evidencia)."""
    desde = datetime.utcnow() - timedelta(days=1)
    q = db.query(models.EjecucionAutomatizacion).filter(models.EjecucionAutomatizacion.fecha_inicio >= desde)
    total = q.count()
    fallidas = q.filter(models.EjecucionAutomatizacion.estado == "FALLIDO").count()
    plan_b = q.filter(models.EjecucionAutomatizacion.estado == "PLAN_B").count()
    pendientes = db.query(models.DocumentoVision).filter(models.DocumentoVision.estado == "PENDIENTE_REVISION").count()
    return {"ejecuciones_24h": total, "fallidas": fallidas, "plan_b": plan_b, "documentos_pendientes_revision": pendientes}


# =========================================================================== registro del inventario

registrar_flujo(FlujoDef(
    id="radicacion_tickets", nombre="Radicación y clasificación de tickets 24/7",
    disparador="POST /api/v1/tickets/ o formulario /crear-solicitud (público)",
    pasos=["Crear/actualizar cliente (con autorización de datos)", "Clasificar prioridad/categoría con LLM (cadena LangChain) o reglas",
           "Generar código de seguimiento", "Asignar agente activo", "Crear hilo con respuesta IA inicial"],
    servicios=["Gemini / Groq / Ollama (opcional)", "Base de datos"], resultado="Ticket con SLA, respuesta inicial y trazabilidad",
    origen_n8n="Webhook ticket -> IA clasificadora -> respuesta", tipo="evento"))
registrar_flujo(FlujoDef(
    id="procesamiento_lote", nombre="Procesamiento de lote documental (hasta 35 archivos)",
    disparador="Subida de lote con el ticket o desde el detalle del ticket",
    pasos=["Validar extensión, tamaño y límite", "Guardar archivos", "Iterar y clasificar por formato (PDF/XLSX/DOCX/JPG)",
           "Extraer texto y priorizar", "Agregar resultados y resumen IA anonimizado", "Actualizar ticket y notificar en el hilo"],
    servicios=["Gemini / Groq / Ollama (opcional)", "Sistema de archivos"], resultado="Síntesis del lote, prioridad consolidada y mensaje en el ticket",
    origen_n8n="Make: Webhook -> Iterator -> Router -> IA -> Aggregator -> Callback", tipo="evento"))
registrar_flujo(FlujoDef(
    id="respuesta_replica", nombre="Respuesta automática a réplicas del cliente",
    disparador="POST /mis-tickets/{codigo}/replicar", pasos=["Registrar mensaje del cliente", "Generar respuesta contextual", "Reabrir ticket si estaba cerrado"],
    servicios=["Base de datos"], resultado="Mensaje IA en el hilo y ticket actualizado", origen_n8n="Webhook réplica -> respuesta IA", tipo="evento"))
registrar_flujo(FlujoDef(
    id="vision_documento", nombre="Lectura de facturas/recibos por visión",
    disparador="POST /api/v1/vision/procesar (web, celular) o chatbot con imagen",
    pasos=["Validar firma binaria y tamaño", "Guardar con control de acceso y auditoría", "OCR local", "Enrutar por privacidad (consentimiento / modelo local)",
           "Extraer JSON con modelo multimodal o reglas", "Validar NIT/fecha/monto y calcular confianza", "Confianza < umbral -> revisión humana"],
    servicios=["Gemini visión / Ollama (LLaVA) / Tesseract"], resultado="JSON estructurado con confianza por campo y estado",
    origen_n8n="Webhook imagen -> OCR/LLM -> JSON", tipo="evento"))
registrar_flujo(FlujoDef(
    id="proceso_negocio_vision", nombre="Proceso de negocio disparado por la visión",
    disparador="Documento CONFIRMADO (automático por confianza o por revisión humana)",
    pasos=["Leer campos confirmados", "Factura/recibo: detectar duplicado y registrar gasto", "Captura de error: elevar prioridad del ticket", "Otros: archivar"],
    servicios=["Base de datos"], resultado="Registro en tbl_gasto / ticket priorizado", origen_n8n="Nodo final: crear registro en módulo de gastos", tipo="evento"))
registrar_flujo(FlujoDef(
    id="monitor_sla", nombre="Monitor de SLA (cron)", disparador=f"Cada {config.SLA_CHECK_MINUTES} min (APScheduler)",
    pasos=["Buscar tickets abiertos sin respuesta de agente", "Escalar prioridad", "Alertar en el hilo (sin duplicar)"],
    servicios=["Base de datos"], resultado="Tickets escalados", origen_n8n="Schedule trigger -> consulta tickets -> alerta",
    tipo="cron", cron={"minutes": config.SLA_CHECK_MINUTES}, ejecutar=monitor_sla))
registrar_flujo(FlujoDef(
    id="cola_reintento_ia", nombre="Cola de reintento de IA (cron)", disparador=f"Cada {config.RETRY_QUEUE_MINUTES} min (APScheduler)",
    pasos=["Buscar documentos en COLA_REINTENTO", "Reprocesar con proveedores disponibles", "Actualizar estado y confianza"],
    servicios=["Gemini / Ollama (opcional)"], resultado="Documentos recuperados tras una caída del modelo", origen_n8n="Error workflow -> reintento",
    tipo="cron", cron={"minutes": config.RETRY_QUEUE_MINUTES}, ejecutar=cola_reintento_ia))
registrar_flujo(FlujoDef(
    id="resumen_diario", nombre="Resumen diario de operación (cron)", disparador="Diario 23:55 (APScheduler)",
    pasos=["Contar ejecuciones, fallos y Plan B de las últimas 24 h", "Contar documentos pendientes de revisión"],
    servicios=["Base de datos"], resultado="Instantánea en el log de ejecuciones", origen_n8n="Schedule trigger -> métricas",
    tipo="cron", cron={"hour": 23, "minute": 55}, ejecutar=resumen_diario))
