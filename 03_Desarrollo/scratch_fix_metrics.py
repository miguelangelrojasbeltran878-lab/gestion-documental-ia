import os

crud_path = r'c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\03_Desarrollo\app\crud.py'
with open(crud_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace hardcoded get_dashboard_metrics with real database-calculated metrics
old_metrics = '''def get_dashboard_metrics(db: Session):
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
    }'''

new_metrics = '''def get_dashboard_metrics(db: Session):
    total = db.query(models.Ticket).count()
    abiertos = db.query(models.Ticket).filter(models.Ticket.estado == "Abierto").count()
    en_proceso = db.query(models.Ticket).filter(models.Ticket.estado == "En Proceso").count()
    resueltos = db.query(models.Ticket).filter(models.Ticket.estado.in_(["Resuelto", "Cerrado"])).count()
    
    p_alta = db.query(models.Ticket).filter(models.Ticket.prioridad == "Alta").count()
    p_media = db.query(models.Ticket).filter(models.Ticket.prioridad == "Media").count()
    p_baja = db.query(models.Ticket).filter(models.Ticket.prioridad == "Baja").count()
    
    # Métricas reales calculadas desde la base de datos
    calificaciones = db.query(models.CalificacionTicket).all()
    if calificaciones:
        promedio_estrellas = round(sum(c.estrellas for c in calificaciones) / len(calificaciones), 2)
        satisfaccion_pct = round((promedio_estrellas / 5.0) * 100, 1)
    else:
        promedio_estrellas = 0.0
        satisfaccion_pct = 0.0

    # Tiempo real promedio de resolución para tickets resueltos/cerrados (en minutos)
    tickets_cerrados = db.query(models.Ticket).filter(
        models.Ticket.estado.in_(["Resuelto", "Cerrado"]),
        models.Ticket.fecha_actualizacion.isnot(None),
        models.Ticket.fecha_creacion.isnot(None)
    ).all()
    
    tiempos_min = []
    for t in tickets_cerrados:
        delta = (t.fecha_actualizacion - t.fecha_creacion).total_seconds() / 60.0
        if delta >= 0:
            tiempos_min.append(delta)
    tiempo_promedio_min = round(sum(tiempos_min) / len(tiempos_min), 1) if tiempos_min else 0.0

    # Métricas del motor de automatización y visión
    total_ejecuciones = db.query(models.EjecucionAutomatizacion).count()
    ejecuciones_exitosas = db.query(models.EjecucionAutomatizacion).filter(
        models.EjecucionAutomatizacion.estado.in_(["EXITOSO", "PLAN_B"])
    ).count()
    tasa_exito_automatizacion = round((ejecuciones_exitosas / total_ejecuciones * 100), 1) if total_ejecuciones > 0 else 100.0

    total_vision = db.query(models.DocumentoVision).count()
    vision_confirmados = db.query(models.DocumentoVision).filter(models.DocumentoVision.estado == "CONFIRMADO").count()
    vision_pendientes = db.query(models.DocumentoVision).filter(models.DocumentoVision.estado == "PENDIENTE_REVISION").count()
    
    return {
        "total_tickets": total,
        "tickets_abiertos": abiertos,
        "tickets_en_proceso": en_proceso,
        "tickets_resueltos": resueltos,
        "prioridad_alta_ia": p_alta,
        "prioridad_media_ia": p_media,
        "prioridad_baja_ia": p_baja,
        "tiempo_promedio_respuesta_minutos": tiempo_promedio_min,
        "efectividad_sugerencia_ia_porcentaje": satisfaccion_pct,
        "calificacion_promedio_estrellas": promedio_estrellas,
        "total_calificaciones": len(calificaciones),
        "total_ejecuciones_automatizacion": total_ejecuciones,
        "tasa_exito_automatizacion": tasa_exito_automatizacion,
        "total_documentos_vision": total_vision,
        "vision_confirmados": vision_confirmados,
        "vision_pendientes": vision_pendientes
    }'''

if old_metrics in content:
    content = content.replace(old_metrics, new_metrics)
    with open(crud_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Real dashboard metrics updated in crud.py successfully!")
else:
    print("Warning: old_metrics not found in crud.py.")
