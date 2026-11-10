import os

ai_path = r'c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\03_Desarrollo\app\ai_module.py'
with open(ai_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Replace the beginning of answer_file_chatbot_question to check Gemini first
old_fn_start = '''def answer_file_chatbot_question(pregunta: str, files_data: List[Dict[str, Any]], ticket_context: Dict[str, Any] = None) -> str:
    """
    Chatbot Inteligente de Consulta y Resumen Documental.
    Entrega respuestas claras, bien estructuradas, con viñetas, hallazgos reales y resúmenes ejecutivos.
    """'''

new_fn_start = '''def answer_file_chatbot_question(pregunta: str, files_data: List[Dict[str, Any]], ticket_context: Dict[str, Any] = None) -> str:
    """
    Chatbot Inteligente de Consulta y Resumen Documental.
    Integra primero inferencia contextual directa con Google Gemini (nivel gratuito),
    y conmuta transparentemente a un motor semántico local cuando la API no esté configurada o falle.
    """
    q = (pregunta or "").strip()
    q_low = q.lower()
    total = len(files_data)

    if total == 0:
        return (
            "🤖 **Aún no hay archivos cargados para analizar.**\\n\\n"
            "Por favor sube tus archivos (`.pdf`, `.xlsx`, `.docx` o `.jpg`) en el área de carga "
            "o pulsa el botón **«Generar Lote Demo de 30 Archivos»** para que pueda leer su contenido y responderte."
        )

    # 1. INTENTO DE RESPUESTA MEDIANTE IA GENERATIVA (GEMINI) CON CONTEXTO COMPLETO
    try:
        from app import ai_provider
        if ai_provider.is_available():
            context_blocks = []
            for idx, f in enumerate(files_data[:30], start=1):
                txt_part = (f.get("deep_text") or f.get("summary") or "")[:1200]
                context_blocks.append(
                    f"--- ARCHIVO #{idx} ---\\n"
                    f"Nombre: {f.get('filename')} (Formato: {f.get('extension')}, Tamaño: {f.get('size_kb')} KB)\\n"
                    f"Prioridad preliminar: {f.get('priority', 'Media')}\\n"
                    f"Contenido extraído / Tabla: {txt_part}\\n"
                )
            archivos_texto = "\\n".join(context_blocks)
            t_info = f"Ticket actual: {ticket_context.get('codigo')} - {ticket_context.get('titulo')}" if ticket_context else "Lote en análisis"

            prompt_gemini = f"""Eres el Asistente Experto en Gestión y Análisis Documental del sistema.
El usuario tiene cargados {total} archivo(s) de soporte ({t_info}).
Analiza detenidamente la siguiente información extraída de los documentos:

{archivos_texto}

Pregunta del usuario: «{q}»

Instrucciones para tu respuesta:
1. Responde de forma muy clara, concisa, profesional y estructurada con viñetas y texto resaltado en negritas.
2. Si te piden un resumen, extrae los datos clave reales (proveedores, importes de facturas, totales de tablas Excel, conclusiones de informes Word, alertas de capturas).
3. Si preguntan por un archivo específico, enfócate exactamente en ese documento.
4. Responde en español y no inventes datos que no estén presentes en el contexto anterior."""

            res_ia = ai_provider.generate(
                prompt=prompt_gemini,
                system="Eres un analista documental senior de clase mundial que entrega respuestas directas, legibles y ejecutivas."
            )
            if res_ia.ok and res_ia.text:
                return res_ia.text.strip()
    except Exception as e:
        # Fallback silencioso al motor heurístico local
        pass
'''

if old_fn_start in code:
    code = code.replace(old_fn_start, new_fn_start)
    with open(ai_path, 'w', encoding='utf-8') as f:
        f.write(code)
    print("Chatbot successfully upgraded with Gemini contextual engine + local fallback!")
else:
    print("Warning: old_fn_start not found in ai_module.py.")
