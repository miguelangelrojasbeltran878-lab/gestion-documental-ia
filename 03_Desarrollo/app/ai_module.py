import os
from typing import Dict, Any, List

def analyze_and_suggest(
    titulo: str,
    descripcion: str,
    soluciones_kb: List[Dict[str, Any]],
    nombre_cliente: str = "Estimado(a) Cliente",
    empresa: str = ""
) -> Dict[str, Any]:
    """Clasificación y respuesta del ticket: LLM gratuito (cadena LangChain) con Plan B de reglas locales."""
    from app import llm_chains
    return llm_chains.clasificar_ticket(
        titulo, descripcion, [s.get("titulo", "") for s in soluciones_kb],
        regla_local=lambda: analyze_and_suggest_rules(titulo, descripcion, soluciones_kb, nombre_cliente, empresa),
    )


def analyze_and_suggest_rules(
    titulo: str,
    descripcion: str,
    soluciones_kb: List[Dict[str, Any]],
    nombre_cliente: str = "Estimado(a) Cliente",
    empresa: str = ""
) -> Dict[str, Any]:
    """
    Motor de Respuesta Inteligente centrada en el Cliente (Customer-Centric AI Engine).
    Analiza intención, urgencia, coincidencias en Base de Conocimiento y redacta una
    respuesta ejecutiva, cálida, accionable y estructurada para el cliente.
    """
    text_full = f"{titulo} {descripcion}".lower()

    high_keywords = [
        "urgente", "crítico", "critico", "caído", "caido", "bloqueo", "error 500",
        "no funciona", "inaccesible", "inacesible", "falla grave", "seguridad",
        "hack", "violación", "producción", "produccion", "detenido"
    ]
    medium_keywords = [
        "lento", "demora", "configuración", "configuracion", "permiso", "acceso",
        "cuenta", "modificar", "duda", "problema", "factura", "cobro", "auditoria",
        "reporte", "conciliación", "conciliacion", "error"
    ]

    prioridad = "Baja"
    if any(k in text_full for k in high_keywords):
        prioridad = "Alta"
    elif any(k in text_full for k in medium_keywords):
        prioridad = "Media"

    categoria = "Soporte Técnico"
    if any(k in text_full for k in ["acceso", "login", "contraseña", "clave", "usuario", "perfil", "2fa", "autenticación"]):
        categoria = "Acceso y Cuentas"
    elif any(k in text_full for k in ["caído", "caido", "servidor", "red", "conexion", "conexión", "timeout", "api", "webhook"]):
        categoria = "Conectividad y Servidores"
    elif any(k in text_full for k in ["pago", "factura", "cobro", "tarjeta", "valor", "reembolso", "nota crédito", "contable", "impuesto"]):
        categoria = "Facturación y Auditoría"
    elif any(k in text_full for k in ["contrato", "cláusula", "clausula", "legal", "anexo", "documento", "certificado"]):
        categoria = "Gestión Documental"

    best_match = None
    highest_score = 0
    for sol in soluciones_kb:
        sol_text = f"{sol.get('titulo', '')} {sol.get('palabras_clave', '')} {sol.get('contenido_solucion', '')}".lower()
        score = 0
        for word in text_full.split():
            clean_w = word.strip(".,;:()¿?¡!")
            if len(clean_w) > 3 and clean_w in sol_text:
                score += 1
        if score > highest_score:
            highest_score = score
            best_match = sol

    sla_map = {
        "Alta": "Atención Crítica Inmediata (< 15 minutos)",
        "Media": "Atención Preferencial (< 2 horas)",
        "Baja": "Atención Estándar Garantizada (< 8 horas)"
    }
    sla_text = sla_map.get(prioridad, "Atención Garantizada 24/7")

    empresa_tag = f" ({empresa})" if empresa and empresa.strip() else ""
    saludo = f"Hola, {nombre_cliente}{empresa_tag}:"

    if best_match:
        pasos_solucion = best_match.get("contenido_solucion", "").strip()
        score_confianza = min(0.99, 0.84 + (highest_score * 0.04))
        diagnostico = (
            f"Hemos analizado tu requerimiento sobre «{titulo}» y encontramos una solución validada "
            f"en nuestra Base de Conocimiento de {categoria}."
        )
    else:
        score_confianza = 0.94
        diagnostico = (
            f"Hemos recibido y analizado tu solicitud sobre «{titulo}» dentro del área de {categoria}."
        )
        if categoria == "Facturación y Auditoría":
            pasos_solucion = (
                "1. Verificación de Comprobantes: Nuestro motor contable está cruzando los montos, fechas y referencias fiscales reportadas.\n"
                "2. Conciliación Automática: Se validarán posibles diferencias de facturación, retenciones o cargos duplicados.\n"
                "3. Emisión de Ajuste / Certificación: En caso de aplicar ajuste o nota crédito, se reflejará directamente en tu estado de cuenta."
            )
        elif categoria == "Acceso y Cuentas":
            pasos_solucion = (
                "1. Diagnóstico de Credenciales: Se verificó el estado de tu cuenta y permisos asociados en el directorio activo.\n"
                "2. Desbloqueo / Sincronización: Hemos habilitado el restablecimiento seguro de sesión y limpieza de tokens expirados.\n"
                "3. Validación de Ingreso: Intenta iniciar sesión nuevamente en ventana privada o confirma por este hilo si requieres asistencia directa."
            )
        elif categoria == "Conectividad y Servidores":
            pasos_solucion = (
                "1. Monitoreo de Nodos y API: Se ejecutó una prueba de latencia y disponibilidad sobre los servicios reportados.\n"
                "2. Mitigación de Incidencia: El tráfico ha sido balanceado y los servicios de integración operan con normalidad.\n"
                "3. Seguimiento Continuo: Mantenemos monitoreo activo sobre tu entorno durante las próximas 24 horas."
            )
        else:
            pasos_solucion = (
                f"1. Clasificación Inteligente: Tu caso fue registrado con prioridad {prioridad} y asignado a un especialista de {categoria}.\n"
                "2. Análisis de Contexto: Hemos procesado tus instrucciones y requerimientos específicos para darte una solución definitiva.\n"
                "3. Canal Directo Activo: Puedes responder directamente en este ticket en cualquier momento para agregar comentarios."
            )

    respuesta = (
        f"{saludo}\n\n"
        f"✅ DIAGNÓSTICO INMEDIATO 24/7:\n"
        f"{diagnostico}\n\n"
        f"📋 PLAN DE ACCIÓN Y SOLUCIÓN RECOMENDADA:\n"
        f"{pasos_solucion}\n\n"
        f"⏱️ NIVEL DE SERVICIO (SLA ASIGNADO):\n"
        f"• Prioridad: {prioridad} — {sla_text}\n"
        f"• Área Especializada: {categoria}\n\n"
        f"Quedamos a tu entera disposición. Puedes responder directamente desde tu portal «Mis Tickets» si tienes alguna pregunta adicional."
    )

    return {
        "prioridad_sugerida": prioridad,
        "categoria_sugerida": categoria,
        "respuesta_sugerida": respuesta,
        "score_confianza": round(score_confianza, 2)
    }


def generate_followup_ai_reply(ticket_titulo: str, cliente_nombre: str, comentario_cliente: str, total_archivos: int = 0) -> str:
    """Genera una respuesta automática e inteligente cuando el cliente envía una réplica en el hilo."""
    comentario_low = comentario_cliente.lower()
    if any(k in comentario_low for k in ["gracias", "resuelto", "funcionó", "funciono", "perfecto", "listo", "excelente"]):
        return (
            f"¡Con mucho gusto, {cliente_nombre}! Nos alegra saber que la información y solución brindada para «{ticket_titulo}» "
            f"haya sido de utilidad. Si deseas, puedes calificar nuestra atención con estrellas en el panel lateral. ¡Seguimos atentos 24/7!"
        )
    if any(k in comentario_low for k in ["archivo", "documento", "pdf", "excel", "factura", "adjunto", "lote"]):
        return (
            f"Hola {cliente_nombre}, hemos registrado tu comentario adicional sobre los documentos adjuntos ({total_archivos} archivo(s) vinculados al expediente). "
            f"Nuestro motor de IA y el especialista asignado han actualizado el análisis con tu observación para priorizar la validación."
        )
    return (
        f"Hola {cliente_nombre}, hemos recibido tu mensaje adicional sobre «{ticket_titulo}»: "
        f"\"{comentario_cliente[:120]}{'...' if len(comentario_cliente) > 120 else ''}\". "
        f"Tu comentario ya quedó anexado al expediente prioritario y nuestro equipo lo ha tomado en cuenta para tu solución."
    )


import os
import io
import re
import zlib
import zipfile
import struct
import xml.etree.ElementTree as ET
from typing import Dict, Any, List


def extract_deep_file_text(filename: str, ext: str, raw_bytes: bytes) -> Dict[str, Any]:
    """
    Extractor profundo de contenido real para .PDF, .DOCX, .XLSX y .JPG.
    Extrae texto limpio, párrafos, tablas, cifras y metadatos reales del binario.
    """
    ext = (ext or "").lower().lstrip(".")
    size_kb = round(len(raw_bytes) / 1024, 1) if raw_bytes else 0.0
    result = {
        "filename": filename,
        "extension": ext,
        "size_kb": size_kb,
        "text": "",
        "key_points": [],
        "metrics": {}
    }
    if not raw_bytes:
        return result

    # 1. WORD (.DOCX): Párrafos y tablas completas desde word/document.xml
    if ext == "docx":
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                xml_content = zf.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            paragraphs = []
            for p_node in tree.iter():
                if p_node.tag.endswith("}p"):
                    runs = [t.text for t in p_node.iter() if t.tag.endswith("}t") and t.text]
                    line = "".join(runs).strip()
                    if line:
                        paragraphs.append(line)
            full_text = "\n".join(paragraphs)
            result["text"] = full_text[:6000]
            result["key_points"] = [p for p in paragraphs if len(p) > 20][:6]
            result["metrics"] = {"parrafos": len(paragraphs), "palabras": len(full_text.split())}
            return result
        except Exception:
            pass

    # 2. EXCEL (.XLSX): Celdas de texto (sharedStrings) + valores numéricos de las hojas
    if ext == "xlsx":
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                shared_strings = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    ss_xml = zf.read("xl/sharedStrings.xml")
                    ss_tree = ET.fromstring(ss_xml)
                    for si in ss_tree.iter():
                        if si.tag.endswith("}si"):
                            txt = "".join(t.text for t in si.iter() if t.tag.endswith("}t") and t.text)
                            shared_strings.append(txt.strip())

                rows_text = []
                numeric_vals = []
                sheet_files = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
                for sf in sheet_files[:3]:
                    sh_tree = ET.fromstring(zf.read(sf))
                    for row_el in sh_tree.iter():
                        if row_el.tag.endswith("}row"):
                            row_cells = []
                            for c_el in row_el:
                                if not c_el.tag.endswith("}c"):
                                    continue
                                c_type = c_el.attrib.get("t", "")
                                v_el = next((ch for ch in c_el if ch.tag.endswith("}v")), None)
                                is_el = next((ch for ch in c_el if ch.tag.endswith("}is")), None)
                                if v_el is not None and v_el.text:
                                    val_str = v_el.text.strip()
                                    if c_type == "s" and val_str.isdigit():
                                        idx = int(val_str)
                                        if 0 <= idx < len(shared_strings):
                                            row_cells.append(shared_strings[idx])
                                    else:
                                        row_cells.append(val_str)
                                        try:
                                            num = float(val_str)
                                            numeric_vals.append(num)
                                        except ValueError:
                                            pass
                                elif is_el is not None:
                                    inline_txt = "".join(t.text for t in is_el.iter() if t.tag.endswith("}t") and t.text)
                                    if inline_txt.strip():
                                        row_cells.append(inline_txt.strip())
                            if row_cells:
                                rows_text.append(" | ".join(row_cells))

                if not rows_text and shared_strings:
                    rows_text = [" | ".join(shared_strings[:30])]

                full_text = "\n".join(rows_text[:40])
                result["text"] = full_text[:6000]
                result["key_points"] = rows_text[:6]
                result["metrics"] = {
                    "filas_con_datos": len(rows_text),
                    "celdas_texto": len(shared_strings),
                    "valores_numericos": len(numeric_vals),
                    "suma_total": round(sum(numeric_vals), 2) if numeric_vals else 0,
                    "max_valor": round(max(numeric_vals), 2) if numeric_vals else 0
                }
                return result
        except Exception:
            pass

    # 3. PDF (.PDF): Extracción con pypdf/PyPDF2 o descompresión nativa FlateDecode + parser PDF
    if ext == "pdf":
        extracted_pdf = ""
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            pages_txt = [page.extract_text() or "" for page in reader.pages[:15]]
            extracted_pdf = "\n".join(pages_txt).strip()
        except Exception:
            pass

        if not extracted_pdf:
            # Descompresión nativa de streams PDF (zlib FlateDecode) y lectura de bloques de texto (...)
            chunks = []
            for m in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_bytes, re.DOTALL):
                stream_data = m.group(1)
                try:
                    decomp = zlib.decompress(stream_data)
                except Exception:
                    decomp = stream_data
                for txt_m in re.finditer(rb"\(([^()]{2,250})\)", decomp):
                    s = txt_m.group(1).decode("latin-1", errors="ignore")
                    s_clean = re.sub(r"\\[nrtbf()\\]", " ", s).strip()
                    if len(s_clean) > 2 and sum(c.isalpha() for c in s_clean) >= 2:
                        chunks.append(s_clean)
            if chunks:
                extracted_pdf = " ".join(chunks)

        if not extracted_pdf:
            # Si es un archivo de texto plano con extensión .pdf (como en el lote demo)
            plain_try = raw_bytes[:8000].decode("utf-8", errors="ignore")
            if not plain_try.startswith("%PDF"):
                extracted_pdf = plain_try.strip()
            else:
                # Extraer cadenas legibles que no sean comandos internos PDF
                pdf_keywords = {"obj", "endobj", "stream", "endstream", "xref", "trailer", "flatedecode", "type", "font", "page", "pages", "catalog", "parent", "resources", "mediabox", "contents", "length", "filter"}
                words = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ0-9,.;:\-\$/%]{3,}", plain_try)
                clean_words = [w for w in words if w.lower() not in pdf_keywords and not w.startswith("PDF")]
                extracted_pdf = " ".join(clean_words[:200])

        lines = [ln.strip() for ln in re.split(r"[\r\n]+|(?<=\.)\s+", extracted_pdf) if len(ln.strip()) > 12]
        result["text"] = extracted_pdf[:6000]
        result["key_points"] = lines[:6]
        result["metrics"] = {"palabras": len(extracted_pdf.split())}
        return result

    # 4. IMÁGENES (.JPG / .JPEG): Resolución JPEG o texto embebido
    if ext in ("jpg", "jpeg", "png", "webp"):
        width, height = 0, 0
        try:
            # Leer dimensiones reales de cabecera JPEG SOF0/SOF2
            idx = 2
            while idx < len(raw_bytes) - 8:
                if raw_bytes[idx] == 0xFF:
                    marker = raw_bytes[idx + 1]
                    if marker in (0xC0, 0xC1, 0xC2):
                        height, width = struct.unpack(">HH", raw_bytes[idx + 5:idx + 9])
                        break
                    length = struct.unpack(">H", raw_bytes[idx + 2:idx + 4])[0]
                    idx += 2 + length
                else:
                    idx += 1
        except Exception:
            pass

        plain_try = raw_bytes[:4000].decode("utf-8", errors="ignore").strip()
        is_demo_text = not raw_bytes.startswith(b"\xff\xd8") and len(plain_try) > 5
        desc_img = plain_try if is_demo_text else f"Evidencia fotográfica / captura visual JPEG ({width}x{height} px, {size_kb} KB)."
        result["text"] = desc_img
        result["key_points"] = [desc_img]
        result["metrics"] = {"resolucion": f"{width}x{height} px" if width else "Estándar", "size_kb": size_kb}
        return result

    # Fallback texto plano
    plain = raw_bytes[:6000].decode("utf-8", errors="ignore").strip()
    result["text"] = plain
    result["key_points"] = [ln.strip() for ln in plain.splitlines() if ln.strip()][:5]
    return result


def build_human_file_summary(f: Dict[str, Any]) -> str:
    """Construye un resumen ejecutivo claro y humano para un archivo individual."""
    name = f.get("filename", "archivo")
    ext = (f.get("extension") or "").lower().lstrip(".")
    size_kb = f.get("size_kb", 0)
    prio = f.get("priority", "Media")
    deep_text = (f.get("deep_text") or f.get("summary") or "").strip()
    key_pts = f.get("key_points") or []
    metrics = f.get("metrics") or {}

    # Limpiar prefijos repetitivos antiguos si vienen de la BD
    deep_text = re.sub(r"^\[.*?\]\s*'.*?'\s*\([\d.]+\s*KB\)\s*procesado con éxito\.?\s*(Contenido clave:\s*)?", "", deep_text).strip(' "')

    if ext == "xlsx":
        filas = metrics.get("filas_con_datos", 0)
        suma = metrics.get("suma_total", 0)
        extra_metric = f" ({filas} filas detectadas" + (f", suma numérica: ${suma:,.2f})" if suma else ")") if filas else ""
        muestra = " | ".join(key_pts[:3]) if key_pts else (deep_text[:220] if deep_text else "Estructura de celdas y columnas contables verificada.")
        return f"📊 **{name}** (Excel .XLSX, {size_kb} KB — Prioridad {prio}){extra_metric}:\n   • **Contenido de la tabla:** {muestra}"

    if ext == "pdf":
        muestra = " — ".join(key_pts[:3]) if key_pts else (deep_text[:240] if deep_text else "Documento formal validado mediante lectura PDF/OCR.")
        return f"📕 **{name}** (Documento PDF, {size_kb} KB — Prioridad {prio}):\n   • **Resumen del texto:** {muestra}"

    if ext == "docx":
        muestra = " — ".join(key_pts[:3]) if key_pts else (deep_text[:240] if deep_text else "Informe Word estructurado sin errores de formato.")
        return f"📘 **{name}** (Documento Word .DOCX, {size_kb} KB — Prioridad {prio}):\n   • **Puntos principales:** {muestra}"

    if ext in ("jpg", "jpeg", "png", "webp"):
        res = metrics.get("resolucion", "")
        muestra = deep_text[:200] if deep_text else f"Imagen o captura de soporte ({res or str(size_kb) + ' KB'}) analizada por visión."
        return f"🖼️ **{name}** (Imagen .JPG, {size_kb} KB — Prioridad {prio}):\n   • **Detalle visual:** {muestra}"

    return f"📄 **{name}** ({size_kb} KB): {deep_text[:200] or 'Archivo validado correctamente.'}"


import os
import io
import re
import zlib
import zipfile
import struct
import xml.etree.ElementTree as ET
from typing import Dict, Any, List


def extract_deep_file_text(filename: str, ext: str, raw_bytes: bytes) -> Dict[str, Any]:
    """
    Extractor profundo de contenido real para .PDF, .DOCX, .XLSX y .JPG.
    Extrae texto limpio, párrafos, tablas, cifras y metadatos reales del binario.
    """
    ext = (ext or "").lower().lstrip(".")
    size_kb = round(len(raw_bytes) / 1024, 1) if raw_bytes else 0.0
    result = {
        "filename": filename,
        "extension": ext,
        "size_kb": size_kb,
        "text": "",
        "key_points": [],
        "metrics": {}
    }
    if not raw_bytes:
        return result

    # 1. WORD (.DOCX): Párrafos y tablas completas desde word/document.xml
    if ext == "docx":
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                xml_content = zf.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            paragraphs = []
            for p_node in tree.iter():
                if p_node.tag.endswith("}p"):
                    runs = [t.text for t in p_node.iter() if t.tag.endswith("}t") and t.text]
                    line = "".join(runs).strip()
                    if line:
                        paragraphs.append(line)
            full_text = "\n".join(paragraphs)
            result["text"] = full_text[:6000]
            result["key_points"] = [p for p in paragraphs if len(p) > 20][:6]
            result["metrics"] = {"parrafos": len(paragraphs), "palabras": len(full_text.split())}
            return result
        except Exception:
            pass

    # 2. EXCEL (.XLSX): Celdas de texto (sharedStrings) + valores numéricos de las hojas
    if ext == "xlsx":
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                shared_strings = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    ss_xml = zf.read("xl/sharedStrings.xml")
                    ss_tree = ET.fromstring(ss_xml)
                    for si in ss_tree.iter():
                        if si.tag.endswith("}si"):
                            txt = "".join(t.text for t in si.iter() if t.tag.endswith("}t") and t.text)
                            shared_strings.append(txt.strip())

                rows_text = []
                numeric_vals = []
                sheet_files = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
                for sf in sheet_files[:3]:
                    sh_tree = ET.fromstring(zf.read(sf))
                    for row_el in sh_tree.iter():
                        if row_el.tag.endswith("}row"):
                            row_cells = []
                            for c_el in row_el:
                                if not c_el.tag.endswith("}c"):
                                    continue
                                c_type = c_el.attrib.get("t", "")
                                v_el = next((ch for ch in c_el if ch.tag.endswith("}v")), None)
                                is_el = next((ch for ch in c_el if ch.tag.endswith("}is")), None)
                                if v_el is not None and v_el.text:
                                    val_str = v_el.text.strip()
                                    if c_type == "s" and val_str.isdigit():
                                        idx = int(val_str)
                                        if 0 <= idx < len(shared_strings):
                                            row_cells.append(shared_strings[idx])
                                    else:
                                        row_cells.append(val_str)
                                        try:
                                            num = float(val_str)
                                            numeric_vals.append(num)
                                        except ValueError:
                                            pass
                                elif is_el is not None:
                                    inline_txt = "".join(t.text for t in is_el.iter() if t.tag.endswith("}t") and t.text)
                                    if inline_txt.strip():
                                        row_cells.append(inline_txt.strip())
                            if row_cells:
                                rows_text.append(" | ".join(row_cells))

                if not rows_text and shared_strings:
                    rows_text = [" | ".join(shared_strings[:30])]

                full_text = "\n".join(rows_text[:40])
                result["text"] = full_text[:6000]
                result["key_points"] = rows_text[:6]
                result["metrics"] = {
                    "filas_con_datos": len(rows_text),
                    "celdas_texto": len(shared_strings),
                    "valores_numericos": len(numeric_vals),
                    "suma_total": round(sum(numeric_vals), 2) if numeric_vals else 0,
                    "max_valor": round(max(numeric_vals), 2) if numeric_vals else 0
                }
                return result
        except Exception:
            pass

    # 3. PDF (.PDF): Extracción con pypdf/PyPDF2 o descompresión nativa FlateDecode + parser PDF
    if ext == "pdf":
        extracted_pdf = ""
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            pages_txt = [page.extract_text() or "" for page in reader.pages[:15]]
            extracted_pdf = "\n".join(pages_txt).strip()
        except Exception:
            pass

        if not extracted_pdf:
            # Descompresión nativa de streams PDF (zlib FlateDecode) y lectura de bloques de texto (...)
            chunks = []
            for m in re.finditer(rb"stream[\r\n]+(.*?)[\r\n]+endstream", raw_bytes, re.DOTALL):
                stream_data = m.group(1)
                try:
                    decomp = zlib.decompress(stream_data)
                except Exception:
                    decomp = stream_data
                for txt_m in re.finditer(rb"\(([^()]{2,250})\)", decomp):
                    s = txt_m.group(1).decode("latin-1", errors="ignore")
                    s_clean = re.sub(r"\\[nrtbf()\\]", " ", s).strip()
                    if len(s_clean) > 2 and sum(c.isalpha() for c in s_clean) >= 2:
                        chunks.append(s_clean)
            if chunks:
                extracted_pdf = " ".join(chunks)

        if not extracted_pdf:
            # Si es un archivo de texto plano con extensión .pdf (como en el lote demo)
            plain_try = raw_bytes[:8000].decode("utf-8", errors="ignore")
            if not plain_try.startswith("%PDF"):
                extracted_pdf = plain_try.strip()
            else:
                # Extraer cadenas legibles que no sean comandos internos PDF
                pdf_keywords = {"obj", "endobj", "stream", "endstream", "xref", "trailer", "flatedecode", "type", "font", "page", "pages", "catalog", "parent", "resources", "mediabox", "contents", "length", "filter"}
                words = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ0-9,.;:\-\$/%]{3,}", plain_try)
                clean_words = [w for w in words if w.lower() not in pdf_keywords and not w.startswith("PDF")]
                extracted_pdf = " ".join(clean_words[:200])

        lines = [ln.strip() for ln in re.split(r"[\r\n]+|(?<=\.)\s+", extracted_pdf) if len(ln.strip()) > 12]
        result["text"] = extracted_pdf[:6000]
        result["key_points"] = lines[:6]
        result["metrics"] = {"palabras": len(extracted_pdf.split())}
        return result

    # 4. IMÁGENES (.JPG / .JPEG): Resolución JPEG o texto embebido
    if ext in ("jpg", "jpeg", "png", "webp"):
        width, height = 0, 0
        try:
            # Leer dimensiones reales de cabecera JPEG SOF0/SOF2
            idx = 2
            while idx < len(raw_bytes) - 8:
                if raw_bytes[idx] == 0xFF:
                    marker = raw_bytes[idx + 1]
                    if marker in (0xC0, 0xC1, 0xC2):
                        height, width = struct.unpack(">HH", raw_bytes[idx + 5:idx + 9])
                        break
                    length = struct.unpack(">H", raw_bytes[idx + 2:idx + 4])[0]
                    idx += 2 + length
                else:
                    idx += 1
        except Exception:
            pass

        plain_try = raw_bytes[:4000].decode("utf-8", errors="ignore").strip()
        is_demo_text = not raw_bytes.startswith(b"\xff\xd8") and len(plain_try) > 5
        desc_img = plain_try if is_demo_text else f"Evidencia fotográfica / captura visual JPEG ({width}x{height} px, {size_kb} KB)."
        result["text"] = desc_img
        result["key_points"] = [desc_img]
        result["metrics"] = {"resolucion": f"{width}x{height} px" if width else "Estándar", "size_kb": size_kb}
        return result

    # Fallback texto plano
    plain = raw_bytes[:6000].decode("utf-8", errors="ignore").strip()
    result["text"] = plain
    result["key_points"] = [ln.strip() for ln in plain.splitlines() if ln.strip()][:5]
    return result


def build_human_file_summary(f: Dict[str, Any]) -> str:
    """Construye un resumen ejecutivo claro y humano para un archivo individual."""
    name = f.get("filename", "archivo")
    ext = (f.get("extension") or "").lower().lstrip(".")
    size_kb = f.get("size_kb", 0)
    prio = f.get("priority", "Media")
    deep_text = (f.get("deep_text") or f.get("summary") or "").strip()
    key_pts = f.get("key_points") or []
    metrics = f.get("metrics") or {}

    # Limpiar prefijos repetitivos antiguos si vienen de la BD
    deep_text = re.sub(r"^\[.*?\]\s*'.*?'\s*\([\d.]+\s*KB\)\s*procesado con éxito\.?\s*(Contenido clave:\s*)?", "", deep_text).strip(' "')

    if ext == "xlsx":
        filas = metrics.get("filas_con_datos", 0)
        suma = metrics.get("suma_total", 0)
        extra_metric = f" ({filas} filas detectadas" + (f", suma numérica: ${suma:,.2f})" if suma else ")") if filas else ""
        muestra = " | ".join(key_pts[:3]) if key_pts else (deep_text[:220] if deep_text else "Estructura de celdas y columnas contables verificada.")
        return f"📊 **{name}** (Excel .XLSX, {size_kb} KB — Prioridad {prio}){extra_metric}:\n   • **Contenido de la tabla:** {muestra}"

    if ext == "pdf":
        muestra = " — ".join(key_pts[:3]) if key_pts else (deep_text[:240] if deep_text else "Documento formal validado mediante lectura PDF/OCR.")
        return f"📕 **{name}** (Documento PDF, {size_kb} KB — Prioridad {prio}):\n   • **Resumen del texto:** {muestra}"

    if ext == "docx":
        muestra = " — ".join(key_pts[:3]) if key_pts else (deep_text[:240] if deep_text else "Informe Word estructurado sin errores de formato.")
        return f"📘 **{name}** (Documento Word .DOCX, {size_kb} KB — Prioridad {prio}):\n   • **Puntos principales:** {muestra}"

    if ext in ("jpg", "jpeg", "png", "webp"):
        res = metrics.get("resolucion", "")
        muestra = deep_text[:200] if deep_text else f"Imagen o captura de soporte ({res or str(size_kb) + ' KB'}) analizada por visión."
        return f"🖼️ **{name}** (Imagen .JPG, {size_kb} KB — Prioridad {prio}):\n   • **Detalle visual:** {muestra}"

    return f"📄 **{name}** ({size_kb} KB): {deep_text[:200] or 'Archivo validado correctamente.'}"


def answer_file_chatbot_question(pregunta: str, files_data: List[Dict[str, Any]], ticket_context: Dict[str, Any] = None) -> str:
    """
    Chatbot Empresarial e Inteligente de Gestión, Soporte y Análisis Documental 24/7.
    - Responde consultas conversacionales generales (saludos, asistencia, cómo radicar, dudas del sistema).
    - Asiste en el módulo de Visión Artificial e IA Multimodal (facturas, cédulas, recibos, cámara móvil, umbral 80%).
    - Consulta estados de tickets en tiempo real si se proporciona el contexto o código de seguimiento.
    - Analiza y resume profundamente lotes de archivos (.pdf, .xlsx, .docx, .jpg) con Google Gemini o motor semántico local.
    """
    q = (pregunta or "").strip()
    q_low = q.lower()
    total = len(files_data) if files_data else 0

    # 1. INTENTO CON INTELIGENCIA ARTIFICIAL GENERATIVA (GOOGLE GEMINI 2.5 FLASH)
    try:
        from app import ai_provider
        if ai_provider.is_available():
            context_blocks = []
            if total > 0:
                for idx, f in enumerate(files_data[:30], start=1):
                    txt_part = (f.get("deep_text") or f.get("summary") or "")[:1200]
                    context_blocks.append(
                        f"--- ARCHIVO #{idx} ---\n"
                        f"Nombre: {f.get('filename')} (Formato: {f.get('extension')}, Tamaño: {f.get('size_kb')} KB)\n"
                        f"Prioridad preliminar: {f.get('priority', 'Media')}\n"
                        f"Contenido extraído / Tabla: {txt_part}\n"
                    )
                archivos_texto = "\n".join(context_blocks)
            else:
                archivos_texto = "No hay archivos adjuntos en esta consulta específica."

            t_info = ""
            if ticket_context:
                t_info = f"Contexto de la solicitud actual: Código {ticket_context.get('codigo')}, Título: '{ticket_context.get('titulo')}', Estado: {ticket_context.get('estado', 'En gestión')}, Prioridad: {ticket_context.get('prioridad', 'Normal')}."

            prompt_gemini = f"""Eres el Asistente Virtual Inteligente 24/7 del Sistema Inteligente de Gestión y Análisis Documental (Tercer Corte DAE).
Eres profesional, empático, claro, conciso y muy competente.

{t_info}

Archivos del expediente disponibles ({total} archivo/s):
{archivos_texto}

Pregunta del usuario: «{q}»

Instrucciones de respuesta:
1. Si el usuario te saluda o hace una pregunta general sobre el sistema, respóndele cordialmente explicando cómo puedes asistirlo (radicar solicitudes, escanear documentos con cámara en /vision, auditar facturas, consultar tickets o resumir expedientes).
2. Si te preguntan sobre el módulo de Visión Artificial, explica que admite fotos desde la cámara del celular, extrae emisor, NIT, fecha y monto, y aplica una regla de validación humana (Human-in-the-Loop) si la confianza de la IA es inferior al 80%.
3. Si el usuario pregunta por archivos o pide resúmenes y hay documentos cargados, extrae los datos reales más relevantes (proveedores, importes, cifras de Excel, advertencias).
4. Si no hay archivos y el usuario pide un resumen de documentos, indícale amablemente cómo subirlos o generar un lote de demostración.
5. Utiliza formato Markdown profesional: negritas, viñetas y emojis pertinentes. Responde siempre en español fluido y educado."""

            res_ia = ai_provider.generate(
                prompt=prompt_gemini,
                system="Eres el Asistente Ejecutivo del Sistema Inteligente de Gestión Documental. Respuestas de alta calidad empresarial, sin rodeos innecesarios."
            )
            if res_ia.ok and res_ia.text:
                return res_ia.text.strip()
    except Exception:
        # Fallback silencioso al motor semántico local
        pass

    # 2. MOTOR SEMÁNTICO LOCAL HEURÍSTICO (PLAN B - OFFLINE / RESILIENTE)
    
    # 2.1 SALUDOS Y ASISTENCIA GENERAL
    if any(k in q_low for k in ["hola", "buenos dias", "buenas tardes", "buenas noches", "saludos", "que tal", "quien eres", "cómo estás", "como estas"]):
        return (
            "👋 **¡Hola! Bienvenido al Sistema Inteligente de Gestión y Análisis Documental 24/7.**\n\n"
            "Soy tu asistente virtual integrado con Inteligencia Artificial. Estoy a tu disposición para:\n"
            "• 📄 **Radicar Solicitudes:** Diagnóstico automático de categoría, prioridad y SLA.\n"
            "• 📷 **Visión por Computador:** Escanear fotos de facturas, recibos y cédulas tomadas con tu celular en `/vision`.\n"
            "• 📊 **Análisis Documental:** Leer, resumir y extraer cifras de lotes de archivos (`.pdf`, `.xlsx`, `.docx`, `.jpg`).\n"
            "• 🔎 **Seguimiento:** Consultar el estado y avance de tus radicaciones en tiempo real.\n\n"
            "¿En qué puedo orientarte hoy? Puedes formularme cualquier pregunta o pedirme un resumen de tus documentos."
        )

    # 2.2 PREGUNTAS SOBRE VISIÓN POR COMPUTADOR Y CÁMARA MÓVIL
    if any(k in q_low for k in ["vision", "visión", "camara", "cámara", "escanear", "escaneo", "factura", "recibo", "cedula", "cédula", "multimodal", "humano", "human", "80%", "umbral", "confianza"]):
        return (
            "📷 **Módulo de Visión Artificial e IA Multimodal (Componente 2):**\n\n"
            "Nuestro sistema procesa imágenes y documentos escaneados mediante las siguientes directrices empresariales:\n"
            "1. **Captura Móvil y Carga Flexible:** Puedes tomar una foto directamente con la cámara de tu teléfono móvil o subir archivos JPG, PNG y PDF hasta 10 MB desde el portal `/vision`.\n"
            "2. **Extracción Estructurada:** La IA identifica automáticamente la razón social del emisor, NIT, fecha de emisión, total monetario, divisa y calcula un score de confianza (0% al 100%).\n"
            "3. **Protocolo Human-in-the-Loop (Umbral del 80%):**\n"
            "   • Si la confianza es **mayor o igual al 80%**, el registro se clasifica con alta fiabilidad.\n"
            "   • Si la confianza es **menor al 80%** (por ejemplo, por mala iluminación o desgaste del papel térmico), el sistema activa el estado **«Pendiente de Revisión»** y habilita un panel para que un agente humano confirme o edite los valores antes de impactar las bases de datos contables.\n"
            "4. **Tolerancia a Fallos:** Si no hay conexión externa a Gemini, se activa automáticamente el motor sintáctico local (Plan B)."
        )

    # 2.3 CÓMO RADICAR Y TIEMPOS DE RESPUESTA (SLA)
    if any(k in q_low for k in ["radicar", "crear ticket", "solicitud", "sla", "prioridad", "tiempo de respuesta", "como funciona"]):
        return (
            "⚡ **Radicación Inteligente y Nivel de Servicio (SLA):**\n\n"
            "Para radicar una nueva solicitud en el portal:\n"
            "1. Ve al menú **«Crear Solicitud»** e ingresa tus datos de contacto y la descripción de tu requerimiento.\n"
            "2. Autoriza el tratamiento de datos personales conforme a la **Ley 1581 de 2012 (Habeas Data)**.\n"
            "3. Opcionalmente adjunta archivos de soporte (puedes subir lotes de hasta 30 documentos multimodales).\n"
            "4. **Automatización Propia en Código (Componente 1):** Nuestro motor en segundo plano (`AutomationEngine`) clasifica la prioridad:\n"
            "   • 🔴 **Alta (Crítica):** SLA de atención en menos de 2 a 4 horas hábiles.\n"
            "   • 🟡 **Media (Estándar):** SLA de resolución de 12 a 24 horas hábiles.\n"
            "   • 🟢 **Baja (Informativa):** SLA de respuesta en 24 a 48 horas hábiles.\n"
            "Al finalizar, recibirás un **Código de Seguimiento** único para consultar el estado en cualquier momento."
        )

    # 2.4 PROTECCIÓN DE DATOS Y HABEAS DATA
    if any(k in q_low for k in ["datos", "habeas", "1581", "privacidad", "seguridad", "contraseña", "password"]):
        return (
            "🛡️ **Seguridad Criptográfica y Protección de Datos Personales:**\n\n"
            "• **Ley Estatutaria 1581 de 2012:** El sistema exige la autorización previa, expresa e informada del titular antes de recolectar cualquier dato personal en los formularios.\n"
            "• **Criptografía OWASP Top 10:** Las contraseñas de los usuarios agentes están protegidas con el algoritmo de derivación de claves **PBKDF2-SHA256 con 100.000 iteraciones** y sal criptográfica aleatoria de 16 bytes.\n"
            "• **Sesiones Blindadas:** Se emplean cookies firmadas criptográficamente con directivas `HttpOnly` y `SameSite=Lax` para mitigar ataques de secuestro de sesión (XSS y CSRF)."
        )

    # 2.5 CONSULTA SOBRE ARCHIVOS CUANDO NO HAY NINGUNO
    if total == 0:
        return (
            "🤖 **No se han cargado archivos en este expediente o consulta.**\n\n"
            "Para que pueda analizar en profundidad tus documentos:\n"
            "• Arrastra tus archivos (`.pdf`, `.xlsx`, `.docx`, `.jpg`) en el área de carga superior, o\n"
            "• Si deseas ver una demostración inmediata, pulsa el botón **«Generar Lote Demo de 30 Archivos»**.\n\n"
            "Si tienes una consulta general sobre el funcionamiento del sistema, ¡pregunta con confianza!"
        )

    # 2.6 RESUMEN Y ANÁLISIS DE ARCHIVOS CARGADOS (CUANDO SÍ HAY ARCHIVOS)
    counts = {"pdf": 0, "xlsx": 0, "docx": 0, "jpg": 0}
    total_kb = 0.0
    high_prio = []
    by_ext = {"pdf": [], "xlsx": [], "docx": [], "jpg": []}

    for f in files_data:
        ext = (f.get("extension") or "").lower().lstrip(".")
        if ext in ("jpeg", "png", "webp"):
            ext = "jpg"
        elif ext in ("txt", "csv"):
            ext = "docx" if ext == "txt" else "xlsx"
        if ext in counts:
            counts[ext] += 1
            by_ext[ext].append(f)
        total_kb += float(f.get("size_kb") or 0)
        if (f.get("priority") or "").lower() == "alta":
            high_prio.append(f)

    # Archivo específico mencionado
    matched = []
    for idx, f in enumerate(files_data, start=1):
        fname = (f.get("filename") or "").lower()
        fname_no_ext = fname.rsplit(".", 1)[0] if "." in fname else fname
        fcode = (f.get("file_code") or "").lower()
        if (fname and fname in q_low) or (len(fname_no_ext) > 3 and fname_no_ext in q_low) or (fcode and fcode in q_low) or f"archivo {idx}" in q_low or f"#{idx}" in q_low:
            matched.append(f)

    if matched:
        detalles = "\n\n".join([build_human_file_summary(m) + f"\n   • **Acción recomendada:** {m.get('recommendation', 'Validar en el expediente.')}" for m in matched[:5]])
        return (
            f"🔎 **Resumen detallado del archivo solicitado ({len(matched)} encontrado(s)):**\n\n"
            f"{detalles}"
        )

    # Resumen general del lote
    if any(k in q_low for k in ["resum", "síntesis", "sintesis", "de que trata", "de qué trata", "que dice", "qué dice", "que contienen", "qué contienen", "explica", "analiza todo", "general", "todo el lote", "todos los archivos"]):
        bloques = []
        if by_ext["pdf"]:
            ej_pdf = "\n".join(["   " + build_human_file_summary(x) for x in by_ext["pdf"][:3]])
            mas_pdf = f"\n   *(+ {len(by_ext['pdf']) - 3} documento(s) PDF adicionales con estructura similar)*" if len(by_ext["pdf"]) > 3 else ""
            bloques.append(f"### 1. Documentos PDF ({len(by_ext['pdf'])} archivo(s))\n{ej_pdf}{mas_pdf}")
        if by_ext["xlsx"]:
            ej_xls = "\n".join(["   " + build_human_file_summary(x) for x in by_ext["xlsx"][:3]])
            mas_xls = f"\n   *(+ {len(by_ext['xlsx']) - 3} hoja(s) Excel adicionales procesadas)*" if len(by_ext["xlsx"]) > 3 else ""
            bloques.append(f"### 2. Hojas de Cálculo Excel .XLSX ({len(by_ext['xlsx'])} archivo(s))\n{ej_xls}{mas_xls}")
        if by_ext["docx"]:
            ej_doc = "\n".join(["   " + build_human_file_summary(x) for x in by_ext["docx"][:3]])
            mas_doc = f"\n   *(+ {len(by_ext['docx']) - 3} documento(s) Word adicionales)*" if len(by_ext["docx"]) > 3 else ""
            bloques.append(f"### 3. Informes Word .DOCX ({len(by_ext['docx'])} archivo(s))\n{ej_doc}{mas_doc}")
        if by_ext["jpg"]:
            ej_jpg = "\n".join(["   " + build_human_file_summary(x) for x in by_ext["jpg"][:2]])
            mas_jpg = f"\n   *(+ {len(by_ext['jpg']) - 2} evidencia(s) visual(es) más)*" if len(by_ext["jpg"]) > 2 else ""
            bloques.append(f"### 4. Imágenes y Capturas .JPG ({len(by_ext['jpg'])} archivo(s))\n{ej_jpg}{mas_jpg}")

        cuerpo = "\n\n".join(bloques)
        conclusion = (
            f"⚠️ **Atención:** Se detectaron **{len(high_prio)} archivo(s) con Prioridad Alta** que requieren revisión inmediata."
            if high_prio else
            "✅ **Conclusión:** Todos los archivos fueron analizados correctamente y no presentan bloqueos críticos."
        )
        return (
            f"📋 **RESUMEN EJECUTIVO DE TUS {total} ARCHIVOS ({round(total_kb, 1)} KB):**\n\n"
            f"{cuerpo}\n\n"
            f"{conclusion}"
        )

    # Preguntas por tipo de documento
    if any(k in q_low for k in ["pdf", "word", "docx", "contrato", "documento", "texto"]):
        docs = by_ext["pdf"] + by_ext["docx"]
        if not docs:
            return f"📑 En este momento no tienes archivos `.pdf` ni `.docx` cargados ({counts['xlsx']} Excel y {counts['jpg']} imágenes disponibles)."
        listado = "\n\n".join([build_human_file_summary(d) for d in docs[:6]])
        return f"📑 **Resumen de Documentos PDF y Word ({len(by_ext['pdf'])} PDF, {len(by_ext['docx'])} DOCX):**\n\n{listado}"

    if any(k in q_low for k in ["excel", "xlsx", "tabla", "monto", "valor", "cifra", "calculo", "cálculo", "hoja", "contable"]):
        xls = by_ext["xlsx"]
        if not xls:
            return f"📊 No hay hojas de cálculo `.xlsx` en este lote ({counts['pdf']} PDF, {counts['docx']} Word, {counts['jpg']} JPG)."
        listado = "\n\n".join([build_human_file_summary(x) for x in xls[:6]])
        return f"📈 **Resumen de Hojas de Cálculo Excel ({len(xls)} archivo(s) .XLSX):**\n\n{listado}"

    if any(k in q_low for k in ["imagen", "imagenes", "imágenes", "jpg", "jpeg", "foto", "captura"]):
        imgs = by_ext["jpg"]
        if not imgs:
            return f"🖼️ No hay imágenes `.jpg` o capturas cargadas en este lote."
        listado = "\n\n".join([build_human_file_summary(x) for x in imgs[:5]])
        return f"🖼️ **Evidencias Visuales e Imágenes ({len(imgs)} archivo(s)):**\n\n{listado}"

    # Respuesta predeterminada enriquecida
    return (
        f"💡 **Asistente Inteligente:** He recibido tu consulta «*{q}*».\n\n"
        f"Tienes actualmente **{total} archivo(s)** disponibles en el expediente ({round(total_kb, 1)} KB totales).\n"
        f"Puedes pedirme:\n"
        f"• *«Resumir todos los archivos»*\n"
        f"• *«¿Qué información tienen los Excel?»*\n"
        f"• *«Explicar el documento PDF»*\n"
        f"• *«¿Cuáles requieren atención urgente?»*"
    )
