import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

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
            run.font.size = Pt(9)
            run.font.name = "Arial"

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

    doc.add_paragraph()
    return table

def add_header_footer(doc, title_text):
    for s in doc.sections:
        s.top_margin = Inches(1)
        s.bottom_margin = Inches(1)
        s.left_margin = Inches(1)
        s.right_margin = Inches(1)
        
        header = s.header
        hp = header.paragraphs[0]
        hp.text = f"SISTEMA INTELIGENTE DE GESTIÓN Y ANÁLISIS DOCUMENTAL — {title_text.upper()}"
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if hp.runs:
            hp.runs[0].font.size = Pt(8)
            hp.runs[0].font.color.rgb = RGBColor(120, 120, 120)
            hp.runs[0].font.name = "Arial"

        footer = s.footer
        fp = footer.paragraphs[0]
        fp.text = "Desarrollo de Aplicaciones Empresariales — Tercer Corte (2026)"
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if fp.runs:
            fp.runs[0].font.size = Pt(8)
            fp.runs[0].font.color.rgb = RGBColor(120, 120, 120)
            fp.runs[0].font.name = "Arial"

def build_arquitectura():
    doc = Document()
    add_header_footer(doc, "Arquitectura del Sistema")

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("ARQUITECTURA INTEGRAL DEL SISTEMA\nEVOLUCIÓN TERCER CORTE: AUTOMATIZACIÓN E IA MULTIMODAL")
    r_title.font.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(31, 73, 125)
    r_title.font.name = "Arial"

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Diseño por Capas, Componente 1 Autónomo, Componente 2 Visión y Seguridad")
    r_sub.font.italic = True
    r_sub.font.size = Pt(11)
    r_sub.font.name = "Arial"
    doc.add_paragraph()

    h1 = doc.add_heading("1. DESCRIPCIÓN GENERAL Y ESTILO ARQUITECTÓNICO", level=1)
    h1.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph(
        "El Sistema Inteligente de Gestión y Análisis Documental evoluciona en el Tercer Corte adoptando una arquitectura "
        "modular desacoplada en capas (Layered Architecture) impulsada por eventos asíncronos y servicios autónomos. "
        "En estricto cumplimiento de la Guía Oficial, se implementa la Ruta A para el Componente 1, sustituyendo cualquier dependencia "
        "de plataformas de automatización externas por un motor propio en Python (FastAPI BackgroundTasks y AutomationEngine), "
        "respaldado por un módulo de visión multimodal (Componente 2) con validación humana (Human-in-the-Loop)."
    )

    h2 = doc.add_heading("2. DIAGRAMA CONCEPTUAL DE CAPAS Y COMPONENTES", level=1)
    h2.runs[0].font.color.rgb = RGBColor(31, 73, 125)

    doc.add_paragraph(
        "+-----------------------------------------------------------------------------------+\n"
        "| CAPA DE PRESENTACIÓN (FRONTEND)                                                    |\n"
        "| - Bento Grid Dashboard (HTML5 / Tailwind CSS / Vanilla JS interactivo)            |\n"
        "| - Módulo de Captura Móvil & Visión (Cámara web/móvil, Drag & Drop, Previsualizador) |\n"
        "| - Chatbot Contextual Documental Multi-Archivo (Modal asíncrono)                   |\n"
        "| - Panel de Aprobación Humana (Human-in-the-Loop con score y editor de entidades)   |\n"
        "+-----------------------------------------+-----------------------------------------+\n"
        "                                          | HTTP / REST (Fetch API / JSON / Cookies)\n"
        "                                          v\n"
        "+-----------------------------------------------------------------------------------+\n"
        "| CAPA DE APLICACIÓN Y CONTROL (FASTAPI BACKEND)                                    |\n"
        "| - app/main.py: Enrutador principal, middleware de sesiones firmadas y CORS       |\n"
        "| - app/auth.py: Autenticación PBKDF2-SHA256 (100.000 it), cookies httpOnly firmadas|\n"
        "| - app/config.py: Variables de entorno centralizadas (API keys, umbrales, storage) |\n"
        "| - app/crud.py: Métricas 100% reales de negocio (CSAT, SLA, tasa de éxito)        |\n"
        "+-------------------+-----------------------------------------+---------------------+\n"
        "                    |                                         |\n"
        "                    v                                         v\n"
        "+---------------------------------------+ +-----------------------------------------+\n"
        "| COMPONENTE 1: AUTOMATIZACIÓN PROPIA   | | COMPONENTE 2: IA MULTIMODAL Y VISIÓN    |\n"
        "| - app/automation_engine.py            | | - app/vision_service.py                 |\n"
        "| - BackgroundTasks asíncronas          | | - Inferencia Gemini 2.5 Flash           |\n"
        "| - Auditoría tbl_ejecucion_automatiz.  | | - Plan B: OCR Heurístico Local          |\n"
        "| - Medición latencia ms & reintentos   | | - Extracción JSON y confianza (0.0-1.0) |\n"
        "+-------------------+-------------------+ +--------------------+--------------------+\n"
        "                    |                                         |\n"
        "                    +--------------------+--------------------+ \n"
        "                                         v\n"
        "+-----------------------------------------------------------------------------------+\n"
        "| CAPA DE INTELIGENCIA ARTIFICIAL (AI PROVIDER)                                     |\n"
        "| - app/ai_provider.py: Abstracción agnóstica con tolerancia a fallos              |\n"
        "| - Primario: Google Gemini 2.5 Flash (google-genai SDK, multimodal, latencia baja)  |\n"
        "| - Secundario (Plan B): Motor heurístico local (análisis sintáctico offline)       |\n"
        "+----------------------------------------+------------------------------------------+\n"
        "                                         v\n"
        "+-----------------------------------------------------------------------------------+\n"
        "| CAPA DE PERSISTENCIA Y ALMACENAMIENTO                                             |\n"
        "| - SQLite 3 con SQLAlchemy ORM (tickets.db con integridad referencial)            |\n"
        "| - Sistema de archivos storage/vision/ con saneamiento SHA256 de nombres           |\n"
        "+-----------------------------------------------------------------------------------+"
    )

    h3 = doc.add_heading("3. DETALLE DE LOS PILARES OBLIGATORIOS DE LA GUÍA", level=1)
    h3.runs[0].font.color.rgb = RGBColor(31, 73, 125)

    headers_comp = ["Componente / Pilar", "Módulo en Código", "Estrategia Técnica", "Garantía de Cumplimiento"]
    data_comp = [
        ["Componente 1:\nAutomatización Propia", "app/automation_engine.py", "BackgroundTasks asíncronas ejecutadas en el worker de FastAPI. Trazabilidad completa con ID de ejecución, timestamp, latencia y payload JSON.", "Elimina al 100% la dependencia de n8n o servicios en la nube de terceros."],
        ["Componente 1:\nPlan B de IA", "app/ai_provider.py", "Circuit breaker lógico con timeout de 8s. Si la API de Gemini no responde o no hay cuota, se activa la heurística local basada en regex y procesamiento sintáctico.", "El sistema nunca colapsa ante desconexión o fallo del proveedor externo."],
        ["Componente 2:\nVisión Multimodal", "app/vision_service.py", "Carga de fotos de cámara móvil o escaneos. Se convierte a bytes o base64 y se analiza con Gemini 2.5 Flash solicitando salida JSON estructurada con score de confianza.", "Admite facturas, recibos y cédulas en JPG, PNG y PDF hasta 10 MB."],
        ["Componente 2:\nHuman-in-the-Loop", "app/templates/vision.html", "Si el score de confianza es inferior al umbral configurado (80%), el documento queda en 'PENDIENTE_REVISION'. Un agente humano edita y confirma las entidades.", "Previene errores contables o tributarios en el negocio antes de confirmar el registro."],
        ["Seguridad y Datos", "app/auth.py\napp/models.py", "Criptografía PBKDF2-SHA256 con 100.000 iteraciones para contraseñas. Sesiones web con cookies firmadas criptográficamente. Checkbox obligatorio de Habeas Data.", "Cumple estrictamente con la Ley Estatutaria 1581 de 2012 y OWASP Top 10."]
    ]
    create_styled_table(doc, headers_comp, data_comp, [Inches(1.5), Inches(1.4), Inches(2.3), Inches(1.8)])

    out_path = r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\02_Diseño\01_Arquitectura_del_Sistema.docx"
    doc.save(out_path)
    print(f"Saved: {out_path}")

def build_modelo_datos():
    doc = Document()
    add_header_footer(doc, "Modelo de Datos y Diccionario")

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("MODELO DE DATOS Y DICCIONARIO DE BASE DE DATOS\nTERCER CORTE: AUTOMATIZACIÓN, VISIÓN Y AUDITORÍA")
    r_title.font.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(31, 73, 125)
    r_title.font.name = "Arial"

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Estructura Relacional en SQLite con SQLAlchemy ORM")
    r_sub.font.italic = True
    r_sub.font.size = Pt(11)
    r_sub.font.name = "Arial"
    doc.add_paragraph()

    h1 = doc.add_heading("1. RESUMEN DEL ESQUEMA RELACIONAL", level=1)
    h1.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph(
        "La base de datos relacional del sistema (`tickets.db`), implementada sobre SQLite 3 e intermediada por SQLAlchemy ORM, "
        "ha sido extendida para soportar las exigencias del Tercer Corte sin romper la compatibilidad con los cortes previos. "
        "Se adicionan dos entidades clave: `tbl_ejecucion_automatizacion` (para auditoría y reintentos del Componente 1) y "
        "`tbl_documento_vision` (para el ciclo de vida de visión artificial y validación humana del Componente 2), además "
        "de campos de seguridad criptográfica y tratamiento de datos personales en entidades existentes."
    )

    h2 = doc.add_heading("2. DICCIONARIO DE DATOS DETALLADO", level=1)
    h2.runs[0].font.color.rgb = RGBColor(31, 73, 125)

    tablas = [
        ("tbl_ejecucion_automatizacion (Nueva - Componente 1)", [
            ["id", "INTEGER", "PRIMARY KEY, AUTOINCREMENT", "Identificador único secuencial"],
            ["codigo_ejecucion", "VARCHAR(36)", "NOT NULL, UNIQUE", "UUID único de correlación del flujo"],
            ["tipo_flujo", "VARCHAR(50)", "NOT NULL", "Tipo: 'CLASIFICACION_TICKET', 'SLA_ROUTING', etc."],
            ["ticket_id", "INTEGER", "NULLABLE, FK -> tbl_ticket.id", "Ticket asociado (si aplica)"],
            ["estado", "VARCHAR(20)", "NOT NULL", "'EXITOSO', 'FALLIDO', 'PLAN_B'"],
            ["latencia_ms", "INTEGER", "NOT NULL", "Tiempo de ejecución en milisegundos"],
            ["payload_entrada", "TEXT", "NULLABLE", "Entrada en formato JSON serialized"],
            ["payload_salida", "TEXT", "NULLABLE", "Respuesta generada en formato JSON"],
            ["error_detalle", "TEXT", "NULLABLE", "Descripción de excepciones en caso de fallo"],
            ["fecha_ejecucion", "DATETIME", "NOT NULL, DEFAULT NOW", "Marca temporal de la ejecución"]
        ]),
        ("tbl_documento_vision (Nueva - Componente 2)", [
            ["id", "INTEGER", "PRIMARY KEY, AUTOINCREMENT", "Identificador único"],
            ["codigo_documento", "VARCHAR(36)", "NOT NULL, UNIQUE", "UUID de seguimiento público"],
            ["ticket_id", "INTEGER", "NULLABLE, FK -> tbl_ticket.id", "Ticket vinculado"],
            ["nombre_archivo", "VARCHAR(255)", "NOT NULL", "Nombre original del archivo"],
            ["ruta_almacenamiento", "VARCHAR(500)", "NOT NULL", "Ruta física segura en storage/vision/"],
            ["tipo_mime", "VARCHAR(50)", "NOT NULL", "image/jpeg, image/png, application/pdf"],
            ["tamanio_bytes", "INTEGER", "NOT NULL", "Tamaño exacto del archivo en bytes"],
            ["emisor", "VARCHAR(150)", "NULLABLE", "Razón social / entidad detectada"],
            ["nit", "VARCHAR(30)", "NULLABLE", "NIT o documento de identificación fiscal"],
            ["total", "FLOAT", "NULLABLE", "Monto total monetario extraído"],
            ["moneda", "VARCHAR(10)", "NULLABLE, DEFAULT 'COP'", "Divisa identificada"],
            ["fecha_documento", "VARCHAR(50)", "NULLABLE", "Fecha impresa en el documento"],
            ["score_confianza", "FLOAT", "NOT NULL", "Nivel de confianza de la IA (0.0 a 1.0)"],
            ["requiere_revision_humana", "BOOLEAN", "NOT NULL", "True si score < 0.80, False si >= 0.80"],
            ["estado_revision", "VARCHAR(30)", "NOT NULL", "'PENDIENTE', 'CONFIRMADO', 'RECHAZADO'"],
            ["estado_ia", "VARCHAR(20)", "NOT NULL", "'GEMINI_FLASH' o 'PLAN_B'"],
            ["fecha_creacion", "DATETIME", "NOT NULL", "Momento del procesamiento inicial"],
            ["fecha_confirmacion", "DATETIME", "NULLABLE", "Momento en que el humano validó los datos"]
        ]),
        ("tbl_cliente (Modificada - Habeas Data)", [
            ["id", "INTEGER", "PRIMARY KEY, AUTOINCREMENT", "Identificador del cliente"],
            ["nombre", "VARCHAR(100)", "NOT NULL", "Nombre completo del cliente"],
            ["correo", "VARCHAR(100)", "NOT NULL, UNIQUE", "Correo electrónico de contacto"],
            ["telefono", "VARCHAR(20)", "NULLABLE", "Número telefónico"],
            ["acepta_tratamiento_datos", "BOOLEAN", "NOT NULL, DEFAULT FALSE", "Autorización expresa Ley 1581"],
            ["fecha_autorizacion_datos", "DATETIME", "NULLABLE", "Timestamp de consentimiento informado"]
        ]),
        ("tbl_usuario_agente (Modificada - Seguridad Criptográfica)", [
            ["id", "INTEGER", "PRIMARY KEY, AUTOINCREMENT", "Identificador del usuario agente"],
            ["correo", "VARCHAR(100)", "NOT NULL, UNIQUE", "Credencial de acceso"],
            ["nombre", "VARCHAR(100)", "NOT NULL", "Nombre completo"],
            ["rol", "VARCHAR(20)", "NOT NULL", "ADMINISTRADOR, AGENTE, SUPERVISOR"],
            ["password_hash", "VARCHAR(255)", "NOT NULL", "Hash PBKDF2-SHA256 (100k iteraciones)"],
            ["ultimo_acceso", "DATETIME", "NULLABLE", "Último inicio de sesión exitoso"],
            ["activo", "BOOLEAN", "NOT NULL, DEFAULT TRUE", "Estado de la cuenta"]
        ])
    ]

    for tbl_name, cols in tablas:
        h_tbl = doc.add_heading(f"2.{tablas.index((tbl_name, cols)) + 1} {tbl_name}", level=2)
        h_tbl.runs[0].font.color.rgb = RGBColor(31, 73, 125)
        headers_col = ["Campo", "Tipo de Dato", "Restricción / Regla", "Descripción"]
        create_styled_table(doc, headers_col, cols, [Inches(1.5), Inches(1.2), Inches(1.8), Inches(2.5)])

    out_path = r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\02_Diseño\02_Modelo_de_Datos_y_Diccionario.docx"
    doc.save(out_path)
    print(f"Saved: {out_path}")

def build_interfaces_api():
    doc = Document()
    add_header_footer(doc, "Diseño de Interfaces y API")

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("DISEÑO DE INTERFACES DE USUARIO Y ESPECIFICACIÓN DE LA API\nTERCER CORTE: EXPERIENCIA MULTIMODAL Y SERVICIOS REST")
    r_title.font.bold = True
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(31, 73, 125)
    r_title.font.name = "Arial"

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Bento Grid UI Responsivo, Captura Móvil, Chatbot Contextual y Endpoints OpenAPI")
    r_sub.font.italic = True
    r_sub.font.size = Pt(11)
    r_sub.font.name = "Arial"
    doc.add_paragraph()

    h1 = doc.add_heading("1. EXPERIENCIA DE USUARIO Y DISEÑO FRONTEND", level=1)
    h1.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    doc.add_paragraph(
        "El frontend del sistema adopta el paradigma Bento Grid (Apple-inspired modular layout), priorizando la "
        "claridad cognitiva, el feedback inmediato del estado del sistema y la facilidad de uso tanto en pantallas de escritorio "
        "como en smartphones y tablets. El módulo de visión por computador (`/vision`) cuenta con una zona interactiva para "
        "activar la cámara web/móvil con un solo clic (`capture='environment'`), vista previa en vivo, indicador cromático "
        "del nivel de confianza de la IA y un panel 'Human-in-the-Loop' que permite la corrección manual inmediata de los datos."
    )

    h2 = doc.add_heading("2. CATÁLOGO COMPLETO DE ENDPOINTS REST (API BACKEND)", level=1)
    h2.runs[0].font.color.rgb = RGBColor(31, 73, 125)

    headers_api = ["Método", "Ruta / Endpoint", "Autenticación", "Descripción y Respuesta", "Componente"]
    data_api = [
        ["POST", "/login", "Pública", "Valida correo y contraseña mediante PBKDF2. Emite cookie httpOnly firmada.", "Seguridad"],
        ["GET", "/logout", "Pública", "Revoca la cookie de sesión del usuario y redirige al login.", "Seguridad"],
        ["GET", "/vision", "Sesión requerida", "Renderiza la interfaz web de escaneo móvil y visión multimodal.", "Componente 2"],
        ["POST", "/api/v1/vision/procesar", "Pública / Sesión", "Recibe archivo multipart (JPG/PNG/PDF), ejecuta Gemini 2.5 Flash o Plan B, extrae entidades y calcula score.", "Componente 2"],
        ["POST", "/api/v1/vision/{codigo}/confirmar", "Sesión agente", "Guarda correcciones humanas y confirma el documento en la base de datos.", "Componente 2"],
        ["POST", "/tickets", "Pública", "Crea ticket, valida Habeas Data y dispara AutomationEngine en background.", "Componente 1"],
        ["POST", "/api/v1/tickets/{id}/chatbot", "Pública", "Chatbot contextual documental. Lee todos los archivos adjuntos y responde con IA o Plan B.", "Componente 1"],
        ["GET", "/api/v1/automatizaciones/logs", "Sesión agente", "Retorna el historial de ejecuciones en segundo plano con latencias y estados.", "Componente 1"],
        ["GET", "/dashboard", "Sesión agente", "Renderiza métricas 100% reales calculadas por SQL (CSAT, tiempo resolución, tasa éxito).", "Gestión"]
    ]
    create_styled_table(doc, headers_api, data_api, [Inches(0.8), Inches(1.8), Inches(1.2), Inches(2.2), Inches(1.0)])

    out_path = r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\02_Diseño\03_Diseno_de_Interfaces_y_API.docx"
    doc.save(out_path)
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    os.makedirs(r"c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\02_Diseño", exist_ok=True)
    build_arquitectura()
    build_modelo_datos()
    build_interfaces_api()
