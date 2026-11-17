"""Tareas programadas (cron) del motor de automatización, con APScheduler.

Se inicia en el arranque de la app (lifespan). Con varios workers de uvicorn cada proceso tendría su
propio scheduler: en el despliegue gratuito se usa un único worker (ver Dockerfile / render.yaml).
"""
import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from app import automation_engine, automation_flows  # noqa: F401  (registra los flujos)
from app import config
from app.database import SessionLocal

log = logging.getLogger("scheduler")
_scheduler: Optional[BackgroundScheduler] = None


def _job(flujo_id: str) -> None:
    db = SessionLocal()
    try:
        automation_engine.ejecutar_flujo_registrado(db, flujo_id, usuario="scheduler")
    except Exception as e:  # noqa: BLE001 - un job nunca debe tumbar el scheduler
        log.error("Job %s falló: %s", flujo_id, e)
    finally:
        db.close()


def iniciar() -> Optional[BackgroundScheduler]:
    global _scheduler
    if not config.SCHEDULER_ENABLED or _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone="America/Bogota")
    for f in automation_engine.FLUJOS.values():
        if f.tipo == "cron" and f.cron and f.ejecutar:
            trigger = "interval" if "minutes" in f.cron else "cron"
            _scheduler.add_job(_job, trigger, args=[f.id], id=f.id, replace_existing=True,
                               max_instances=1, coalesce=True, **f.cron)
    _scheduler.start()
    log.info("Scheduler iniciado con %s tareas", len(_scheduler.get_jobs()))
    return _scheduler


def detener() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
