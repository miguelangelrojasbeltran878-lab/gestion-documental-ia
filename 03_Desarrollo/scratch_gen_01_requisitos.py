import os
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_bg(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)

def add_table(doc, headers, rows, header_bg="1E1B4B"):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = ""
        p = hdr_cells[i].paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)
        set_cell_bg(hdr_cells[i], header_bg)
    for row_idx, r_data in enumerate(rows):
        row_cells = table.add_row().cells
        bg = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for i, val in enumerate(r_data):
            row_cells[i].text = ""
            p = row_cells[i].paragraphs[0]
            run = p.add_run(str(val))
            run.font.size = Pt(8.5)
            run.font.color.rgb = RGBColor(30, 41, 59)
            set_cell_bg(row_cells[i], bg)
    doc.add_paragraph()
    return table

def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        if level == 1:
            run.font.color.rgb = RGBColor(30, 27, 75)
            run.font.size = Pt(14)
        elif level == 2:
            run.font.color.rgb = RGBColor(109, 40, 217)
            run.font.size = Pt(12)
        else:
            run.font.color.rgb = RGBColor(15, 118, 110)
            run.font.size = Pt(10.5)
    return h

def generate_01_requisitos():
    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(0.85); s.bottom_margin = Inches(0.85)
        s.left_margin = Inches(0.85); s.right_margin = Inches(0.85)

    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = title_p.add_run("DESARROLLO DE APLICACIONES EMPRESARIALES — TERCER CORTE\n")
    r_sub.bold = True; r_sub.font.size = Pt(10); r_sub.font.color.rgb = RGBColor(109, 40, 217)
    r_main = title_p.add_run("01_ANALISIS — ESPECIFICACIÓN DE REQUISITOS DEL SISTEMA\n")
    r_main.bold = True; r_main.font.size = Pt(16); r_main.font.color.rgb = RGBColor(30, 27, 75)
    r_doc = title_p.add_run("Sistema Inteligente de Gestión y Análisis Documental con IA Multimodal\n")
    r_doc.bold = True; r_doc.font.size = Pt(12); r_doc.font.color.rgb = RGBColor(15, 118, 110)
    
    meta_p = doc.add_paragraph()
    meta_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_meta = meta_p.add_run(
        f"Versión: 3.0 (Evolución Oficial Tercer Corte) | Fecha: {datetime.now().strftime('%Y-%m-%d')}\n"
        "Autores: Miguel Angel Rojas Beltran & Nicolle Steffany Garcia Grimaldos"
    )
    r_meta.font.size = Pt(9); r_meta.font.color.rgb = RGBColor(71, 85, 105)
    doc.add_paragraph("─" * 80)

    add_heading(doc, "1. Introducción y Alcance Evolutivo (Tercer Corte)", level=1)
    doc.add_paragraph(
        "El presente documento especifica los requisitos de software del 'Sistema Inteligente de Gestión y Análisis Documental', "
        "evolución del aplicativo empresarial para el Tercer Corte. Cumpliendo la directriz de la guía oficial, el sistema deja de "
        "depender de plataformas externas de pago (n8n Cloud) e implementa la RUTA A: motor de automatización propio en código, "
        "incorporando además un módulo de visión por computador e IA multimodal real, seguridad robusta y un chatbot documental inteligente."
    )

    add_heading(doc, "2. Matriz de Requisitos Funcionales del Sistema (RF)", level=1)
    rf_data = [
        ["RF-001", "Carga y Validación Masiva", "Permitir la carga de hasta 35 archivos simultáneos (.pdf, .xlsx, .docx, .jpg) con validación estricta de tamaño (máx 15MB) e integridad MIME."],
        ["RF-002", "Motor de Automatización en Código (Ruta A)", "Ejecutar internamente los flujos documentales (recepción, desglose, análisis, priorización y notificación) sin plataformas externas."],
        ["RF-003", "Auditoría de Automatización", "Registrar en 'tbl_ejecucion_automatizacion' cada proceso (EXE-...), duración en milisegundos, reintentos automáticos y estado."],
        ["RF-004", "IA Multimodal y Visión por Computador", "Procesar imágenes de celulares o escaneos (.jpg, .png, .pdf), extraer texto y generar un JSON estructurado de entidades."],
        ["RF-005", "Cálculo de Nivel de Confianza", "Estimar la precisión de la extracción visual (0.0 a 1.0). Si confianza < 0.75, asignar automáticamente estado PENDIENTE_REVISION."],
        ["RF-006", "Validación Humana Obligatoria", "Proveer interfaz para confirmar, corregir o rechazar los campos extraídos por visión antes de impactar el proceso de negocio."],
        ["RF-007", "Plan B ante Fallos de IA", "Conmutar automáticamente a reglas heurísticas locales y OCR de contingencia si Gemini agota cuota o pierde conexión."],
        ["RF-008", "Chatbot Documental Contextual", "Permitir al usuario formular preguntas libres sobre el contenido de los archivos y recibir respuestas analíticas inmediatas."],
        ["RF-009", "Autenticación PBKDF2 y Roles", "Controlar acceso de agentes y administradores con contraseñas seguras (100.000 iteraciones) y sesiones firmadas con cookies seguras."],
        ["RF-010", "Protección de Datos (Ley 1581)", "Exigir consentimiento explícito previo y anonimizar datos personales en bitácoras de auditoría y trazas de IA."],
        ["RF-011", "Dashboard con Métricas 100% Reales", "Calcular satisfacción CSAT (estrellas) y tiempos promedio desde la base de datos SQLite sin valores fijos."],
        ["RF-012", "Hilo de Conversación y Feedback", "Mantener chat bidireccional entre cliente, agente y respuestas automáticas del sistema."]
    ]
    add_table(doc, ["Código", "Requisito Funcional", "Descripción y Criterio de Aceptación"], rf_data)

    add_heading(doc, "3. Requisitos No Funcionales (RNF)", level=1)
    rnf_data = [
        ["RNF-001", "Rendimiento y Latencia", "El backend debe procesar lotes y responder peticiones locales en menos de 500 ms bajo concurrencia moderada."],
        ["RNF-002", "Cero Costo Operativo", "Uso exclusivo de herramientas gratuitas, open-source o niveles gratuitos suficientes (Python, SQLite, Gemini gratuito)."],
        ["RNF-003", "Seguridad Criptográfica", "Hashing PBKDF2-SHA256 para credenciales y tokens firmados con clave simétrica para descarga temporal."],
        ["RNF-004", "Resiliencia y Disponibilidad", "Tolerancia a fallos de proveedores externos mediante el Plan B sin bloquear la navegación del usuario."],
        ["RNF-005", "Portabilidad", "Compatibilidad total para ejecución en entornos Windows, Linux y contenedores de despliegue en la nube (Render/Railway)."]
    ]
    add_table(doc, ["Código", "Requisito No Funcional", "Especificación Técnica"], rnf_data)

    os.makedirs(r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\01_ANALISIS", exist_ok=True)
    out_path = r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\01_ANALISIS\01_Requisitos.docx"
    doc.save(out_path)
    print("Saved:", out_path)

if __name__ == "__main__":
    generate_01_requisitos()
