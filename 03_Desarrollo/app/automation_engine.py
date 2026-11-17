"""Motor de automatización propio en código (reemplazo de los flujos n8n / Make).

Responsabilidades:
  * Registro de flujos (`FLUJOS`): inventario ejecutable con disparador, pasos, servicios y resultado.
  * Ejecución con reintentos (retroceso exponencial), manejo de errores y registro de cada ejecución
    (fecha, usuario, entrada, resultado, error, intentos, duración, proveedor de IA).
  * Ejecución de flujos programados (cron) a través de `app.scheduler`.
"""
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app import config, models

log = logging.getLogger("automation_engine")

# Errores de validación del usuario: reintentar no los arregla.
NO_REINTENTABLES: Tuple[type, ...] = (ValueError, PermissionError)


@dataclass
class FlujoDef:
    """Definición de un flujo (equivale a un escenario de n8n)."""
    id: str
    nombre: str
    disparador: str
    pasos: List[str]
    servicios: List[str]
    resultado: str
    tipo: str = "evento"            # evento | cron | manual
    origen_n8n: str = ""            # nodo/escenario que reemplaza
    cron: Optional[Dict[str, Any]] = None   # p. ej. {"minutes": 15}
    ejecutar: Optional[Callable[[Session], Dict[str, Any]]] = None  # flujos programados / manuales
    solo_admin: bool = True


FLUJOS: Dict[str, FlujoDef] = {}


def registrar_flujo(flujo: FlujoDef) -> FlujoDef:
    FLUJOS[flujo.id] = flujo
    return flujo


# ------------------------------------------------------------------ registro de ejecución

def registrar_inicio_ejecucion(
    db: Session,
    flujo: str,
    proceso: str,
    usuario: Optional[str] = "sistema",
    id_ticket: Optional[int] = None,
    entrada_resumen: Optional[str] = None,
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
        fecha_inicio=datetime.utcnow(),
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
    duracion_ms: int = 0,
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
    max_reintentos: Optional[int] = None,
) -> Dict[str, Any]:
    """Ejecuta `func` con reintentos (backoff exponencial), cronómetro y persistencia de auditoría.

    Estados finales: EXITOSO | PLAN_B (el servicio respondió con respaldo local) | FALLIDO.
    Los ValueError/PermissionError (errores de validación) no se reintentan y se relanzan al llamador
    después de registrarse, para que la API pueda responder 400/403 con el mensaje real.
    """
    max_reintentos = max_reintentos or config.AUTOMATION_MAX_ATTEMPTS
    ejecucion = registrar_inicio_ejecucion(db, flujo, proceso, usuario, id_ticket, entrada_resumen)
    inicio = time.time()
    ultimo_error: Optional[str] = None
    excepcion_final: Optional[BaseException] = None

    for intento in range(1, max_reintentos + 1):
        ejecucion.intentos = intento
        db.commit()
        try:
            res = func()
            duracion = int((time.time() - inicio) * 1000)
            if not isinstance(res, dict):
                res = {"resultado": res}
            res_str = json.dumps(res, ensure_ascii=False, default=str)
            prov = res.get("proveedor_ia")
            est = "PLAN_B" if res.get("plan_b_utilizado") else "EXITOSO"
            finalizar_ejecucion(db, ejecucion, estado=est, resultado=res_str, proveedor_ia=prov, duracion_ms=duracion)
            res["codigo_ejecucion"] = ejecucion.codigo_ejecucion
            return res
        except Exception as e:  # noqa: BLE001 - el motor debe capturar todo y registrarlo
            db.rollback()
            ultimo_error = f"{type(e).__name__}: {e}"
            excepcion_final = e
            log.warning("Error en %s/%s (intento %s/%s): %s", flujo, proceso, intento, max_reintentos, ultimo_error)
            if isinstance(e, NO_REINTENTABLES):
                break
            if intento < max_reintentos:
                time.sleep(config.AUTOMATION_BACKOFF_SECONDS * (2 ** (intento - 1)))

    duracion = int((time.time() - inicio) * 1000)
    ejecucion = db.merge(ejecucion)
    finalizar_ejecucion(db, ejecucion, estado="FALLIDO", error=ultimo_error, duracion_ms=duracion)
    if isinstance(excepcion_final, NO_REINTENTABLES):
        raise excepcion_final
    return {
        "ok": False,
        "error": ultimo_error,
        "codigo_ejecucion": ejecucion.codigo_ejecucion,
        "estado": "FALLIDO",
    }


# ------------------------------------------------------------------ ejecución de flujos registrados

def ejecutar_flujo_registrado(db: Session, flujo_id: str, usuario: str = "sistema") -> Dict[str, Any]:
    """Ejecuta un flujo del registro (cron o manual) dejando el rastro completo en el log."""
    flujo = FLUJOS.get(flujo_id)
    if not flujo or not flujo.ejecutar:
        raise KeyError(f"Flujo '{flujo_id}' no existe o no es ejecutable manualmente.")
    return ejecutar_servicio_con_auditoria(
        db=db,
        flujo=flujo.id,
        proceso="EJECUCION_PROGRAMADA" if usuario == "scheduler" else "EJECUCION_MANUAL",
        func=lambda: flujo.ejecutar(db),  # type: ignore[misc]
        usuario=usuario,
        entrada_resumen=f"Disparador: {flujo.disparador}",
    )


def inventario(db: Session) -> List[Dict[str, Any]]:
    """Inventario de flujos con su última ejecución y tasa de éxito (especificación viva del motor)."""
    salida = []
    for f in FLUJOS.values():
        q = db.query(models.EjecucionAutomatizacion).filter(models.EjecucionAutomatizacion.flujo == f.id)
        total = q.count()
        ok = q.filter(models.EjecucionAutomatizacion.estado.in_(["EXITOSO", "PLAN_B"])).count()
        ultima = q.order_by(models.EjecucionAutomatizacion.fecha_inicio.desc()).first()
        salida.append({
            "id": f.id,
            "nombre": f.nombre,
            "tipo": f.tipo,
            "disparador": f.disparador,
            "pasos": f.pasos,
            "servicios": f.servicios,
            "resultado": f.resultado,
            "origen_n8n": f.origen_n8n,
            "cron": f.cron,
            "ejecutable_manual": f.ejecutar is not None,
            "ejecuciones": total,
            "tasa_exito": round(100 * ok / total, 1) if total else None,
            "ultima_ejecucion": ultima.fecha_inicio.strftime("%Y-%m-%d %H:%M:%S") if ultima and ultima.fecha_inicio else None,
            "ultimo_estado": ultima.estado if ultima else None,
        })
    return salida
