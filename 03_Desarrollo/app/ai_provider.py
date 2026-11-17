"""Proveedor de IA con cadena de respaldo (todo gratuito).

Orden configurable con AI_PROVIDER_ORDER (por defecto gemini -> groq -> ollama):
  * Gemini (nivel gratuito, multimodal)           -> GEMINI_API_KEY
  * Groq (nivel gratuito, texto)                  -> GROQ_API_KEY
  * Ollama local (texto: llama3/gemma/qwen; visión: llava/llama3.2-vision) -> OLLAMA_BASE_URL
  * Plan B final: `AIResult(ok=False, provider="local")` y quien llama usa sus reglas locales.

Los proveedores externos solo se usan si AI_EXTERNAL_ALLOWED=true. Ollama corre en la propia
infraestructura, por lo que es el único permitido cuando el dato personal no puede salir.
El módulo nunca lanza excepciones: una falla del proveedor jamás bloquea el sistema.
"""
import base64
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from app import config

log = logging.getLogger("ai_provider")

EXTERNAL = {"gemini", "groq"}
LOCAL = {"ollama"}


@dataclass
class AIResult:
    ok: bool
    provider: str  # "gemini" | "groq" | "ollama" | "local"
    text: str = ""
    data: Optional[Any] = None
    error: str = ""
    attempts: int = 0
    latency_ms: int = 0
    meta: dict = field(default_factory=dict)


_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        from google.genai import types
        _gemini_client = genai.Client(
            api_key=config.GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=int(config.AI_TIMEOUT_SECONDS * 1000)),
        )
    return _gemini_client


def _configured(name: str) -> bool:
    if name == "gemini":
        return bool(config.GEMINI_API_KEY)
    if name == "groq":
        return bool(config.GROQ_API_KEY)
    if name == "ollama":
        return bool(config.OLLAMA_BASE_URL)
    return False


def active_providers(*, local_only: bool = False, vision: bool = False) -> List[str]:
    """Proveedores utilizables ahora, en orden de preferencia."""
    result = []
    for name in config.AI_PROVIDER_ORDER:
        if not _configured(name):
            continue
        if name in EXTERNAL and (local_only or not config.AI_EXTERNAL_ALLOWED):
            continue
        if vision and name == "groq":  # Groq se usa solo para texto en este proyecto
            continue
        result.append(name)
    return result


def is_available(*, local_only: bool = False, vision: bool = False) -> bool:
    return bool(active_providers(local_only=local_only, vision=vision))


def status() -> dict:
    providers = active_providers()
    if not providers:
        reason = "Ningún proveedor configurado (GEMINI_API_KEY / GROQ_API_KEY / OLLAMA_BASE_URL): se usa Plan B (reglas locales)"
        if not config.AI_EXTERNAL_ALLOWED and any(_configured(p) for p in EXTERNAL):
            reason = "AI_EXTERNAL_ALLOWED=false: procesamiento solo local"
        return {"provider": "local", "available": False, "chain": [], "reason": reason}
    return {
        "provider": providers[0],
        "available": True,
        "chain": providers,
        "models": {"gemini": config.GEMINI_MODEL, "groq": config.GROQ_MODEL,
                   "ollama": config.OLLAMA_MODEL, "ollama_vision": config.OLLAMA_VISION_MODEL},
        "external_allowed": config.AI_EXTERNAL_ALLOWED,
    }


def _extract_json(text: str):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


# ----------------------------- llamadas por proveedor -----------------------------

def _call_gemini(prompt, json_mode, images, system, temperature) -> str:
    from google.genai import types
    parts: list = [types.Part.from_bytes(data=d, mime_type=m) for d, m in images or []]
    parts.append(prompt)
    cfg = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system,
        response_mime_type="application/json" if json_mode else None,
    )
    resp = _get_gemini_client().models.generate_content(model=config.GEMINI_MODEL, contents=parts, config=cfg)
    return (resp.text or "").strip()


def _call_groq(prompt, json_mode, images, system, temperature) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body: Dict[str, Any] = {"model": config.GROQ_MODEL, "messages": messages, "temperature": temperature}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    r = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json=body,
        headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
        timeout=config.AI_TIMEOUT_SECONDS,
    )
    r.raise_for_status()
    return (r.json()["choices"][0]["message"]["content"] or "").strip()


def _call_ollama(prompt, json_mode, images, system, temperature) -> str:
    model = config.OLLAMA_VISION_MODEL if images else config.OLLAMA_MODEL
    msg: Dict[str, Any] = {"role": "user", "content": prompt}
    if images:
        msg["images"] = [base64.b64encode(d).decode() for d, _ in images if _.startswith("image/")]
    messages = ([{"role": "system", "content": system}] if system else []) + [msg]
    body: Dict[str, Any] = {"model": model, "messages": messages, "stream": False,
                            "options": {"temperature": temperature}}
    if json_mode:
        body["format"] = "json"
    r = httpx.post(config.OLLAMA_BASE_URL.rstrip("/") + "/api/chat", json=body, timeout=config.AI_TIMEOUT_SECONDS * 4)
    r.raise_for_status()
    return (r.json().get("message", {}).get("content") or "").strip()


_CALLERS = {"gemini": _call_gemini, "groq": _call_groq, "ollama": _call_ollama}


def generate(prompt: str, *, json_mode: bool = False, images: Optional[list] = None,
             system: Optional[str] = None, temperature: float = 0.2,
             local_only: bool = False) -> AIResult:
    """Recorre la cadena de proveedores. `images` = lista de (bytes, mime_type). Nunca lanza excepción.

    `local_only=True` restringe la llamada a proveedores locales (datos personales que no pueden salir).
    """
    vision = bool(images)
    chain = active_providers(local_only=local_only, vision=vision)
    if not chain:
        return AIResult(ok=False, provider="local", error=status()["reason"])

    errors: List[str] = []
    start = time.time()
    total_attempts = 0
    for name in chain:
        for attempt in range(1, config.AI_MAX_RETRIES + 2):
            total_attempts += 1
            try:
                text = _CALLERS[name](prompt, json_mode, images, system, temperature)
                if not text:
                    raise ValueError("Respuesta vacía del modelo")
                data = _extract_json(text) if json_mode else None
                return AIResult(ok=True, provider=name, text=text, data=data, attempts=total_attempts,
                                latency_ms=int((time.time() - start) * 1000),
                                meta={"fallbacks": errors})
            except Exception as e:  # cuota (429), red, JSON inválido, etc.
                err = f"{name}: {type(e).__name__}: {str(e)[:200]}"
                log.warning("Intento %s/%s falló (%s)", attempt, config.AI_MAX_RETRIES + 1, err)
                quota = "429" in err or "RESOURCE_EXHAUSTED" in err
                if quota:  # cuota agotada: no insistir, pasar al siguiente proveedor
                    errors.append(err)
                    break
                if attempt > config.AI_MAX_RETRIES:
                    errors.append(err)
                else:
                    time.sleep(min(config.AUTOMATION_BACKOFF_SECONDS * attempt, 4))
    return AIResult(ok=False, provider="local", error=" | ".join(errors), attempts=total_attempts,
                    latency_ms=int((time.time() - start) * 1000), meta={"fallbacks": errors})
