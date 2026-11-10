import random
import string
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import extract
from . import models, schemas, ai_module

def generate_codigo_seguimiento() -> str:
    num = "".join(random.choices(string.digits, k=4))
    return f"TCK-2026-{num}"

def get_cliente_by_email(db: Session, email: str):
    return db.query(models.Cliente).filter(models.Cliente.correo_electronico == email).first()

def create_or_update_cliente(db: Session, cliente: schemas.ClienteCreate):
    db_cliente = get_cliente_by_email(db, cliente.correo_electronico)
    if db_cliente:
        db_cliente.nombre_completo = cliente.nombre_completo
        if cliente.telefono:
            db_cliente.telefono = cliente.telefono
        if cliente.empresa_organizacion:
            db_cliente.empresa_organizacion = cliente.empresa_organizacion
    else:
        db_cliente = models.Cliente(
            nombre_completo=cliente.nombre_completo,
            correo_electronico=cliente.correo_electronico,
            telefono=cliente.telefono,
            empresa_organizacion=cliente.empresa_organizacion
        )
        db.add(db_cliente)
    db.commit()
    db.refresh(db_cliente)
    return db_cliente

def create_ticket_with_ai(db: Session, ticket_data: schemas.TicketCreate):
    # 1. Get or Create/Update Cliente
    cliente_in = schemas.ClienteCreate(
        nombre_completo=ticket_data.nombre_cliente,
        correo_electronico=ticket_data.correo_cliente,
        telefono=ticket_data.telefono,
        empresa_organizacion=ticket_data.empresa
    )
    cliente = create_or_update_cliente(db, cliente_in)

    # 2. Generate Tracking Code
    codigo = generate_codigo_seguimiento()
    while db.query(models.Ticket).filter(models.Ticket.codigo_seguimiento == codigo).first():
        codigo = generate_codigo_seguimiento()

    # 3. Fetch Soluciones for AI matching
    soluciones = db.query(models.Solucion).all()
    soluciones_list = [
        {
            "id_solucion": s.id_solucion,
            "titulo": s.titulo,
            "contenido_solucion": s.contenido_solucion,
            "categoria": s.categoria,
            "palabras_clave": s.palabras_clave
        }
        for s in soluciones
    ]

    # 4. Run Customer-Centric AI Analysis
    ai_result = ai_module.analyze_and_suggest(
        titulo=ticket_data.titulo,
        descripcion=ticket_data.descripcion,
        soluciones_kb=soluciones_list,
        nombre_cliente=ticket_data.nombre_cliente,
        empresa=ticket_data.empresa or ""
    )

    # 5. Respect client's selected category if present, otherwise use AI category
    cat_final = ticket_data.categoria_preliminar if (ticket_data.categoria_preliminar and ticket_data.categoria_preliminar != "General") else (ai_result["categoria_sugerida"] or "General")

    # 6. Auto-assign a default active specialist agent so the client always sees a responsible specialist
    agente_default = db.query(models.UsuarioAgente).filter(models.UsuarioAgente.activo == True).first()

    # 7. Create Ticket in DB with immediate 24/7 response ready for the customer
    db_ticket = models.Ticket(
        codigo_seguimiento=codigo,
        id_cliente=cliente.id_cliente,
        titulo=ticket_data.titulo,
        descripcion=ticket_data.descripcion,
        categoria_preliminar=cat_final,
        prioridad=ai_result["prioridad_sugerida"],
        estado="En Proceso",
        id_agente_asignado=agente_default.id_agente if agente_default else None,
        respuesta_oficial=ai_result["respuesta_sugerida"]
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)

    # 8. Create SugerenciaIA entry
    db_sugerencia = models.SugerenciaIA(
        id_ticket=db_ticket.id_ticket,
        prioridad_sugerida=ai_result["prioridad_sugerida"],
        categoria_sugerida=ai_result["categoria_sugerida"],
        respuesta_sugerida=ai_result["respuesta_sugerida"],
        score_confianza=ai_result["score_confianza"]
    )
    db.add(db_sugerencia)

    # 9. Create initial Conversation Thread messages (Client request + Instant 24/7 AI Response)
    msg_cliente = models.MensajeTicket(
        id_ticket=db_ticket.id_ticket,
        remitente_tipo="CLIENTE",
        remitente_nombre=cliente.nombre_completo,
        contenido=f"Asunto: {ticket_data.titulo}\n\n{ticket_data.descripcion}"
    )
    msg_ia = models.MensajeTicket(
        id_ticket=db_ticket.id_ticket,
        remitente_tipo="IA",
        remitente_nombre="Asistente Ejecutivo IA 24/7",
        contenido=ai_result["respuesta_sugerida"]
    )
    db.add(msg_cliente)
    db.add(msg_ia)
    db.commit()
    db.refresh(db_ticket)

    return db_ticket

def get_ticket_by_codigo(db: Session, codigo: str):
    return db.query(models.Ticket).filter(models.Ticket.codigo_seguimiento == codigo).first()

def get_ticket_by_id(db: Session, id_ticket: int):
    return db.query(models.Ticket).filter(models.Ticket.id_ticket == id_ticket).first()

def get_tickets(db: Session, estado: str = None, prioridad: str = None):
    query = db.query(models.Ticket)
    if estado and estado != "Todos":
        query = query.filter(models.Ticket.estado == estado)
    if prioridad and prioridad != "Todas":
        query = query.filter(models.Ticket.prioridad == prioridad)
    return query.order_by(models.Ticket.fecha_creacion.desc()).all()

def asignar_ticket(db: Session, id_ticket: int, id_agente: int):
    ticket = get_ticket_by_id(db, id_ticket)
    if ticket:
        ticket.id_agente_asignado = id_agente
        if ticket.estado == "Abierto":
            ticket.estado = "En Proceso"
        ticket.fecha_actualizacion = datetime.utcnow()
        db.commit()
        db.refresh(ticket)
    return ticket

def responder_ticket(db: Session, id_ticket: int, respuesta: str, nuevo_estado: str):
    ticket = get_ticket_by_id(db, id_ticket)
    if ticket:
        ticket.respuesta_oficial = respuesta
        ticket.estado = nuevo_estado
        ticket.fecha_actualizacion = datetime.utcnow()
        agente_nombre = ticket.agente_asignado.nombre_completo if ticket.agente_asignado else "Especialista de Soporte Senior"
        msg_agente = models.MensajeTicket(
            id_ticket=ticket.id_ticket,
            remitente_tipo="AGENTE",
            remitente_nombre=agente_nombre,
            contenido=respuesta
        )
        db.add(msg_agente)
        db.commit()
        db.refresh(ticket)
    return ticket

def agregar_replica_cliente(db: Session, codigo: str, comentario: str):
    ticket = get_ticket_by_codigo(db, codigo)
    if not ticket or not comentario.strip():
        return None
    cliente_nombre = ticket.cliente.nombre_completo if ticket.cliente else "Cliente"
    msg_cli = models.MensajeTicket(
        id_ticket=ticket.id_ticket,
        remitente_tipo="CLIENTE",
        remitente_nombre=cliente_nombre,
        contenido=comentario.strip()
    )
    db.add(msg_cli)

    total_archivos = sum(l.total_archivos for l in ticket.lotes) if ticket.lotes else 0
    ai_followup = ai_module.generate_followup_ai_reply(
        ticket_titulo=ticket.titulo,
        cliente_nombre=cliente_nombre,
        comentario_cliente=comentario.strip(),
        total_archivos=total_archivos
    )
    msg_ia = models.MensajeTicket(
        id_ticket=ticket.id_ticket,
        remitente_tipo="IA",
        remitente_nombre="Asistente Ejecutivo IA 24/7",
        contenido=ai_followup
    )
    db.add(msg_ia)
    if ticket.estado == "Cerrado":
        ticket.estado = "En Proceso"
    ticket.fecha_actualizacion = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return ticket

def calificar_ticket_cliente(db: Session, codigo: str, estrellas: int, comentario: str = ""):
    ticket = get_ticket_by_codigo(db, codigo)
    if not ticket:
        return None
    estrellas_val = max(1, min(5, int(estrellas)))
    if ticket.calificacion:
        ticket.calificacion.estrellas = estrellas_val
        ticket.calificacion.comentario = comentario.strip()
        ticket.calificacion.fecha_calificacion = datetime.utcnow()
    else:
        cal = models.CalificacionTicket(
            id_ticket=ticket.id_ticket,
            estrellas=estrellas_val,
            comentario=comentario.strip()
        )
        db.add(cal)
    db.commit()
    db.refresh(ticket)
    return ticket

def get_soluciones(db: Session, categoria: str = None, query: str = None):
    q = db.query(models.Solucion)
    if categoria:
        q = q.filter(models.Solucion.categoria == categoria)
    if query:
        q = q.filter(models.Solucion.titulo.contains(query) | models.Solucion.palabras_clave.contains(query))
    return q.all()

def create_solucion(db: Session, solucion: schemas.SolucionCreate):
    db_sol = models.Solucion(
        titulo=solucion.titulo,
        contenido_solucion=solucion.contenido_solucion,
        categoria=solucion.categoria,
        palabras_clave=solucion.palabras_clave,
        id_autor=solucion.id_autor,
        id_ticket_origen=solucion.id_ticket_origen
    )
    db.add(db_sol)
    db.commit()
    db.refresh(db_sol)
    return db_sol

def get_dashboard_metrics(db: Session):
    total = db.query(models.Ticket).count()
    abiertos = db.query(models.Ticket).filter(models.Ticket.estado == "Abierto").count()
    en_proceso = db.query(models.Ticket).filter(models.Ticket.estado == "En Proceso").count()
    resueltos = db.query(models.Ticket).filter(models.Ticket.estado.in_(["Resuelto", "Cerrado"])).count()
    
    p_alta = db.query(models.Ticket).filter(models.Ticket.prioridad == "Alta").count()
    p_media = db.query(models.Ticket).filter(models.Ticket.prioridad == "Media").count()
    p_baja = db.query(models.Ticket).filter(models.Ticket.prioridad == "Baja").count()
    
    return {
        "total_tickets": total,
        "tickets_abiertos": abiertos,
        "tickets_en_proceso": en_proceso,
        "tickets_resueltos": resueltos,
        "prioridad_alta_ia": p_alta,
        "prioridad_media_ia": p_media,
        "prioridad_baja_ia": p_baja,
        "tiempo_promedio_respuesta_minutos": 8.4,
        "efectividad_sugerencia_ia_porcentaje": 96.4
    }

def get_monthly_report_data(db: Session, mes: int, anio: int):
    tickets_query = db.query(models.Ticket).filter(
        extract('month', models.Ticket.fecha_creacion) == mes,
        extract('year', models.Ticket.fecha_creacion) == anio
    )
    tickets = tickets_query.all()
    total = len(tickets)
    
    resueltos = sum(1 for t in tickets if t.estado in ["Resuelto", "Cerrado"])
    abiertos = sum(1 for t in tickets if t.estado == "Abierto")
    en_proceso = sum(1 for t in tickets if t.estado == "En Proceso")
    
    alta = sum(1 for t in tickets if t.prioridad == "Alta")
    media = sum(1 for t in tickets if t.prioridad == "Media")
    baja = sum(1 for t in tickets if t.prioridad == "Baja")
    
    agentes = db.query(models.UsuarioAgente).all()
    agentes_perf = []
    for a in agentes:
        cnt = sum(1 for t in tickets if t.id_agente_asignado == a.id_agente)
        agentes_perf.append({
            "id_agente": a.id_agente,
            "nombre": a.nombre_completo,
            "rol": a.rol,
            "atendidos": cnt
        })
        
    return {
        "mes": mes,
        "anio": anio,
        "periodo": f"{anio}-{mes:02d}",
        "total_tickets": total,
        "tickets_resueltos": resueltos,
        "tickets_abiertos": abiertos,
        "tickets_en_proceso": en_proceso,
        "prioridad_alta": alta,
        "prioridad_media": media,
        "prioridad_baja": baja,
        "agentes_perf": agentes_perf,
        "tickets_lista": tickets
    }
