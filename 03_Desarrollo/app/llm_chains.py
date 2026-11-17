"""Cadenas LangChain (langchain-core) para las tareas de IA que antes resolvía n8n.

Cada cadena sigue el mismo patrón:  prompt  |  modelo (cadena de proveedores gratuitos)  |  parser
con `.with_fallbacks([...])` como Plan B determinista: si el modelo falla o no hay cuota, se ejecuta
la regla local y el sistema sigue respondiendo.
"""
import json
import logging
from typing import Any, Callable, Dict, List

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from app import ai_provider, privacy

log = logging.getLogger("llm_chains")

PRIORIDADES = {"Alta", "Media", "Baja"}
CATEGORIAS = {"Soporte Técnico", "Acceso y Cuentas", "Conectividad y Servidores",
              "Facturación y Auditoría", "Gestión Documental"}


class ModeloNoDisponible(RuntimeError):
    """El modelo no respondió; activa el Plan B de la cadena."""


def _modelo(json_mode: bool = False, local_only: bool = False) -> RunnableLambda:
    """Adaptador: PromptValue -> texto, usando la cadena Gemini -> Groq -> Ollama."""
    def _call(prompt_value) -> str:
        res = ai_provider.generate(prompt_value.to_string(), json_mode=json_mode, local_only=local_only)
        if not res.ok:
            raise ModeloNoDisponible(res.error or "sin proveedor")
        _call.last_provider = res.provider  # type: ignore[attr-defined]
        return res.text
    _call.last_provider = "local"  # type: ignore[attr-defined]
    runnable = RunnableLambda(_call)
    runnable.fn = _call  # type: ignore[attr-defined]
    return runnable


# ----------------------------------------------------------------------------- clasificación de tickets

_PROMPT_TICKET = ChatPromptTemplate.from_messages([
    ("system", "Eres un analista de mesa de ayuda empresarial. Responde SOLO con JSON válido."),
    ("human",
     "Clasifica la solicitud y redacta una respuesta breve, cordial y accionable en español.\n"
     "Prioridad: Alta | Media | Baja. Categoría: Soporte Técnico | Acceso y Cuentas | "
     "Conectividad y Servidores | Facturación y Auditoría | Gestión Documental.\n"
     "Base de conocimiento disponible: {kb}\n\n"
     "Título: {titulo}\nDescripción: {descripcion}\n\n"
     'JSON: {{"prioridad": "...", "categoria": "...", "respuesta": "...", "confianza": 0.0}}'),
])


def clasificar_ticket(titulo: str, descripcion: str, kb_titulos: List[str],
                      regla_local: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    """Clasificación con LLM; si falla, `regla_local()` (reglas heurísticas) responde igual."""
    modelo = _modelo(json_mode=True)

    def _parse(texto: str) -> Dict[str, Any]:
        data = json.loads(texto)
        if data.get("prioridad") not in PRIORIDADES or data.get("categoria") not in CATEGORIAS:
            raise ValueError("Clasificación fuera de catálogo")
        base = regla_local()
        base.update({
            "prioridad_sugerida": data["prioridad"],
            "categoria_sugerida": data["categoria"],
            "respuesta_sugerida": str(data.get("respuesta") or base["respuesta_sugerida"]),
            "score_confianza": round(float(data.get("confianza") or 0.8), 2),
            "proveedor_ia": getattr(modelo.fn, "last_provider", "llm"),  # type: ignore[attr-defined]
        })
        return base

    cadena = (_PROMPT_TICKET | modelo | StrOutputParser() | RunnableLambda(_parse)).with_fallbacks(
        [RunnableLambda(lambda _: {**regla_local(), "plan_b_utilizado": True, "proveedor_ia": "local_reglas"})]
    )
    # El texto del cliente viaja anonimizado a servicios externos (Ley 1581).
    return cadena.invoke({
        "titulo": privacy.anonimizar_texto(titulo),
        "descripcion": privacy.anonimizar_texto(descripcion)[:1500],
        "kb": "; ".join(kb_titulos[:12]) or "ninguna",
    })


# ----------------------------------------------------------------------------- resumen de lotes

_PROMPT_LOTE = ChatPromptTemplate.from_messages([
    ("system", "Eres un auditor documental. Escribe resúmenes ejecutivos claros en español."),
    ("human", "Resume en máximo 5 líneas los hallazgos de estos {n} documentos de un expediente "
              "(prioriza importes, vencimientos y alertas):\n{detalle}"),
])


def resumir_lote(detalles: List[str], resumen_local: str) -> Dict[str, Any]:
    """Resumen ejecutivo del lote con LLM; fallback: resumen determinista ya calculado."""
    modelo = _modelo()
    cadena = (_PROMPT_LOTE | modelo | StrOutputParser()).with_fallbacks(
        [RunnableLambda(lambda _: resumen_local)]
    )
    detalle = privacy.anonimizar_texto("\n".join(detalles))[:6000]
    texto = cadena.invoke({"n": len(detalles), "detalle": detalle})
    usado_modelo = texto != resumen_local
    return {"resumen": texto, "proveedor_ia": getattr(modelo.fn, "last_provider", "local") if usado_modelo else "local_reglas",  # type: ignore[attr-defined]
            "plan_b_utilizado": not usado_modelo}
