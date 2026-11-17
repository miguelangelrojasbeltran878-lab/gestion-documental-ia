"""Chatbot con LangGraph: memoria por conversación, uso de herramientas y Plan B.

Grafo:   recuperar (herramientas)  ->  responder (LLM gratuito)  ->  fin
  * Memoria: `MemorySaver` conserva el historial por `thread_id` (usuario/sesión).
  * Herramientas: consultar ticket por código, listar documentos de visión del usuario y gastos registrados.
  * Plan B: si ningún modelo responde, `ai_module.answer_file_chatbot_question` (motor semántico local de los
    cortes anteriores) contesta, de modo que el chatbot mantiene el comportamiento previo.
  * Privacidad: lo que se envía al modelo pasa por `privacy.anonimizar_texto`.
"""
import operator
import re
from typing import Annotated, Any, Dict, List, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app import ai_module, ai_provider, models, privacy

MAX_TURNOS_MEMORIA = 8


class EstadoChat(TypedDict):
    messages: Annotated[List[Dict[str, str]], operator.add]
    pregunta: str
    contexto: str
    herramientas: List[str]
    respuesta: str
    proveedor: str


# ----------------------------------------------------------------------------- herramientas

def tool_consultar_ticket(db: Session, codigo: str) -> str:
    t = db.query(models.Ticket).filter(models.Ticket.codigo_seguimiento == codigo.upper()).first()
    if not t:
        return f"No existe un ticket con código {codigo}."
    return (f"Ticket {t.codigo_seguimiento}: «{t.titulo}», estado {t.estado}, prioridad {t.prioridad}, "
            f"creado {t.fecha_creacion:%Y-%m-%d %H:%M}.")


def tool_listar_documentos(db: Session, user: models.UsuarioAgente, limite: int = 5) -> str:
    q = db.query(models.DocumentoVision)
    if user.rol != "Administrador":
        q = q.filter(models.DocumentoVision.cargado_por == user.correo_electronico)
    docs = q.order_by(models.DocumentoVision.fecha_carga.desc()).limit(limite).all()
    if not docs:
        return "El usuario no tiene documentos procesados por visión."
    return "\n".join(f"- {d.codigo}: {d.tipo_documento or 'sin tipo'}, confianza {d.confianza}, estado {d.estado}" for d in docs)


def tool_listar_gastos(db: Session, limite: int = 5) -> str:
    gastos = db.query(models.Gasto).order_by(models.Gasto.fecha_registro.desc()).limit(limite).all()
    if not gastos:
        return "Aún no hay gastos registrados desde facturas."
    return "\n".join(f"- {g.proveedor or 'Proveedor s/d'} NIT {g.nit or 's/d'}: ${g.monto_total:,.0f} {g.moneda} ({g.fecha_documento or 's/f'})" for g in gastos)


def tool_resumen_tickets(db: Session, limite: int = 5) -> str:
    """Conteos por estado/prioridad y los casos abiertos de prioridad alta (datos reales de la BD)."""
    T = models.Ticket
    por_estado = {e: db.query(T).filter(T.estado == e).count() for e in ["Abierto", "En Proceso", "Resuelto", "Cerrado"]}
    por_prio = {p: db.query(T).filter(T.prioridad == p).count() for p in ["Alta", "Media", "Baja"]}
    lineas = [f"Total de tickets: {db.query(T).count()}.",
              "Por estado: " + ", ".join(f"{k} {v}" for k, v in por_estado.items()) + ".",
              "Por prioridad: " + ", ".join(f"{k} {v}" for k, v in por_prio.items()) + "."]
    urgentes = (db.query(T).filter(T.prioridad == "Alta", T.estado.in_(["Abierto", "En Proceso"]))
                .order_by(T.fecha_creacion.desc()).limit(limite).all())
    if urgentes:
        lineas.append("Casos de prioridad alta sin resolver:")
        lineas += [f"- {t.codigo_seguimiento}: «{t.titulo}» ({t.estado})" for t in urgentes]
    return "\n".join(lineas)


def tool_pendientes_vision(db: Session, limite: int = 5) -> str:
    docs = (db.query(models.DocumentoVision).filter(models.DocumentoVision.estado == "PENDIENTE_REVISION")
            .order_by(models.DocumentoVision.fecha_carga.desc()).limit(limite).all())
    total = db.query(models.DocumentoVision).filter(models.DocumentoVision.estado == "PENDIENTE_REVISION").count()
    if not total:
        return "No hay documentos de visión pendientes de revisión."
    return f"{total} documento(s) pendientes de revisión humana (se revisan en /vision):\n" + "\n".join(
        f"- {d.codigo}: {d.tipo_documento or 'sin tipo'}, confianza {d.confianza}" for d in docs)


# ----------------------------------------------------------------------------- nodos

def _nodo_recuperar(state: EstadoChat, config: RunnableConfig) -> Dict[str, Any]:
    cfg = config.get("configurable", {})
    db: Session = cfg["db"]
    user = cfg.get("user")
    q = state["pregunta"]
    q_low = q.lower()
    partes: List[str] = []
    usadas: List[str] = []

    m = re.search(r"(TIK-\d{4}-[A-Za-z0-9]+|TCK-\d{4}-[A-Za-z0-9]+)", q, re.I)
    if m:
        partes.append(tool_consultar_ticket(db, m.group(1)))
        usadas.append("consultar_ticket")
    if user and any(k in q_low for k in ["mis documentos", "mis facturas", "mis fotos", "documentos procesados", "última foto", "ultima foto", "mis imágenes", "mis imagenes"]):
        partes.append("Documentos de visión del usuario:\n" + tool_listar_documentos(db, user))
        usadas.append("listar_documentos")
    if any(k in q_low for k in ["gasto", "compras", "facturas registradas"]):
        partes.append("Gastos registrados:\n" + tool_listar_gastos(db))
        usadas.append("listar_gastos")
    if any(k in q_low for k in ["ticket", "abierto", "prioridad", "resumen", "operación", "operacion", "carga", "urgente", "hoy"]):
        partes.append("Estado de la mesa de ayuda:\n" + tool_resumen_tickets(db))
        usadas.append("resumen_tickets")
    if any(k in q_low for k in ["pendiente", "revisión", "revision", "por revisar", "visión", "vision"]):
        partes.append("Visión por computador:\n" + tool_pendientes_vision(db))
        usadas.append("pendientes_vision")
    if cfg.get("contexto_extra"):
        partes.append(cfg["contexto_extra"])
    return {"contexto": "\n".join(partes), "herramientas": usadas}


def _nodo_responder(state: EstadoChat, config: RunnableConfig) -> Dict[str, Any]:
    cfg = config.get("configurable", {})
    historial = state["messages"][-(MAX_TURNOS_MEMORIA * 2):]
    previo = "\n".join(f"{'Usuario' if m['role'] == 'user' else 'Asistente'}: {m['content']}" for m in historial[:-1])
    prompt = (
        "Eres el asistente del sistema de gestión documental y mesa de ayuda. Responde en español, claro y conciso, "
        "usando SOLO los datos del contexto; si no los tienes, dilo y explica cómo obtenerlos.\n"
        "Funciones del sistema: radicar solicitudes, subir fotos de facturas en /vision (extrae emisor, NIT, fecha, total y "
        "pide revisión humana si la confianza es baja), consultar tickets y resumir expedientes.\n\n"
        f"Conversación previa:\n{privacy.anonimizar_texto(previo) or '(inicio)'}\n\n"
        f"Contexto de herramientas:\n{privacy.anonimizar_texto(state['contexto']) or '(ninguno)'}\n\n"
        f"Pregunta actual: {privacy.anonimizar_texto(state['pregunta'])}"
    )
    res = ai_provider.generate(prompt)
    if res.ok and res.text:
        texto, proveedor = res.text.strip(), res.provider
    else:  # Plan B: motor local de los cortes anteriores
        base = ai_module.answer_file_chatbot_question(state["pregunta"], cfg.get("files_data", []), cfg.get("ticket_context"))
        texto = base + (f"\n\n{state['contexto']}" if state["contexto"] else "")
        proveedor = "local"
    return {"respuesta": texto, "proveedor": proveedor,
            "messages": [{"role": "assistant", "content": texto}]}


def _construir_grafo():
    g = StateGraph(EstadoChat)
    g.add_node("recuperar", _nodo_recuperar)
    g.add_node("responder", _nodo_responder)
    g.add_edge(START, "recuperar")
    g.add_edge("recuperar", "responder")
    g.add_edge("responder", END)
    return g.compile(checkpointer=MemorySaver())


_GRAFO = _construir_grafo()


def conversar(db: Session, user: models.UsuarioAgente, pregunta: str, *, thread_id: str,
              contexto_extra: str = "", files_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Ejecuta un turno del chatbot recordando la conversación del `thread_id`."""
    resultado = _GRAFO.invoke(
        {"messages": [{"role": "user", "content": pregunta}], "pregunta": pregunta},
        config={"configurable": {"thread_id": thread_id, "db": db, "user": user,
                                 "contexto_extra": contexto_extra, "files_data": files_data or []}},
    )
    return {"respuesta": resultado["respuesta"], "proveedor": resultado["proveedor"],
            "herramientas": resultado.get("herramientas", []),
            "turnos_en_memoria": len(resultado["messages"]) // 2}


def olvidar(thread_id: str) -> None:
    try:
        _GRAFO.checkpointer.delete_thread(thread_id)  # type: ignore[union-attr]
    except Exception:
        pass
