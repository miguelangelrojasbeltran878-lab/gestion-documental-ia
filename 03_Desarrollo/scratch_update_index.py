import os

index_path = r'c:\Users\Lenovo\OneDrive\Documentos\Proyecto_Aplicaciones_Empresariales\03_Desarrollo\app\templates\index.html'
with open(index_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Update the form action from GET /agente/tickets to POST /login
old_form = '<form action="/agente/tickets" method="GET" class="mb-3">'
new_form = '''{% if error_login %}
                    <div class="alert alert-danger py-2 px-3 rounded-4 small mb-3 d-flex align-items-center gap-2" style="background:rgba(244,63,94,0.15);border:1px solid rgba(244,63,94,0.35);color:#fca5a5;">
                        <i class="bi bi-exclamation-octagon-fill"></i>
                        <div>{{ error_login }}</div>
                    </div>
                    {% endif %}
                    <form action="/login" method="POST" class="mb-3">'''

# Change input name attributes
old_inputs = '''<div class="mb-3">
                            <label class="form-label small text-secondary fw-semibold">CORREO CORPORATIVO</label>
                            <input type="email" value="andres.gomez@empresa.com" required class="form-control sleek-input">
                        </div>
                        <div class="mb-4">
                            <label class="form-label small text-secondary fw-semibold">CONTRASEÑA</label>
                            <input type="password" value="••••••••" required class="form-control sleek-input">
                        </div>'''

new_inputs = '''<div class="mb-3">
                            <label class="form-label small text-secondary fw-semibold">CORREO CORPORATIVO</label>
                            <input type="email" name="email" value="andres.gomez@empresa.com" required class="form-control sleek-input">
                        </div>
                        <div class="mb-4">
                            <label class="form-label small text-secondary fw-semibold">CONTRASEÑA</label>
                            <input type="password" name="password" value="Password123*" required class="form-control sleek-input">
                        </div>'''

if old_form in html:
    html = html.replace(old_form, new_form)
if old_inputs in html:
    html = html.replace(old_inputs, new_inputs)

# Add link to /vision in index.html navbar or footer
if '/vision' not in html:
    html = html.replace(
        '<a href="/make/flujos" class="text-info small text-decoration-none fw-bold"><i class="bi bi-diagram-3-fill me-1"></i>Ver Flujos Make</a>',
        '<a href="/vision" class="text-warning small text-decoration-none fw-bold"><i class="bi bi-camera-fill me-1"></i>Visión Multimodal (Guía 3)</a><a href="/make/flujos" class="text-info small text-decoration-none fw-bold"><i class="bi bi-diagram-3-fill me-1"></i>Ver Flujos Make</a>'
    )

with open(index_path, 'w', encoding='utf-8') as f:
    f.write(html)
print("Index.html updated with POST /login and Vision link!")
