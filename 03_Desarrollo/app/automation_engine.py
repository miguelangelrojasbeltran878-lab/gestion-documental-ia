"""Motor de automatización propio en código (reemplazo de flujos n8n / Make externos).
Ejecuta procesos documentales desacoplados, con registro detallado en base de datos, reintentos controlados y manejo robusto de errores.
"""
import time
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from app import models, config

log = logging.getLogger("automation_engine")


def registrar_inicio_ejecucion(
    db: Session,
    flujo: str,
    proceso: str,
    usuario: Optional[str] = "sistema",
    id_ticket: Optional[int] = None,
    entrada_resumen: Optional[str] = None
) -> models.EjecucionAutomatizacion:
    """Crea el registro de auditoría para la ejecución de un paso o flujo automatizado."""
    codigo = f"EXE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
    ejecucion = models.EjecucionAutomatizacion(
        codigo_ejecucion=codigo,
        flujo=flujo,
        proceso=proceso,
        usuario=usuario,
        id_ticket=id_ticket,
        entrada_resumen=(entrada_resumen or "")[:500],
        estado="EN_CURSO",
        intentos=1,
        fecha_inicio=datetime.utcnow()
    )
    db.add(ejecucion)
    db.commit()
    db.refresh(ejecucion)
    return ejecucion


def finalizar_ejecucion(
    db: Session,
    ejecucion: models.EjecucionAutomatizacion,
    estado: str,
    resultado: Optional[str] = None,
    error: Optional[str] = None,
    proveedor_ia: Optional[str] = None,
    duracion_ms: int = 0
):
    """Actualiza y cierra la ejecución en base de datos con telemetría de rendimiento."""
    ejecucion.estado = estado
    ejecucion.resultado = (resultado or "")[:2000]
    ejecucion.error = (error or "")[:1000] if error else None
    ejecucion.proveedor_ia = proveedor_ia
    ejecucion.duracion_ms = duracion_ms
    ejecucion.fecha_fin = datetime.utcnow()
    db.commit()
    db.refresh(ejecucion)
    return ejecucion


def ejecutar_servicio_con_auditoria(
    db: Session,
    flujo: str,
    proceso: str,
    func: Callable[[], Dict[str, Any]],
    usuario: Optional[str] = "sistema",
    id_ticket: Optional[int] = None,
    entrada_resumen: Optional[str] = None,
    max_reintentos: int = 2
) -> Dict[str, Any]:
    """Ejecuta una función de servicio con reintentos controlados, cronómetro y persistencia de auditoría."""
    ejecucion = registrar_inicio_ejecucion(db, flujo, proceso, usuario, id_ticket, entrada_resumen)
    inicio = time.time()
    ultimo_error = None
    
    for intento in range(1, max_reintentos + 1):
        ejecucion.intentos = intento
        try:
            res = func()
            duracion = int((time.time() - inicio) * 1000)
            res_str = json.dumps(res, ensure_ascii=False) if isinstance(res, dict) else str(res)
            prov = res.get("proveedor_ia") if isinstance(res, dict) else None
            est = "PLAN_B" if (isinstance(res, dict) and res.get("plan_b_utilizado")) else "EXITOSO"
            finalizar_ejecucion(db, ejecucion, estado=est, resultado=res_str, proveedor_ia=prov, duracion_ms=duracion)
            res["codigo_ejecucion"] = ejecucion.codigo_ejecucion
            return res
        except Exception as e:
            ultimo_error = f"{type(e).__name__}: {str(e)}"
            log.warning(f"Error en {flujo}/{proceso} (intento {intento}/{max_reintentos}): {ultimo_error}")
            if intento < max_reintentos:
                time.sleep(1)

    duracion = int((time.time() - inicio) * 1000)
    finalizar_ejecucion(db, ejecucion, estado="FALLIDO", error=ultimo_error, duracion_ms=duracion)
    return {
        "ok": False,
        "error": ultimo_error,
        "codigo_ejecucion": ejecucion.codigo_ejecucion,
        "estado": "FALLIDO"
    }
