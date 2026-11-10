import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color):
    shading_xml = f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>'
    cell._tc.get_or_add_tcPr().append(parse_xml(shading_xml))

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="{top}" w:type="dxa"/><w:bottom w:w="{bottom}" w:type="dxa"/><w:left w:w="{left}" w:type="dxa"/><w:right w:w="{right}" w:type="dxa"/></w:tcMar>')
    tcPr.append(tcMar)

def create_styled_table(doc, headers, data, col_widths=None):
    table = doc.add_table(rows=len(data) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Header Row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "1F497D")
        set_cell_margins(hdr_cells[i], top=120, bottom=120, left=140, right=140)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in p.runs:
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.font.size = Pt(9.5)
            run.font.name = "Arial"

    # Data Rows
    for r_idx, row in enumerate(data):
        row_cells = table.rows[r_idx + 1].cells
        bg_color = "F2F5F9" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, val in enumerate(row):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_color)
            set_cell_margins(row_cells[c_idx], top=80, bottom=80, left=120, right=120)
            p = row_cells[c_idx].paragraphs[0]
            if c_idx == 0 or len(str(val)) < 15:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.size = Pt(8.5)
                run.font.name = "Arial"

    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = width

    doc.add_paragraph() # Spacing
    return table

def add_header_footer(doc, title_text):
    for s in doc.sections:
        s.top_margin = Inches(1)
        s.bottom_margin = Inches(1)
        s.left_margin = Inches(1)
        s.right_margin = Inches(1)
        
        # Header
        header = s.header
        hp = header.paragraphs[0]
        hp.text = f"SISTEMA INTELIGENTE DE GESTIÓN Y ANÁLISIS DOCUMENTAL — {title_text.upper()}"
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if hp.runs:
            hp.runs[0].font.size = Pt(8)
            hp.runs[0].font.color.rgb = RGBColor(120, 120, 120)
            hp.runs[0].font.name = "Arial"

        # Footer
        footer = s.footer
        fp = footer.paragraphs[0]
        fp.text = "Desarrollo de Aplicaciones Empresariales — Tercer Corte (2026)"
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if fp.runs:
            fp.runs[0].font.size = Pt(8)
            fp.runs[0].font.color.rgb = RGBColor(120, 120, 120)
            fp.runs[0].font.name = "Arial"

def build_hu_cu_doc():
    doc = Document()
    add_header_footer(doc, "Historias de Usuario y Casos de Uso")

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("HISTORIAS DE USUARIO Y CASOS DE USO\nTERCER CORTE: AUTOMATIZACIÓN E IA MULTIMODAL")
    r_title.font.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(31, 73, 125)
    r_title.font.name = "Arial"

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Evolución del Sistema Inteligente de Gestión y Análisis Documental\nIngeniería de Software / Desarrollo de Aplicaciones Empresariales")
    r_sub.font.italic = True
    r_sub.font.size = Pt(11)
    r_sub.font.name = "Arial"
    doc.add_paragraph()

    # Introduction
    h1 = doc.add_heading("1. INTRODUCCIÓN Y ENFOQUE ÁGIL", level=1)
    h1.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    
    p = doc.add_paragraph("El presente documento formaliza los artefactos ágiles y de análisis funcional correspondientes a la evolución del Sistema Inteligente de Gestión y Análisis Documental en el Tercer Corte. Se incorporan las Historias de Usuario (HU) y Casos de Uso (CU) orientados a los dos pilares obligatorios de la guía docente: (1) Automatización Autónoma en Código Python sin dependencia externa de n8n, y (2) Visión por Computador e IA Multimodal con Human-in-the-Loop.")

    # HU Table
    h2 = doc.add_heading("2. HISTORIAS DE USUARIO EVOLUCIONADAS (CORTE 3)", level=1)
    h2.runs[0].font.color.rgb = RGBColor(31, 73, 125)

    headers_hu = ["ID", "Rol / Actor", "Historia de Usuario (Quiero / Para)", "Criterios de Aceptación (DoD)", "Prioridad"]
    data_hu = [
        ["HU-C3-01", "Cliente / Usuario Final", "Subir fotografía de factura/documento tomada desde cámara móvil para auto-clasificar mi ticket sin escribir datos manuales.", "1. Admite JPG, PNG y PDF hasta 10MB.\n2. Inferencia multimodal con Gemini 2.5 Flash o Plan B.\n3. Extracción de emisor, NIT, fecha y monto.", "Alta (Core)"],
        ["HU-C3-02", "Agente de Servicio", "Validar y confirmar las entidades extraídas por visión artificial antes de que se impacte la base de datos.", "1. Interfaz muestra alerta si confianza < 80%.\n2. Campos editables antes de confirmar.\n3. Auditoría de confirmación humana registrada.", "Alta (Core)"],
        ["HU-C3-03", "Sistema / Motor Interno", "Ejecutar flujos en segundo plano con reintentos y trazabilidad en base de datos para no depender de n8n cloud.", "1. Registro en tbl_ejecucion_automatizacion.\n2. Medición de latencia en ms.\n3. Estados: EXITOSO, PLAN_B, FALLIDO.", "Alta (Core)"],
        ["HU-C3-04", "Cliente / Usuario Final", "Consultar y chatear con múltiples documentos adjuntos de forma contextual e interactiva.", "1. Chatbot analiza todos los archivos del ticket.\n2. Respuestas fundamentadas sin alucinaciones.\n3. Modo offline local heurístico si no hay API.", "Media-Alta"],
        ["HU-C3-05", "Oficial de Seguridad / DPO", "Contar con autorización expresa de datos personales (Habeas Data Ley 1581) y hashing de contraseñas.", "1. Checkbox obligatorio de tratamiento de datos.\n2. Passwords hasheadas con PBKDF2-SHA256 (100k it).\n3. Cookies de sesión httpOnly y firmadas.", "Alta (Normativa)"],
        ["HU-C3-06", "Gerente de Operaciones", "Visualizar métricas 100% reales en el Dashboard Bento sin datos simulados o quemados en código.", "1. Cálculo dinámico de CSAT en escala 1-5.\n2. Tasa real de éxito de automatizaciones.\n3. Tiempo medio de resolución calculado por SQL.", "Media"]
    ]
    create_styled_table(doc, headers_hu, data_hu, [Inches(0.9), Inches(1.1), Inches(2.3), Inches(1.8), Inches(0.8)])

    # CU Section
    h3 = doc.add_heading("3. ESPECIFICACIÓN DETALLADA DE CASOS DE USO", level=1)
    h3.runs[0].font.color.rgb = RGBColor(31, 73, 125)

    cu_details = [
        ("CU-C3-01: Procesamiento Multimodal de Documentos y Facturas con Visión Artificial", [
            ("Actores:", "Cliente, Sistema de Visión (Gemini / Plan B), Agente Revisor."),
            ("Precondiciones:", "El usuario accede al módulo /vision o adjunta archivo a un ticket."),
            ("Flujo Principal:", "1. El usuario captura foto con cámara o sube archivo JPG/PNG/PDF.\n2. El backend valida peso <= 10MB y tipo MIME.\n3. Se invoca VisionService.procesar_documento_vision().\n4. Se calculan entidades estructuradas (emisor, nit, total, moneda, fecha) y score de confianza (0.0 - 1.0).\n5. Se almacena en tbl_documento_vision con estado 'PENDIENTE_REVISION' si confianza < 0.80 o 'CONFIRMADO' si es superior y no requiere intervención."),
            ("Flujo Alterno (Plan B):", "Si la cuota de Gemini falla o no hay conexión externa, se activa el motor heurístico local Plan B mediante OCR sintáctico y expresiones regulares, marcando estado_ia = 'PLAN_B'."),
            ("Postcondiciones:", "Documento clasificado con entidades listas para integración en tickets.")
        ]),
        ("CU-C3-02: Ejecución de Automatización Autónoma en Código (Ruta A)", [
            ("Actores:", "Motor de Automatización (AutomationEngine), Base de Datos."),
            ("Precondiciones:", "Se crea o actualiza un ticket, o se procesa un lote documental."),
            ("Flujo Principal:", "1. Se dispara AutomationEngine.ejecutar_flujo_en_segundo_plano().\n2. Se calcula la inferencia de categorización y prioridad con IA.\n3. Se guarda log en tbl_ejecucion_automatizacion con timestamp, latencia_ms, entrada y salida JSON.\n4. Se actualiza el estado del ticket y notificaciones."),
            ("Postcondiciones:", "Ticket enriquecido con SLA, categoría y log de auditoría persistido.")
        ]),
        ("CU-C3-03: Chatbot Documental Contextual Multi-Archivo", [
            ("Actores:", "Cliente, Agente, Modelo de Lenguaje."),
            ("Precondiciones:", "El ticket contiene al menos un archivo subido o procesado."),
            ("Flujo Principal:", "1. El usuario escribe una pregunta sobre el expediente.\n2. El sistema extrae el texto de todos los archivos asociados al ticket.\n3. Se genera un prompt contextualizado inyectando el contenido documental.\n4. La IA responde con citas precisas del texto.\n5. Si no hay API externa, opera el motor de búsqueda léxica y resumen extractivo."),
            ("Postcondiciones:", "Respuesta clara y precisa entregada al usuario sin alucinación.")
        ])
    ]

    for title, steps in cu_details:
        h_cu = doc.add_heading(title, level=2)
        h_cu.runs[0].font.color.rgb = RGBColor(31, 73, 125)
        for label, text in steps:
            p_step = doc.add_paragraph()
            r_l = p_step.add_run(f"{label} ")
            r_l.bold = True
            r_l.font.color.rgb = RGBColor(50, 50, 50)
            p_step.add_run(text)

    # Conclusion
    h4 = doc.add_heading("4. CONCLUSIÓN DE ANÁLISIS", level=1)
    h4.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph("Las Historias de Usuario y Casos de Uso definidos cubren el 100% de los requerimientos funcionales del Tercer Corte, asegurando que las capacidades de automatización y visión artificial se integren de manera transparente y segura en la operación empresarial diaria.")

    out_path = r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\01_ANALISIS\02_Historias_de_Usuario_y_Casos_de_Uso.docx"
    doc.save(out_path)
    print(f"Saved: {out_path}")

def build_matriz_trazabilidad():
    doc = Document()
    add_header_footer(doc, "Matriz de Trazabilidad")

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("MATRIZ DE TRAZABILIDAD DE REQUISITOS\nTERCER CORTE: AUTOMATIZACIÓN, VISIÓN Y SEGURIDAD")
    r_title.font.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(31, 73, 125)
    r_title.font.name = "Arial"

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Alineación entre Requisitos Guía Docente, Código Fuente, Casos de Prueba y BD")
    r_sub.font.italic = True
    r_sub.font.size = Pt(11)
    r_sub.font.name = "Arial"
    doc.add_paragraph()

    h1 = doc.add_heading("1. ALCANCE Y METODOLOGÍA", level=1)
    h1.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph("La matriz de trazabilidad garantiza que cada uno de los lineamientos de la Guía Oficial de Tercer Corte de Desarrollo de Aplicaciones Empresariales (Profesor Wilson Castaño Galviz) tenga correspondencia biunívoca con módulos de código implementados, modelos de datos en SQLite, endpoints API y pruebas unitarias.")

    h2 = doc.add_heading("2. MATRIZ DE TRAZABILIDAD INTEGRAL", level=1)
    h2.runs[0].font.color.rgb = RGBColor(31, 73, 125)

    headers = ["Req Guía", "Historia Usuario", "Módulo / Archivo Código", "Tabla / BD", "Caso de Prueba", "Estado"]
    data = [
        ["Comp 1: Auto. Propia", "HU-C3-03", "app/automation_engine.py\napp/main.py", "tbl_ejecucion_automatizacion", "test_automation_engine_log", "100% Verificado"],
        ["Comp 1: Plan B Offline", "HU-C3-03", "app/ai_provider.py", "tbl_ejecucion_automatizacion", "test_ai_provider_plan_b", "100% Verificado"],
        ["Comp 1: Chatbot Contextual", "HU-C3-04", "app/ai_module.py\napp/main.py", "tbl_archivo\ntbl_ticket", "test_chatbot_contextual", "100% Verificado"],
        ["Comp 2: Visión Multimodal", "HU-C3-01", "app/vision_service.py\napp/main.py", "tbl_documento_vision", "test_vision_service_mock", "100% Verificado"],
        ["Comp 2: Human-in-the-Loop", "HU-C3-02", "app/templates/vision.html\napp/main.py", "tbl_documento_vision", "test_vision_confirmacion", "100% Verificado"],
        ["Comp 2: Captura Cámara", "HU-C3-01", "app/templates/vision.html", "storage/vision/", "test_upload_vision_flow", "100% Verificado"],
        ["Seguridad: PBKDF2 Hashing", "HU-C3-05", "app/auth.py\napp/crud.py", "tbl_usuario_agente", "test_auth_pbkdf2_hashing", "100% Verificado"],
        ["Seguridad: Sesiones Firmadas", "HU-C3-05", "app/auth.py\napp/main.py", "Cookies httpOnly", "test_login_success", "100% Verificado"],
        ["Datos: Habeas Data 1581", "HU-C3-05", "app/models.py\napp/templates/index.html", "tbl_cliente (acepta_tratamiento_datos)", "test_habeas_data_field", "100% Verificado"],
        ["Métricas: 100% Reales BD", "HU-C3-06", "app/crud.py", "tbl_ticket\ntbl_ejecucion_automatizacion", "test_dashboard_real_metrics", "100% Verificado"]
    ]

    create_styled_table(doc, headers, data, [Inches(1.1), Inches(0.9), Inches(1.6), Inches(1.4), Inches(1.3), Inches(0.9)])

    h3 = doc.add_heading("3. BALANCE DE CUMPLIMIENTO", level=1)
    h3.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph("Todos los requisitos exigidos se encuentran al 100% cubiertos, sin simulaciones ni código quemado, respaldados por la suite de pruebas unitarias automatizadas en pytest.")

    out_path = r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\01_ANALISIS\03_Matriz_de_Trazabilidad.docx"
    doc.save(out_path)
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    os.makedirs(r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\01_ANALISIS", exist_ok=True)
    build_hu_cu_doc()
    build_matriz_trazabilidad()
